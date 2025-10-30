import logging
from datetime import datetime, timedelta, time
from collections import defaultdict
from typing import List, Dict, Tuple, Optional, Set
import random
import itertools
from src.core.db_raw import Database

logger = logging.getLogger(__name__)


class ExamScheduler:
    
    def __init__(self, db: Database, exam_schedule_id: int):
        self.db = db
        
        exam_schedule_row = self.db.fetch_one(
            "SELECT * FROM exam_schedules WHERE id = ?", 
            (exam_schedule_id,)
        )
        
        if not exam_schedule_row:
            raise ValueError(f"ExamSchedule ID {exam_schedule_id} bulunamadı")
        
        self.exam_schedule = dict(exam_schedule_row)
        
        self.courses: List[Dict] = []
        self.classrooms: List[Dict] = []
        self.time_slots: List[Tuple[datetime, int]] = []
        self.student_courses: Dict[int, List[int]] = defaultdict(list)
        self.course_student_counts: Dict[int, int] = {}
        self.course_class_levels: Dict[int, str] = {}
        self.slot_to_date: Dict[int, datetime] = {}
        
        self.course_assignments: Dict[int, Dict] = {}
        self.slot_usage: Dict[int, Set[int]] = defaultdict(set)
        self.classroom_slot_usage: Dict[Tuple[int, int], int] = {}
        self.date_class_level_usage: Dict[Tuple, Set[int]] = defaultdict(set)
        
        self.start_time = None
        self.end_time = None
        self.total_attempts = 0
        
    def prepare_data(self, course_ids: List[int], classroom_ids: List[int]):
        logger.info("📊 Zamanlama verileri hazırlanıyor...")

        if course_ids:
            placeholders = ','.join('?' * len(course_ids))
            course_rows = self.db.fetch_all(
                f"SELECT * FROM courses WHERE id IN ({placeholders})",
                tuple(course_ids)
            )
            self.courses = [dict(row) for row in course_rows]
        else:
            self.courses = []
        
        logger.info(f"  ✓ {len(self.courses)} ders yüklendi")

        if classroom_ids:
            placeholders = ','.join('?' * len(classroom_ids))
            classroom_rows = self.db.fetch_all(
                f"SELECT * FROM classrooms WHERE id IN ({placeholders})",
                tuple(classroom_ids)
            )
            self.classrooms = [dict(row) for row in classroom_rows]
        else:
            self.classrooms = []
        
        logger.info(f"  ✓ {len(self.classrooms)} derslik yüklendi")
        total_capacity = sum(c['capacity'] for c in self.classrooms)
        logger.info(f"  ✓ Toplam derslik kapasitesi: {total_capacity}")

        self._generate_time_slots()
        logger.info(f"  ✓ {len(self.time_slots)} zaman dilimi oluşturuldu")

        self._load_student_courses()
        logger.info(f"  ✓ {len(self.student_courses)} öğrencinin ders kayıtları yüklendi")

        self._calculate_student_counts()
        
    def _generate_time_slots(self):
        try:
            start_date = self.exam_schedule['start_date']
            end_date = self.exam_schedule['end_date']
            
            if not start_date or not end_date:
                raise ValueError("Başlangıç ve bitiş tarihleri belirtilmemiş!")

            if not self.exam_schedule.get('allowed_days'):
                logger.warning("allowed_days belirtilmemiş, varsayılan: Pazartesi-Cuma")
                allowed_days = [0, 1, 2, 3, 4]
            else:
                allowed_days = [int(d) for d in self.exam_schedule['allowed_days'].split(',')]

            slot_times = [
                time(9, 0),
                time(13, 30)
            ]
            
            current_date = start_date
            slot_index = 0
            
            while current_date <= end_date:
                if current_date.weekday() in allowed_days:
                    for time_slot in slot_times:
                        slot_datetime = datetime.combine(current_date, time_slot)
                        self.time_slots.append((slot_datetime, slot_index))
                        self.slot_to_date[slot_index] = current_date.date()
                        slot_index += 1
                
                current_date += timedelta(days=1)
                
        except Exception as e:
            logger.error(f"Zaman slotları oluşturma hatası: {str(e)}", exc_info=True)
            raise
    
    def _load_student_courses(self):
        student_course_rows = self.db.fetch_all("SELECT * FROM student_courses")
        
        course_ids_set = {c['id'] for c in self.courses}
        for row in student_course_rows:
            record = dict(row)
            if record['course_id'] in course_ids_set:
                self.student_courses[record['student_id']].append(record['course_id'])
    
    def _calculate_student_counts(self):
        for course in self.courses:
            student_count = sum(
                1 for students in self.student_courses.values()
                if course['id'] in students
            )
            self.course_student_counts[course['id']] = student_count
            self.course_class_levels[course['id']] = course.get('class_level', '')
            logger.info(f"    • {course['code']} (Sınıf: {course.get('class_level', 'N/A')}): {student_count} öğrenci")
        
        total_students = sum(self.course_student_counts.values())
        logger.info(f"  ✓ Toplam {total_students} ders-öğrenci eşleşmesi")
    
    def solve(self, time_limit_seconds: int = 300) -> bool:
        logger.info("🚀 Manuel zamanlama algoritması başlatılıyor...")
        logger.info(f"  📚 Ders sayısı: {len(self.courses)}")
        logger.info(f"  ⏰ Slot sayısı: {len(self.time_slots)}")
        logger.info(f"  🏫 Derslik sayısı: {len(self.classrooms)}")
        
        self.start_time = datetime.now()

        sorted_courses = self._sort_courses_by_priority()

        success = True
        failed_courses = []
        
        for i, course in enumerate(sorted_courses, 1):
            logger.info(f"\n[{i}/{len(sorted_courses)}] Ders yerleştiriliyor: {course['code']} ({course.get('name', 'N/A')})")
            
            if not self._assign_course_to_slot(course):
                logger.error(f"  ❌ Ders yerleştirilemedi: {course['code']}")
                failed_courses.append(course)
                success = False
            else:
                logger.info(f"  ✅ Yerleştirildi")
        
        self.end_time = datetime.now()
        elapsed = (self.end_time - self.start_time).total_seconds()
        
        if success:
            logger.info(f"\n✨ BAŞARILI! Tüm dersler yerleştirildi")
            logger.info(f"  ⏱️  Süre: {elapsed:.2f} saniye")
            logger.info(f"  🔄 Toplam deneme: {self.total_attempts}")
            return True
        else:
            logger.error(f"\n❌ BAŞARISIZ! {len(failed_courses)} ders yerleştirilemedi:")
            for course in failed_courses:
                logger.error(f"  • {course['code']} - {course.get('name', 'N/A')}")
            return False
    
    def _sort_courses_by_priority(self) -> List[Dict]:
        def priority_key(course):
            student_count = self.course_student_counts.get(course['id'], 0)
            is_mandatory = course.get('is_mandatory', 0)

            try:
                class_level = int(course.get('class_level', 0))
            except:
                class_level = 0

            return (-student_count, -is_mandatory, -class_level)
        
        sorted_courses = sorted(self.courses, key=priority_key)
        
        logger.info("\n📋 Derslerin öncelik sırası:")
        for i, course in enumerate(sorted_courses[:10], 1):
            student_count = self.course_student_counts.get(course['id'], 0)
            logger.info(f"  {i}. {course['code']} - {student_count} öğrenci - Sınıf: {course.get('class_level', 'N/A')}")
        
        if len(sorted_courses) > 10:
            logger.info(f"  ... ve {len(sorted_courses) - 10} ders daha")
        
        return sorted_courses
    
    def _assign_course_to_slot(self, course: Dict) -> bool:
        course_id = course['id']
        student_count = self.course_student_counts.get(course_id, 0)
        class_level = course.get('class_level', '')

        for slot_datetime, slot_idx in self.time_slots:
            self.total_attempts += 1

            slot_date = self.slot_to_date[slot_idx]
            if class_level:
                if self._check_class_level_conflict(slot_date, class_level, course_id):
                    continue

            if self._check_student_conflict(slot_idx, course_id):
                continue

            if not self._check_min_days_between(slot_date, course_id):
                continue

            suitable_classrooms = self._find_suitable_classrooms(slot_idx, student_count)
            
            if not suitable_classrooms:
                continue

            self._place_course(course_id, slot_idx, slot_datetime, suitable_classrooms, class_level, slot_date)
            return True
        
        return False
    
    def _check_class_level_conflict(self, slot_date, class_level: str, course_id: int) -> bool:
        if (slot_date, class_level) in self.date_class_level_usage:
            return True
        return False
    
    def _check_student_conflict(self, slot_idx: int, course_id: int) -> bool:
        courses_in_slot = self.slot_usage.get(slot_idx, set())

        students_taking_this_course = {
            student_id for student_id, course_ids in self.student_courses.items()
            if course_id in course_ids
        }

        for other_course_id in courses_in_slot:
            students_taking_other_course = {
                student_id for student_id, course_ids in self.student_courses.items()
                if other_course_id in course_ids
            }

            common_students = students_taking_this_course & students_taking_other_course
            if common_students:
                return True
        
        return False
    
    def _check_min_days_between(self, slot_date, course_id: int) -> bool:
        min_days = self.exam_schedule.get('min_days_between_exams', 0)
        
        if min_days == 0:
            return True

        students_taking_this_course = {
            student_id for student_id, course_ids in self.student_courses.items()
            if course_id in course_ids
        }
        
        for student_id in students_taking_this_course:
            other_courses = [cid for cid in self.student_courses[student_id] if cid != course_id]
            
            for other_course_id in other_courses:
                if other_course_id in self.course_assignments:
                    other_slot_idx = self.course_assignments[other_course_id]['slot_idx']
                    other_date = self.slot_to_date[other_slot_idx]
                    
                    day_diff = abs((slot_date - other_date).days)
                    
                    if day_diff < min_days:
                        return False
        
        return True

    def _find_suitable_classrooms(self, slot_idx: int, student_count: int) -> List[Dict]:
        available_classrooms = [
            c for c in self.classrooms
            if (c['id'], slot_idx) not in self.classroom_slot_usage
        ]
        if not available_classrooms:
            return []

        available_classrooms.sort(key=lambda c: c['capacity'])

        selected = []
        total_capacity = 0

        for c in available_classrooms:
            selected.append(c)
            total_capacity += c['capacity']

            if total_capacity >= student_count:
                break

        if total_capacity < student_count:
            return []

        usage_rate = student_count / total_capacity
        logger.debug(
            f"🔹 Slot {slot_idx}: {student_count} öğrenci için {len(selected)} derslik seçildi "
            f"({usage_rate:.1%} doluluk)"
        )

        return selected
    def _place_course(self, course_id: int, slot_idx: int, slot_datetime: datetime,
                      classrooms: List[Dict], class_level: str, slot_date):
        
        classroom_ids = [c['id'] for c in classrooms]

        self.course_assignments[course_id] = {
            'slot_idx': slot_idx,
            'datetime': slot_datetime,
            'classroom_ids': classroom_ids
        }

        self.slot_usage[slot_idx].add(course_id)

        for classroom_id in classroom_ids:
            self.classroom_slot_usage[(classroom_id, slot_idx)] = course_id

        if class_level:
            self.date_class_level_usage[(slot_date, class_level)].add(course_id)
    
    def save_solution(self):
        logger.info("\n💾 Çözüm veritabanına kaydediliyor...")
        
        try:
            self.db.execute(
                "DELETE FROM exams WHERE schedule_id = ?",
                (self.exam_schedule['id'],)
            )

            for course_id, assignment in self.course_assignments.items():
                course = next((c for c in self.courses if c['id'] == course_id), None)
                if not course:
                    continue
                
                slot_datetime = assignment['datetime']
                classroom_ids = assignment['classroom_ids']
                student_count = self.course_student_counts.get(course_id, 0)

                exam_id = self.db.execute("""
                    INSERT INTO exams 
                    (schedule_id, course_id, exam_date, start_time, duration, student_count, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'scheduled')
                """, (
                    self.exam_schedule['id'],
                    course_id,
                    slot_datetime.date().isoformat(),
                    slot_datetime.time().isoformat(),
                    self.exam_schedule['default_exam_duration'],
                    student_count
                ))

                for classroom_id in classroom_ids:
                    classroom = next((c for c in self.classrooms if c['id'] == classroom_id), None)
                    if classroom:
                        self.db.execute("""
                            INSERT INTO exam_sessions (exam_id, classroom_id, allocated_seats)
                            VALUES (?, ?, ?)
                        """, (
                            exam_id,
                            classroom_id,
                            min(student_count, classroom['capacity'])
                        ))
                
                logger.info(f"  ✓ {course['code']}: {slot_datetime.strftime('%d.%m.%Y %H:%M')} - {len(classroom_ids)} derslik")
            
            
            self.db.execute(
                "UPDATE exam_schedules SET is_finalized = 1 WHERE id = ?",
                (self.exam_schedule['id'],)
            )
            
            logger.info("✅ Çözüm başarıyla kaydedildi")
            
        except Exception as e:
            logger.error(f"Çözüm kaydetme hatası: {str(e)}")
            raise
    
    def get_statistics(self) -> Dict:
        elapsed = 0
        if self.start_time and self.end_time:
            elapsed = (self.end_time - self.start_time).total_seconds()

        used_classrooms = len(set(
            classroom_id for classroom_id, slot_idx in self.classroom_slot_usage.keys()
        ))
        
        return {
            'toplam_ders': len(self.courses),
            'yerlestirildi': len(self.course_assignments),
            'toplam_derslik': len(self.classrooms),
            'kullanilan_derslik': used_classrooms,
            'toplam_slot': len(self.time_slots),
            'kullanilan_slot': len(self.slot_usage),
            'toplam_ogrenci': len(self.student_courses),
            'cozum_suresi': elapsed,
            'toplam_deneme': self.total_attempts,
            'durum': 'OPTIMAL' if len(self.course_assignments) == len(self.courses) else 'PARTIAL'
        }


def schedule_exams(
    db: Database,
    exam_schedule_id: int,
    course_ids: List[int],
    classroom_ids: List[int],
    time_limit_seconds: int = 300
) -> Tuple[bool, Optional[Dict]]:

    try:
        scheduler = ExamScheduler(db, exam_schedule_id)
        scheduler.prepare_data(course_ids, classroom_ids)
        
        success = scheduler.solve(time_limit_seconds=time_limit_seconds)
        
        if success:
            scheduler.save_solution()
            stats = scheduler.get_statistics()
            return True, stats
        else:
            stats = scheduler.get_statistics()
            return False, stats
    
    except Exception as e:
        logger.error(f"Sınav zamanlama hatası: {e}", exc_info=True)
        return False, None
