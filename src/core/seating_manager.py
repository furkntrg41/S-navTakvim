from typing import List, Dict, Tuple
from datetime import datetime
from src.core.db_raw import Database
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SeatingManager:
    
    def __init__(self, db: Database):
        self.db = db
    
    def generate_seating_for_exam(self, exam_id: int) -> Dict:
        try:
            exam_row = self.db.fetch_one("SELECT * FROM exams WHERE id = ?", (exam_id,))
            if not exam_row:
                return {
                    "success": False,
                    "message": f"Sınav bulunamadı (ID: {exam_id})",
                    "total_students": 0,
                    "assigned_students": 0,
                    "sessions": []
                }
            
            exam = dict(exam_row)

            student_rows = self.db.fetch_all("""
                SELECT s.*
                FROM students s
                JOIN student_courses sc ON s.id = sc.student_id
                WHERE sc.course_id = ?
            """, (exam['course_id'],))
            
            students = [dict(row) for row in student_rows]
            
            if not students:
                return {
                    "success": False,
                    "message": "Bu sınava kayıtlı öğrenci bulunamadı",
                    "total_students": 0,
                    "assigned_students": 0,
                    "sessions": []
                }
            
            total_students = len(students)
            logger.info(f"Sınav {exam_id} için {total_students} öğrenci bulundu")

            session_rows = self.db.fetch_all("""
                SELECT es.*, cl.code as classroom_code, cl.capacity as classroom_capacity,
                       cl.rows as row_count, cl.columns as column_count, cl.is_active,
                       cl.seating_arrangement
                FROM exam_sessions es
                JOIN classrooms cl ON es.classroom_id = cl.id
                WHERE es.exam_id = ?
                ORDER BY cl.capacity DESC
            """, (exam_id,))
            
            exam_sessions = [dict(row) for row in session_rows]
            initial_session_count = len(exam_sessions)
            
            if not exam_sessions:
                return {
                    "success": False,
                    "message": "Bu sınav için derslik ataması yapılmamış",
                    "total_students": total_students,
                    "assigned_students": 0,
                    "sessions": [],
                    "initial_classrooms": 0
                }
            
            total_capacity = sum(s['classroom_capacity'] for s in exam_sessions)
            if total_capacity < total_students:
                needed_capacity = total_students - total_capacity
                logger.warning(
                    f"Kapasite yetersiz! {total_students} öğrenci için "
                    f"{total_capacity} koltuk var. {needed_capacity} ek koltuk gerekli."
                )

                used_classroom_ids = [s['classroom_id'] for s in exam_sessions]

                conflicting_rows = self.db.fetch_all("""
                    SELECT es.classroom_id
                    FROM exam_sessions es
                    JOIN exams e ON es.exam_id = e.id
                    WHERE e.schedule_id = ?
                      AND e.exam_date = ?
                      AND e.start_time = ?
                      AND e.id != ?
                """, (exam['schedule_id'], exam['exam_date'], exam['start_time'], exam_id))
                
                conflicting_classroom_ids = [row['classroom_id'] for row in conflicting_rows]

                excluded_ids = used_classroom_ids + conflicting_classroom_ids
                if excluded_ids:
                    placeholders = ','.join('?' * len(excluded_ids))
                    available_rows = self.db.fetch_all(f"""
                        SELECT * FROM classrooms
                        WHERE is_active = 1
                          AND id NOT IN ({placeholders})
                        ORDER BY capacity DESC
                    """, tuple(excluded_ids))
                else:
                    available_rows = self.db.fetch_all("""
                        SELECT * FROM classrooms
                        WHERE is_active = 1
                        ORDER BY capacity DESC
                    """)
                
                available_classrooms = [dict(row) for row in available_rows]

                added_capacity = 0
                for classroom in available_classrooms:
                    if added_capacity >= needed_capacity:
                        break

                    new_session_id = self.db.execute("""
                        INSERT INTO exam_sessions (exam_id, classroom_id, allocated_seats)
                        VALUES (?, ?, 0)
                    """, (exam_id, classroom['id']))

                    seating = classroom.get('seating_arrangement', 2)
                    total_seats = classroom['rows'] * classroom['columns']
                    if seating == 2:
                        actual_capacity = classroom['rows'] * (classroom['columns'] // 2)
                    elif seating == 3:
                        actual_capacity = classroom['rows'] * ((classroom['columns'] // 3) * 2)
                    elif seating == 4:
                        actual_capacity = classroom['rows'] * ((classroom['columns'] // 4) * 2)
                    else:
                        actual_capacity = total_seats // 2
                    
                    new_session = {
                        'id': new_session_id,
                        'exam_id': exam_id,
                        'classroom_id': classroom['id'],
                        'allocated_seats': 0,
                        'classroom_code': classroom['code'],
                        'classroom_capacity': actual_capacity,
                        'row_count': classroom['rows'],
                        'column_count': classroom['columns'],
                        'is_active': classroom['is_active'],
                        'seating_arrangement': seating
                    }
                    exam_sessions.append(new_session)
                    added_capacity += actual_capacity
                    
                    logger.info(
                        f"Ek derslik eklendi: {classroom['code']} "
                        f"({actual_capacity} öğrenci kapasitesi, {seating}'li oturma)"
                    )
                
                if added_capacity < needed_capacity:
                    logger.warning(
                        f"Yeterli boş derslik bulunamadı! "
                        f"{needed_capacity - added_capacity} koltuk hala eksik."
                    )
            
            for session in exam_sessions:
                self.db.execute(
                    "DELETE FROM seating_assignments WHERE exam_session_id = ?",
                    (session['id'],)
                )
            
            assigned_count = 0
            session_infos = []
            student_index = 0
            
            for exam_session in exam_sessions:
                rows = exam_session['row_count']
                cols = exam_session['column_count']
                seating_arrangement = exam_session.get('seating_arrangement', 2)

                total_seats = rows * cols
                if seating_arrangement == 2:
                    capacity = rows * (cols // 2)
                elif seating_arrangement == 3:
                    capacity = rows * ((cols // 3) * 2)
                elif seating_arrangement == 4:
                    capacity = rows * ((cols // 4) * 2)
                else:
                    capacity = total_seats // 2
                
                logger.info(
                    f"Derslik {exam_session['classroom_code']}: {rows}x{cols} = {total_seats} koltuk, "
                    f"{seating_arrangement}'li oturma → {capacity} öğrenci kapasitesi"
                )
                
                students_for_session = []
                while student_index < total_students and len(students_for_session) < capacity:
                    students_for_session.append(students[student_index])
                    student_index += 1
                
                if not students_for_session:
                    logger.warning(f"Derslik {exam_session['classroom_code']} için öğrenci kalmadı")
                    continue
                
                assignments = self._assign_by_seating_arrangement(
                    exam_session['id'], students_for_session, rows, cols, seating_arrangement
                )
                
                for assignment in assignments:
                    self.db.execute("""
                        INSERT INTO seating_assignments 
                        (exam_session_id, student_id, row_number, column_number, seat_number)
                        VALUES (?, ?, ?, ?, ?)
                    """, (assignment['exam_session_id'], assignment['student_id'],
                          assignment['row_number'], assignment['column_number'], 
                          assignment['seat_number']))
                
                assigned_count += len(assignments)
                
                self.db.execute(
                    "UPDATE exam_sessions SET allocated_seats = ? WHERE id = ?",
                    (len(assignments), exam_session['id'])
                )
                
                session_infos.append({
                    "classroom_code": exam_session['classroom_code'],
                    "classroom_name": exam_session['classroom_code'],
                    "capacity": capacity,
                    "assigned": len(assignments),
                    "rows": rows,
                    "cols": cols
                })
                
                logger.info(
                    f"Derslik {exam_session['classroom_code']}: {len(assignments)} öğrenci yerleştirildi"
                )
            
            success = assigned_count == total_students
            message = (
                f"Oturma planı oluşturuldu: {assigned_count}/{total_students} öğrenci" 
                if success 
                else f"UYARI: {assigned_count}/{total_students} öğrenci yerleştirildi (kapasite yetersiz)"
            )
            
            return {
                "success": success,
                "message": message,
                "total_students": total_students,
                "assigned_students": assigned_count,
                "sessions": session_infos,
                "initial_classrooms": initial_session_count
            }
        
        except Exception as e:
            logger.error(f"Oturma planı oluşturma hatası: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Hata: {str(e)}",
                "total_students": 0,
                "assigned_students": 0,
                "sessions": [],
                "initial_classrooms": 0
            }
    
    def _assign_by_seating_arrangement(
        self, 
        exam_session_id: int, 
        students: list, 
        rows: int, 
        cols: int,
        seating_arrangement: int
    ) -> list:
        assignments = []
        student_idx = 0
        
        if seating_arrangement == 2:
            for row in range(1, rows + 1):
                for col in range(2, cols + 1, 2):
                    if student_idx >= len(students):
                        return assignments
                    
                    assignments.append({
                        'exam_session_id': exam_session_id,
                        'student_id': students[student_idx]['id'],
                        'row_number': row,
                        'column_number': col,
                        'seat_number': (row - 1) * cols + col
                    })
                    student_idx += 1
        
        elif seating_arrangement == 3:
            for row in range(1, rows + 1):
                for col in range(1, cols + 1):
                    col_in_group = ((col - 1) % 3) + 1
                    if col_in_group == 1 or col_in_group == 3:
                        if student_idx >= len(students):
                            return assignments
                        
                        assignments.append({
                            'exam_session_id': exam_session_id,
                            'student_id': students[student_idx]['id'],
                            'row_number': row,
                            'column_number': col,
                            'seat_number': (row - 1) * cols + col
                        })
                        student_idx += 1
        
        elif seating_arrangement == 4:
            for row in range(1, rows + 1):
                for col in range(1, cols + 1):
                    col_in_group = ((col - 1) % 4) + 1
                    if col_in_group == 1 or col_in_group == 4:
                        if student_idx >= len(students):
                            return assignments
                        
                        assignments.append({
                            'exam_session_id': exam_session_id,
                            'student_id': students[student_idx]['id'],
                            'row_number': row,
                            'column_number': col,
                            'seat_number': (row - 1) * cols + col
                        })
                        student_idx += 1
        
        else:
            for row in range(1, rows + 1):
                if row % 2 == 1:
                    start_col = 1
                else:
                    start_col = 2
                
                for col in range(start_col, cols + 1, 2):
                    if student_idx >= len(students):
                        return assignments
                    
                    assignments.append({
                        'exam_session_id': exam_session_id,
                        'student_id': students[student_idx]['id'],
                        'row_number': row,
                        'column_number': col,
                        'seat_number': (row - 1) * cols + col
                    })
                    student_idx += 1
        
        return assignments
    
    def get_seating_plan(self, exam_id: int) -> Dict:
        try:
            exam_row = self.db.fetch_one("""
                SELECT e.*, c.code as course_code, c.name as course_name
                FROM exams e
                JOIN courses c ON e.course_id = c.id
                WHERE e.id = ?
            """, (exam_id,))
            
            if not exam_row:
                return {"success": False, "message": "Sınav bulunamadı"}
            
            exam = dict(exam_row)

            session_rows = self.db.fetch_all("""
                SELECT es.*, cl.code as classroom_code, cl.rows as row_count, 
                       cl.columns as column_count, cl.capacity
                FROM exam_sessions es
                JOIN classrooms cl ON es.classroom_id = cl.id
                WHERE es.exam_id = ?
            """, (exam_id,))
            
            sessions_data = []
            for session_row in session_rows:
                exam_session = dict(session_row)

                assignment_rows = self.db.fetch_all("""
                    SELECT sa.*, s.student_number, s.first_name, s.last_name
                    FROM seating_assignments sa
                    JOIN students s ON sa.student_id = s.id
                    WHERE sa.exam_session_id = ?
                    ORDER BY sa.row_number, sa.column_number
                """, (exam_session['id'],))
                
                seating_data = []
                for assignment_row in assignment_rows:
                    assignment = dict(assignment_row)
                    seating_data.append({
                        "student_no": assignment['student_number'],
                        "student_name": f"{assignment['first_name']} {assignment['last_name']}",
                        "row": assignment['row_number'],
                        "col": assignment['column_number'],
                        "seat": assignment['seat_number']
                    })
                
                sessions_data.append({
                    "classroom": {
                        "code": exam_session['classroom_code'],
                        "name": exam_session['classroom_code'],
                        "rows": exam_session['row_count'],
                        "cols": exam_session['column_count'],
                        "capacity": exam_session['capacity']
                    },
                    "seating": seating_data
                })
            
            if isinstance(exam['exam_date'], str):
                exam_date = datetime.fromisoformat(exam['exam_date'])
            else:
                exam_date = exam['exam_date']
            
            if isinstance(exam['start_time'], str):
                from datetime import datetime
                start_time = datetime.fromisoformat(f"2000-01-01 {exam['start_time']}")
            else:
                start_time = exam['start_time']
            
            return {
                "success": True,
                "exam": {
                    "id": exam['id'],
                    "course_code": exam['course_code'],
                    "course_name": exam['course_name'],
                    "date": exam_date.strftime("%Y-%m-%d"),
                    "time": start_time.strftime("%H:%M")
                },
                "sessions": sessions_data
            }
        
        except Exception as e:
            logger.error(f"Oturma planı getirme hatası: {e}", exc_info=True)
            return {"success": False, "message": f"Hata: {str(e)}"}
