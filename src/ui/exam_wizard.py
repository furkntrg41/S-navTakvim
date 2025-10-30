 
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QWizard, QWizardPage, QDateEdit, QSpinBox, QListWidget,
    QTextEdit, QMessageBox, QCheckBox, QListWidgetItem
)
from PyQt6.QtCore import Qt, QDate
from src.core.db_raw import Database
from src.core.scheduler import schedule_exams
from datetime import datetime, timedelta
import logging
from src.utils.error_handler import (
    AppException, DatabaseException, ValidationException,
    validate_input, show_error_dialog, show_info_dialog, log_operation
)

logger = logging.getLogger(__name__)


class ExamWizard(QWizard):
    
    def __init__(self, current_user, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        
        self.selected_courses = []
        self.selected_classrooms = []
        self.course_durations = {}

        self.setWindowTitle("📅 Sınav Programı Oluştur")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setMinimumSize(700, 500)

        self.addPage(DateSelectionPage(self.current_user))
        self.addPage(ParametersPage(self.current_user))
        self.addPage(CourseSelectionPage(self.current_user, self))
        self.addPage(ClassroomSelectionPage(self.current_user, self))
        self.addPage(SummaryPage(self.current_user, self))

        self.button(QWizard.WizardButton.FinishButton).clicked.connect(self.on_finish_clicked)

    def on_finish_clicked(self):
        try:
            log_operation("Sınav Programı Oluşturma Başladı")

            logger.info("=" * 60)
            logger.info("SINAV PROGRAMI WIZARD - FINISH BASILDI")
            logger.info("=" * 60)

            self.create_exam_schedule()
        except Exception as e:
            logger.error(f"Wizard finish hatası: {e}", exc_info=True)
            show_error_dialog(self, "Hata", f"Sınav programı oluşturulamadı:\n{str(e)}")

    def create_exam_schedule(self):
        try:
            start_date = self.field("start_date")
            end_date = self.field("end_date")
            exam_type = self.field("exam_type")
            default_duration = self.field("default_duration")
            wait_duration = self.field("wait_duration")
            allow_parallel = self.field("allow_parallel")
            exclude_weekends = self.field("exclude_weekends")
            selected_courses = self.selected_courses
            selected_classrooms = self.selected_classrooms
            course_durations = self.course_durations
        except Exception as e:
            logger.error(f"Wizard veri toplama hatası: {e}", exc_info=True)
            show_error_dialog(self, "Hata", f"Wizard verilerinde hata:\n{str(e)}")
            return

        if not selected_courses:
            show_error_dialog(self, "Ders Seçimi Gerekli", "En az bir ders seçmelisiniz!")
            log_operation("Ders seçilmedi", success=False)
            return

        if not selected_classrooms:
            show_error_dialog(self, "Derslik Seçimi Gerekli", "En az bir derslik seçmelisiniz!")
            log_operation("Derslik seçilmedi", success=False)
            return

        logger.info(f"Sınav programı oluşturuluyor...")
        logger.info(f"  Dersler: {len(selected_courses)}")
        logger.info(f"  Özel süre ayarlı ders: {len(course_durations)}")
        logger.info(f"  Derslikler: {len(selected_classrooms)}")
        logger.info(f"  Paralel sınav: {'Evet' if allow_parallel else 'Hayır'}")

        start_date_py = start_date.date().toPyDate()
        end_date_py = end_date.date().toPyDate()

        if exclude_weekends:
            allowed_days = "0,1,2,3,4"
        else:
            allowed_days = "0,1,2,3,4,5,6"

        from src.core.db_raw import Database
        db = Database()

        try:
            exam_schedule_id = db.execute("""
                INSERT INTO exam_schedules 
                (name, start_date, end_date, created_by, allowed_days, 
                 default_exam_duration, default_break_duration, is_finalized)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"{exam_type} Sınavı - {start_date.date().toString('dd.MM.yyyy')}",
                start_date_py.isoformat(),
                end_date_py.isoformat(),
                self.current_user['id'],
                allowed_days,
                default_duration,
                wait_duration,
                False
            ))

            logger.info(f"✓ Sınav programı oluşturuldu: ID={exam_schedule_id}")
            log_operation(f"Sınav Programı DB'ye Kaydedildi: ID={exam_schedule_id}", success=True)

        except Exception as db_error:
            log_operation(f"Sınav Programı DB Hatası: {str(db_error)}", success=False)
            raise

        try:
            logger.info("Otomatik zamanlama başlatılıyor...")
            success_count = self.simple_scheduling(
                exam_schedule_id,
                selected_courses,
                selected_classrooms,
                start_date_py,
                end_date_py,
                default_duration,
                wait_duration,
                exclude_weekends,
                    allow_parallel,
                    course_durations
                )

            show_info_dialog(
                self,
                "Sınav Programı Oluşturuldu ✓",
                f"Sınav programı başarıyla oluşturuldu!\n\n"
                f"📋 Program ID: {exam_schedule_id}\n"
                f"📅 Tarih: {start_date.date().toString('dd.MM.yyyy')} - {end_date.date().toString('dd.MM.yyyy')}\n"
                f"✅ Zamanlanan: {success_count} / {len(selected_courses)} ders\n\n"
                f"Sınav programını görüntülemek için ana menüye dönün."
            )
            log_operation(f"Sınav Programı Tamamlandı: {success_count}/{len(selected_courses)} ders", success=True)

        except Exception as sched_error:
            logger.error(f"Zamanlama hatası: {str(sched_error)}")
            log_operation(f"Zamanlama Hatası: {str(sched_error)}", success=False)

            show_error_dialog(
                self,
                "Zamanlama Başarısız ❌",
                f"Sınav programı oluşturulamadı!\n\n{str(sched_error)}"
            )
            return  # Wizard'ı açık bırak

    def _find_best_classrooms(self, available_classrooms: list, student_count: int) -> list:
        import itertools
        import random

        random.shuffle(available_classrooms)

        for num_rooms in range(1, len(available_classrooms) + 1):
            suitable_combos = []

            for combo in itertools.combinations(available_classrooms, num_rooms):
                total_capacity = sum(r['capacity'] for r in combo)
                if total_capacity >= student_count:
                    wasted_space = total_capacity - student_count
                    suitable_combos.append((combo, wasted_space))

            if suitable_combos:
                min_waste = min(wasted_space for combo, wasted_space in suitable_combos)
                best_combos = [combo for combo, wasted_space in suitable_combos if wasted_space == min_waste]
                
                return list(random.choice(best_combos))

        return []

    def simple_scheduling(self, exam_schedule_id, course_ids, classroom_ids,
                          start_date, end_date, default_duration, wait_duration,
                          exclude_weekends=True, allow_parallel=True, course_durations=None):
        from src.core.db_raw import Database
        from datetime import timedelta, datetime, time
        from collections import defaultdict

        db = Database()
        course_durations = course_durations or {}
        
        logger.info(f"🔄 DİNAMİK ZAMANLAMA Başlatılıyor:")
        logger.info(f"  📚 Ders sayısı: {len(course_ids)}")
        logger.info(f"  ⏱️ Varsayılan süre: {default_duration} dk + {wait_duration} dk bekleme")
        logger.info(f"  🔧 Özel süre ayarlı ders: {len(course_durations)}")
        logger.info(f"  ⚡ Paralel sınav: {'EVET' if allow_parallel else 'HAYIR'}")

        DAY_START_TIME = time(9, 0)
        DAY_END_TIME = time(21, 0)

        courses_data = []
        for course_id in course_ids:
            course_row = db.fetch_one("SELECT * FROM courses WHERE id = ?", (course_id,))
            if course_row:
                course = dict(course_row)
                student_count_row = db.fetch_one("SELECT COUNT(*) as cnt FROM student_courses WHERE course_id = ?",
                                                 (course_id,))
                student_count = student_count_row['cnt'] if student_count_row else 0
                
                duration = course_durations.get(course_id, default_duration)
                
                courses_data.append({
                    'id': course_id,
                    'code': course['code'],
                    'name': course['name'],
                    'student_count': student_count,
                    'class_level': course.get('class_level'),
                    'duration': duration
                })
                logger.info(f"  • {course['code']}: {student_count} öğrenci, {duration} dk")
                
        courses_data.sort(key=lambda x: x['student_count'], reverse=True)

        if not classroom_ids:
            raise Exception("Hiç derslik seçilmedi!")
        
        placeholders = ','.join(['?' for _ in classroom_ids])
        classroom_rows = db.fetch_all(
            f"SELECT id, code, capacity, seating_arrangement FROM classrooms WHERE id IN ({placeholders})",
            tuple(classroom_ids))

        classrooms = []
        for room_data in classroom_rows:
            room = dict(room_data)
            total_capacity = room.get('capacity', 0)
            seating_arrangement_val = room.get('seating_arrangement', 1)
            effective_capacity = total_capacity
            if seating_arrangement_val == 3:
                effective_capacity = (total_capacity // 3) * 2
            elif seating_arrangement_val == 2:
                effective_capacity = total_capacity // 2
            room['capacity'] = effective_capacity
            classrooms.append(room)

        total_classroom_capacity = sum(r['capacity'] for r in classrooms)
        max_student_count = max(c['student_count'] for c in courses_data) if courses_data else 0
        
        if total_classroom_capacity < max_student_count:
            raise Exception(
                f"❌ Kapasite Yetersiz! Toplam kapasite ({total_classroom_capacity}), en kalabalık sınavı ({max_student_count} öğrenci) karşılamıyor.")

        student_schedule = defaultdict(list)
        classroom_schedule = {c['id']: [] for c in classrooms}
        class_level_daily_count = defaultdict(int)
        class_level_used_dates = defaultdict(set)
        scheduled_courses = []
        failed_courses = []

        for course in courses_data:
            course_id = course['id']
            course_code = course['code']
            student_count = course['student_count']
            duration = course['duration']
            class_level = course.get('class_level')
            
            logger.info(f"\n📝 Zamanlaniyor: {course_code} ({student_count} öğr, {duration}dk)")
            
            student_rows = db.fetch_all("SELECT student_id FROM student_courses WHERE course_id = ?", (course_id,))
            course_student_ids = {row['student_id'] for row in student_rows}
            
            scheduled = False
            current_date = start_date
            
            while current_date <= end_date and not scheduled:
                if exclude_weekends and current_date.weekday() >= 5:
                    current_date += timedelta(days=1)
                    continue
                
                if class_level and current_date in class_level_used_dates.get(class_level, set()):
                    if class_level_daily_count.get((class_level, current_date), 0) >= 2:
                        current_date += timedelta(days=1)
                        continue
                
                if class_level and class_level_daily_count.get((class_level, current_date), 0) >= 2:
                    current_date += timedelta(days=1)
                    continue
                
                current_time = DAY_START_TIME
                attempted_times = set()
                
                while current_time < DAY_END_TIME and not scheduled:
                    current_dt = datetime.combine(current_date, current_time)
                    exam_end_dt = current_dt + timedelta(minutes=duration)
                    
                    if exam_end_dt.time() > DAY_END_TIME:
                        break
                    
                    time_key = current_time.strftime('%H:%M')
                    if time_key in attempted_times:
                        current_time = (current_dt + timedelta(minutes=15)).time()
                        continue
                    attempted_times.add(time_key)
                    
                    student_conflict = False
                    
                    for sid in course_student_ids:
                        for (start, end) in student_schedule[sid]:
                            end_with_wait = end + timedelta(minutes=wait_duration)
                            
                            if current_dt < end_with_wait and exam_end_dt > start:
                                student_conflict = True
                                break
                        if student_conflict:
                            break
                    
                    if student_conflict:
                        if allow_parallel:
                            earliest_available = None
                            for sid in course_student_ids:
                                for (start, end) in student_schedule[sid]:
                                    end_with_wait = end + timedelta(minutes=wait_duration)
                                    if current_dt < end_with_wait and exam_end_dt > start:
                                        if earliest_available is None or end_with_wait > earliest_available:
                                            earliest_available = end_with_wait
                            
                            if earliest_available and earliest_available.time() < DAY_END_TIME:
                                current_time = earliest_available.time()
                            else:
                                break
                        else:
                            next_time = None
                            for sid in course_student_ids:
                                for (start, end) in student_schedule[sid]:
                                    if start <= current_dt < end:
                                        end_with_break = end + timedelta(minutes=wait_duration)
                                        if next_time is None or end_with_break.time() < next_time:
                                            next_time = end_with_break.time()
                            
                            if next_time and next_time < DAY_END_TIME:
                                current_time = next_time
                            else:
                                break
                        continue
                    
                    available_classrooms = []
                    for classroom in classrooms:
                        is_free = True
                        for (start, end) in classroom_schedule[classroom['id']]:
                            if current_dt < end and exam_end_dt > start:
                                is_free = False
                                break
                        if is_free:
                            available_classrooms.append(classroom)
                    
                    total_available_capacity = sum(c['capacity'] for c in available_classrooms)
                    
                    if total_available_capacity < student_count:
                        if allow_parallel:
                            current_time = (current_dt + timedelta(minutes=15)).time()
                        else:
                            next_time = None
                            for classroom in classrooms:
                                for (start, end) in classroom_schedule[classroom['id']]:
                                    if start <= current_dt < end:
                                        end_with_break = end + timedelta(minutes=wait_duration)
                                        if next_time is None or end_with_break.time() < next_time:
                                            next_time = end_with_break.time()
                            
                            if next_time and next_time < DAY_END_TIME:
                                current_time = next_time
                            else:
                                break
                        continue
                    
                    selected_classrooms = self._find_best_classrooms(available_classrooms, student_count)
                    
                    try:
                        start_time_str = current_dt.strftime('%H:%M:%S')
                        exam_id = db.execute(
                            "INSERT INTO exams (schedule_id, course_id, exam_date, start_time, duration, student_count, status) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (exam_schedule_id, course_id, current_date.isoformat(),
                             start_time_str, duration, student_count, 'scheduled'))
                        
                        for sid in course_student_ids:
                            student_schedule[sid].append((current_dt, exam_end_dt))
                        
                        remaining_students = student_count
                        for room in selected_classrooms:
                            allocated = min(remaining_students, room['capacity'])
                            db.execute(
                                "INSERT INTO exam_sessions (exam_id, classroom_id, allocated_seats) VALUES (?, ?, ?)",
                                (exam_id, room['id'], allocated))
                            
                            classroom_schedule[room['id']].append((current_dt, exam_end_dt))
                            remaining_students -= allocated
                            
                            if remaining_students <= 0:
                                break
                        
                        if class_level:
                            class_level_daily_count[(class_level, current_date)] += 1
                            class_level_used_dates[class_level].add(current_date)
                        
                        scheduled = True
                        scheduled_courses.append(course)
                        
                        classroom_names = ', '.join([c['code'] for c in selected_classrooms])
                        logger.info(
                            f"  ✅ {course_code}: {current_date.strftime('%d.%m.%Y')} {start_time_str} "
                            f"({duration}dk) → {classroom_names}"
                        )
                        
                    except Exception as e:
                        logger.error(f"  ❌ DB Hatası: {e}", exc_info=True)
                        raise
                
                if not scheduled:
                    current_date += timedelta(days=1)
            
            if not scheduled:
                failed_courses.append(course)
                logger.warning(f"  ❌ {course_code}: Uygun zaman bulunamadı!")
        
        success_count = len(scheduled_courses)
        failed_count = len(failed_courses)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ ZAMANLAMA TAMAMLANDI")
        logger.info(f"  Başarılı: {success_count}/{len(courses_data)}")
        logger.info(f"  Başarısız: {failed_count}/{len(courses_data)}")
        logger.info(f"{'='*60}\n")
        
        if failed_courses:
            failed_list = '\n'.join([f"  • {c['code']} ({c['student_count']} öğr, {c['duration']}dk)" 
                                    for c in failed_courses])
            raise Exception(
                f"❌ Zamanlama Kısmen Başarısız!\n\n"
                f"Başarısız {failed_count} ders:\n{failed_list}\n\n"
                f"Öneriler:\n"
                f"• Tarih aralığını genişletin\n"
                f"• Daha fazla derslik seçin\n"
                f"• Paralel sınav seçeneğini aktif edin\n"
                f"• Sınav sürelerini kısaltın"
            )
        
        return success_count

        # 2. ZAMANLAMA TAKİP YAPILARI
        student_schedule = defaultdict(list)
        classroom_schedule = {c['id']: [] for c in classrooms}
        class_level_date_usage = defaultdict(int)
        unscheduled_courses = list(courses_data)

        # 3. ANA ZAMANLAMA DÖNGÜSÜ (Zaman Dilimi Odaklı)
        current_date = start_date
        while current_date <= end_date and unscheduled_courses:
            if exclude_weekends and current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue

            possible_start_time = DAY_START_TIME
            while possible_start_time < DAY_END_TIME and unscheduled_courses:

                current_dt = datetime.combine(current_date, possible_start_time)

                # --- BU ZAMAN DİLİMİ İÇİN PARALEL ATAMA MOTORU ---
                available_classrooms_in_slot = [r for r in classrooms if not any(
                    current_dt < end and start < (current_dt + timedelta(minutes=exam_duration)) for start, end in
                    classroom_schedule.get(r['id'], []))]

                while True:
                    if not available_classrooms_in_slot:
                        break

                    course_to_schedule = None

                    for course_data in unscheduled_courses:
                        class_level = course_data.get('class_level')
                        if class_level and class_level_date_usage.get((class_level, current_date),
                                                                      0) >= MAX_EXAMS_PER_DAY_PER_LEVEL:
                            continue

                        student_rows = db.fetch_all("SELECT student_id FROM student_courses WHERE course_id = ?",
                                                    (course_data['id'],))
                        course_student_ids = {row['student_id'] for row in student_rows}

                        has_student_conflict = any(
                            current_dt < (end + timedelta(minutes=wait_duration)) and start < (
                                        current_dt + timedelta(minutes=exam_duration))
                            for sid in course_student_ids
                            for start, end in student_schedule.get(sid, [])
                        )
                        if has_student_conflict:
                            continue

                        if sum(r['capacity'] for r in available_classrooms_in_slot) >= course_data['student_count']:
                            course_to_schedule = course_data
                            break

                    if course_to_schedule:
                        student_count = course_to_schedule['student_count']
                        selected_classrooms = self._find_best_classrooms(available_classrooms_in_slot, student_count)

                        if selected_classrooms:
                            try:
                                start_time_str = current_dt.strftime('%H:%M:%S')
                                exam_id = db.execute(
                                    "INSERT INTO exams (schedule_id, course_id, exam_date, start_time, duration, student_count, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                    (exam_schedule_id, course_to_schedule['id'], current_date.isoformat(),
                                     start_time_str, exam_duration, student_count, 'scheduled'))

                                exam_end_dt = current_dt + timedelta(minutes=exam_duration)

                                student_rows = db.fetch_all(
                                    "SELECT student_id FROM student_courses WHERE course_id = ?",
                                    (course_to_schedule['id'],))
                                for row in student_rows: student_schedule[row['student_id']].append(
                                    (current_dt, exam_end_dt))

                                remaining_students = student_count
                                for room in selected_classrooms:
                                    allocated = min(remaining_students, room['capacity'])
                                    db.execute(
                                        "INSERT INTO exam_sessions (exam_id, classroom_id, allocated_seats) VALUES (?, ?, ?)",
                                        (exam_id, room['id'], allocated))
                                    classroom_schedule[room['id']].append((current_dt, exam_end_dt))
                                    available_classrooms_in_slot.remove(room)
                                    remaining_students -= allocated

                                class_level = course_to_schedule.get('class_level')
                                if class_level: class_level_date_usage[(class_level, current_date)] += 1

                                unscheduled_courses.remove(course_to_schedule)
                                logger.info(
                                    f"✓ Paralel Atama: {course_to_schedule['code']} -> {current_date.strftime('%d.%m')} {start_time_str} ({len(selected_classrooms)} derslik kullanıldı)")

                            except Exception as e:
                                logger.error(f"❌ DB Hatası - {course_to_schedule['code']}: {e}", exc_info=True)
                                raise
                        else:
                            break
                    else:
                        break

                possible_start_time = (current_dt + timedelta(minutes=15)).time()

            current_date += timedelta(days=1)

        # 4. SONUÇLARI RAPORLAMA
        logger.info(
            f"✅ Zamanlama tamamlandı: {len(courses_data) - len(unscheduled_courses)}/{len(courses_data)} ders yerleştirildi.")

        if unscheduled_courses:
            warnings = [
                f"❌ {c['code']} (Sınıf: {c.get('class_level')}, Öğr: {c['student_count']}): Uygun zaman bulunamadı!" for
                c in unscheduled_courses]
            for warning in warnings: logger.warning(warning)
            failed_list = "\n".join(warnings)
            raise Exception(
                f"❌ Zamanlama Kısmen Başarısız!\n\nBaşarısız olan {len(unscheduled_courses)} ders:\n{failed_list}\n\nÖneri: Tarih aralığını genişletin veya daha fazla derslik seçin.")

        return len(courses_data)




    def run_scheduling(self, exam_schedule_id: int, course_ids: list, classroom_ids: list):
        
        try:
            logger.info("🔄 Zamanlama başlatılıyor...")
            logger.info(f"  ExamSchedule ID: {exam_schedule_id}")
            logger.info(f"  Ders sayısı: {len(course_ids)}")
            logger.info(f"  Derslik sayısı: {len(classroom_ids)}")

            # Zamanlama motorunu çalıştır
            success, stats = schedule_exams(
                db=self.db,
                exam_schedule_id=exam_schedule_id,
                course_ids=course_ids,
                classroom_ids=classroom_ids,
                time_limit_seconds=300  # 5 dakika
            )

            logger.info(f"Zamanlama tamamlandı: success={success}")

            if success:
                logger.info("✓ Zamanlama başarılı!")
                QMessageBox.information(
                    self,
                    "Başarılı",
                    f"✓ Sınav programı başarıyla oluşturuldu!\n\n"
                    f"📊 İstatistikler:\n"
                    f"  • Zamanlanan Ders: {stats['toplam_ders']}\n"
                    f"  • Kullanılan Derslik: {stats['toplam_derslik']}\n"
                    f"  • Toplam Slot: {stats['toplam_slot']}\n"
                    f"  • Çözüm Süresi: {stats['cozum_suresi']:.2f} saniye\n"
                    f"  • Durum: {stats['durum']}\n\n"
                    f"Sınav programını görüntülemek için ana menüye dönün."
                )
            else:
                logger.warning("⚠ Zamanlama başarısız - Geçerli çözüm bulunamadı")
                QMessageBox.warning(
                    self,
                    "Uyarı",
                    "⚠️ Geçerli bir zamanlama bulunamadı!\n\n"
                    "Olası nedenler:\n"
                    "• Derslik kapasitesi yetersiz\n"
                    "• Zaman dilimi sayısı yetersiz\n"
                        "• Öğrenci çakışması çözülemedi\n\n"
                        "Lütfen parametreleri gözden geçirip tekrar deneyin."
                    )

        except Exception as e:
            logger.error(f"Zamanlama hatası: {str(e)}", exc_info=True)
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Hata",
                f"Zamanlama sırasında hata oluştu:\n\n{str(e)}\n\n"
                f"Detaylar log dosyasında."
            )


class DateSelectionPage(QWizardPage):
    

    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user

        self.setTitle("📆 Sınav Tarihleri")
        self.setSubTitle("Sınav programı için başlangıç ve bitiş tarihlerini seçin.")

        layout = QVBoxLayout()

        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("Başlangıç Tarihi:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(7))
        self.start_date.setDisplayFormat("dd.MM.yyyy")
        start_layout.addWidget(self.start_date)
        start_layout.addStretch()
        layout.addLayout(start_layout)

        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("Bitiş Tarihi:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate().addDays(21))
        self.end_date.setDisplayFormat("dd.MM.yyyy")
        end_layout.addWidget(self.end_date)
        end_layout.addStretch()
        layout.addLayout(end_layout)

        self.exclude_weekends = QCheckBox("⛔ Cumartesi ve Pazar günlerini hariç tut")
        self.exclude_weekends.setChecked(True)
        layout.addWidget(self.exclude_weekends)

        info = QLabel(
            "💡 <b>İpucu:</b> Genellikle sınav dönemi 2-3 hafta sürer. "
            "Hafta sonları genellikle sınav yapılmaz."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #7f8c8d; margin-top: 20px; padding: 10px; background-color: #ecf0f1; border-radius: 5px;")
        layout.addWidget(info)

        layout.addStretch()
        self.setLayout(layout)

        self.registerField("start_date", self.start_date)
        self.registerField("end_date", self.end_date)
        self.registerField("exclude_weekends", self.exclude_weekends)

    def validatePage(self):
        if self.start_date.date() >= self.end_date.date():
            QMessageBox.warning(
                self,
                "Geçersiz Tarih",
                "Bitiş tarihi başlangıç tarihinden sonra olmalıdır!"
            )
            return False

        days_diff = self.start_date.date().daysTo(self.end_date.date())
        if days_diff < 5:
            QMessageBox.warning(
                self,
                "Yetersiz Süre",
                "Sınav programı için en az 5 günlük süre gereklidir!"
            )
            return False

        return True


class ParametersPage(QWizardPage):
    

    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user

        self.setTitle("⚙️ Sınav Parametreleri")
        self.setSubTitle("Sınav türü, süre ve zamanlama parametrelerini belirleyin.")

        layout = QVBoxLayout()

        from PyQt6.QtWidgets import QComboBox
        exam_type_layout = QHBoxLayout()
        exam_type_layout.addWidget(QLabel("📝 Sınav Türü:"))
        self.exam_type = QComboBox()
        self.exam_type.addItems(["Vize", "Final", "Bütünleme", "Mazeret"])
        self.exam_type.setCurrentIndex(0)
        exam_type_layout.addWidget(self.exam_type)
        exam_type_layout.addStretch()
        layout.addLayout(exam_type_layout)

        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("⏱️ Varsayılan Sınav Süresi:"))
        self.default_duration = QSpinBox()
        self.default_duration.setRange(60, 180)
        self.default_duration.setValue(75)
        self.default_duration.setSingleStep(15)
        self.default_duration.setSuffix(" dakika")
        duration_layout.addWidget(self.default_duration)
        duration_layout.addStretch()
        layout.addLayout(duration_layout)

        wait_layout = QHBoxLayout()
        wait_layout.addWidget(QLabel("🕐 Sınavlar Arası Bekleme:"))
        self.wait_duration = QSpinBox()
        self.wait_duration.setRange(0, 60)
        self.wait_duration.setValue(15)
        self.wait_duration.setSingleStep(5)
        self.wait_duration.setSuffix(" dakika")
        wait_layout.addWidget(self.wait_duration)
        wait_layout.addStretch()
        layout.addLayout(wait_layout)

        self.allow_parallel = QCheckBox("⚡ Sınavlar aynı anda başlayabilir (Paralel Sınav)")
        self.allow_parallel.setChecked(True)
        self.allow_parallel.setToolTip(
            "İşaretli: Farklı derslerin sınavları aynı saatte başlayabilir (daha hızlı zamanlama)\n"
            "İşaretsiz: Bir sınav bitene kadar diğeri başlamaz (daha uzun sürer)"
        )
        layout.addWidget(self.allow_parallel)

        info = QLabel(
            "💡 <b>Bilgilendirme:</b><br>"
            "• <b>Varsayılan Süre:</b> Tüm dersler için geçerli (sonraki adımda ders bazlı değiştirilebilir)<br>"
            "• <b>Bekleme Süresi:</b> Bir sınav bittikten sonra öğrencilerin dinlenmesi için ara<br>"
            "• <b>Paralel Sınav:</b> İşaretli ise, farklı derslerin sınavları aynı saatte başlayabilir<br>"
            "• <b>Zamanlama:</b> Sınav süresi + Bekleme = Bir sonraki sınav başlangıcı<br>"
            "• <b>Örnek:</b> 75dk sınav + 15dk bekleme = 90dk sonra yeni sınav"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #34495e; margin-top: 15px; padding: 12px; background-color: #e8f4f8; border-left: 4px solid #3498db; border-radius: 5px;")
        layout.addWidget(info)

        layout.addStretch()
        self.setLayout(layout)

        self.registerField("exam_type", self.exam_type, "currentText")
        self.registerField("default_duration", self.default_duration)
        self.registerField("wait_duration", self.wait_duration)
        self.registerField("allow_parallel", self.allow_parallel)


class CourseSelectionPage(QWizardPage):
    

    def __init__(self, current_user, wizard_parent):
        super().__init__()
        self.current_user = current_user
        self.wizard_parent = wizard_parent
        self.course_durations = {}

        self.setTitle("📚 Ders Seçimi ve Süre Ayarları")
        self.setSubTitle("Sınava girecek dersleri seçin ve özel süre ayarları yapın")

        from PyQt6.QtWidgets import QSplitter, QGroupBox, QFormLayout
        
        main_layout = QVBoxLayout()
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        button_layout = QHBoxLayout()
        select_all_btn = QPushButton("✓ Tümünü Seç")
        select_all_btn.clicked.connect(self.select_all)
        deselect_all_btn = QPushButton("✗ Tümünü Kaldır")
        deselect_all_btn.clicked.connect(self.deselect_all)
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(deselect_all_btn)
        button_layout.addStretch()
        left_layout.addLayout(button_layout)
        
        left_layout.addWidget(QLabel("<b>Sınava Girecek Dersler:</b>"))
        self.course_list = QListWidget()
        self.course_list.currentItemChanged.connect(self.on_course_selected)
        self.load_courses()
        left_layout.addWidget(self.course_list)
        
        self.info_label = QLabel()
        self.update_info()
        self.course_list.itemChanged.connect(self.update_info)
        left_layout.addWidget(self.info_label)
        
        splitter.addWidget(left_widget)
        
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        duration_group = QGroupBox("⏱️ Özel Sınav Süresi")
        duration_layout = QVBoxLayout()
        
        duration_layout.addWidget(QLabel(
            "<i>Seçili ders için varsayılan süreden farklı bir süre belirleyebilirsiniz.</i>"
        ))
        
        form_layout = QFormLayout()
        
        self.selected_course_label = QLabel("<i>Bir ders seçin</i>")
        self.selected_course_label.setStyleSheet("color: #7f8c8d;")
        form_layout.addRow("Seçili Ders:", self.selected_course_label)
        
        self.default_duration_label = QLabel("75 dakika")
        form_layout.addRow("Varsayılan Süre:", self.default_duration_label)
        
        self.custom_duration = QSpinBox()
        self.custom_duration.setRange(30, 240)
        self.custom_duration.setValue(75)
        self.custom_duration.setSingleStep(15)
        self.custom_duration.setSuffix(" dakika")
        self.custom_duration.setEnabled(False)
        form_layout.addRow("Özel Süre:", self.custom_duration)
        
        duration_layout.addLayout(form_layout)
        
        button_layout2 = QHBoxLayout()
        self.apply_custom_btn = QPushButton("✓ Özel Süre Uygula")
        self.apply_custom_btn.clicked.connect(self.apply_custom_duration)
        self.apply_custom_btn.setEnabled(False)
        self.reset_custom_btn = QPushButton("↺ Varsayılana Dön")
        self.reset_custom_btn.clicked.connect(self.reset_custom_duration)
        self.reset_custom_btn.setEnabled(False)
        button_layout2.addWidget(self.apply_custom_btn)
        button_layout2.addWidget(self.reset_custom_btn)
        duration_layout.addLayout(button_layout2)
        
        duration_layout.addWidget(QLabel("<b>Özel Süre Ayarlanan Dersler:</b>"))
        self.custom_duration_list = QListWidget()
        self.custom_duration_list.setMaximumHeight(150)
        duration_layout.addWidget(self.custom_duration_list)
        
        duration_group.setLayout(duration_layout)
        right_layout.addWidget(duration_group)
        right_layout.addStretch()
        
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 300])
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    def load_courses(self):
        try:
            from src.core.db_raw import Database
            db = Database()

            if self.current_user['role'] == 'coordinator':
                course_rows = db.fetch_all(
                    "SELECT * FROM courses WHERE department_id = ? ORDER BY code",
                    (self.current_user['department_id'],)
                )
            else:
                course_rows = db.fetch_all("SELECT * FROM courses ORDER BY code")

            courses = [dict(row) for row in course_rows]

            for course in courses:
                item = QListWidgetItem(f"{course['code']} - {course['name']}")
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                item.setData(Qt.ItemDataRole.UserRole, course['id'])
                item.setData(Qt.ItemDataRole.UserRole + 1, course)
                self.course_list.addItem(item)

        except Exception as e:
            logger.error(f"Dersler yüklenirken hata: {str(e)}", exc_info=True)

    def on_course_selected(self, current, previous):
        if current and current.checkState() == Qt.CheckState.Checked:
            course = current.data(Qt.ItemDataRole.UserRole + 1)
            course_id = current.data(Qt.ItemDataRole.UserRole)
            
            self.selected_course_label.setText(f"<b>{course['code']} - {course['name']}</b>")
            self.selected_course_label.setStyleSheet("color: #2c3e50;")
            
            default_dur = self.wizard().field("default_duration") or 75
            self.default_duration_label.setText(f"{default_dur} dakika")
            
            if course_id in self.course_durations:
                self.custom_duration.setValue(self.course_durations[course_id])
            else:
                self.custom_duration.setValue(default_dur)
            
            self.custom_duration.setEnabled(True)
            self.apply_custom_btn.setEnabled(True)
            self.reset_custom_btn.setEnabled(course_id in self.course_durations)
        else:
            self.selected_course_label.setText("<i>Bir ders seçin</i>")
            self.selected_course_label.setStyleSheet("color: #7f8c8d;")
            self.custom_duration.setEnabled(False)
            self.apply_custom_btn.setEnabled(False)
            self.reset_custom_btn.setEnabled(False)

    def apply_custom_duration(self):
        current = self.course_list.currentItem()
        if not current:
            return
            
        course_id = current.data(Qt.ItemDataRole.UserRole)
        course = current.data(Qt.ItemDataRole.UserRole + 1)
        custom_dur = self.custom_duration.value()
        default_dur = self.wizard().field("default_duration") or 75
        
        if custom_dur != default_dur:
            self.course_durations[course_id] = custom_dur
            self.reset_custom_btn.setEnabled(True)
            self.update_custom_duration_list()
            QMessageBox.information(self, "Başarılı", 
                f"{course['code']} dersi için özel süre ({custom_dur} dk) kaydedildi!")
        else:
            if course_id in self.course_durations:
                del self.course_durations[course_id]
            self.reset_custom_btn.setEnabled(False)
            self.update_custom_duration_list()

    def reset_custom_duration(self):
        current = self.course_list.currentItem()
        if not current:
            return
            
        course_id = current.data(Qt.ItemDataRole.UserRole)
        course = current.data(Qt.ItemDataRole.UserRole + 1)
        
        if course_id in self.course_durations:
            del self.course_durations[course_id]
            default_dur = self.wizard().field("default_duration") or 75
            self.custom_duration.setValue(default_dur)
            self.reset_custom_btn.setEnabled(False)
            self.update_custom_duration_list()
            QMessageBox.information(self, "Sıfırlandı", 
                f"{course['code']} dersi varsayılan süreye ({default_dur} dk) döndürüldü!")

    def update_custom_duration_list(self):
        self.custom_duration_list.clear()
        if not self.course_durations:
            self.custom_duration_list.addItem("Henüz özel süre ayarlanmadı")
            return
            
        for i in range(self.course_list.count()):
            item = self.course_list.item(i)
            course_id = item.data(Qt.ItemDataRole.UserRole)
            course = item.data(Qt.ItemDataRole.UserRole + 1)
            
            if course_id in self.course_durations:
                dur = self.course_durations[course_id]
                self.custom_duration_list.addItem(
                    f"📝 {course['code']}: {dur} dakika (Varsayılan: {self.wizard().field('default_duration')} dk)"
                )

    def select_all(self):
        for i in range(self.course_list.count()):
            self.course_list.item(i).setCheckState(Qt.CheckState.Checked)
        self.update_info()

    def deselect_all(self):
        for i in range(self.course_list.count()):
            self.course_list.item(i).setCheckState(Qt.CheckState.Unchecked)
        self.update_info()

    def update_info(self):
        selected = sum(1 for i in range(self.course_list.count())
                      if self.course_list.item(i).checkState() == Qt.CheckState.Checked)
        total = self.course_list.count()
        custom_count = len(self.course_durations)
        
        info_text = f"✓ {selected}/{total} ders seçildi"
        if custom_count > 0:
            info_text += f" | ⏱️ {custom_count} derste özel süre var"
        self.info_label.setText(info_text)

    def validatePage(self):
        selected_courses = []
        for i in range(self.course_list.count()):
            item = self.course_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_courses.append(item.data(Qt.ItemDataRole.UserRole))

        if not selected_courses:
            QMessageBox.warning(self, "Ders Seçilmedi", "En az 1 ders seçmelisiniz!")
            return False

        self.wizard_parent.selected_courses = selected_courses
        self.wizard_parent.course_durations = self.course_durations
        return True


class ClassroomSelectionPage(QWizardPage):
    

    def __init__(self, current_user, wizard_parent):
        super().__init__()
        self.current_user = current_user
        self.wizard_parent = wizard_parent

        self.setTitle("🏫 Derslik Seçimi")
        self.setSubTitle("Hangi dersliklerde sınav yapılacak?")

        layout = QVBoxLayout()

        button_layout = QHBoxLayout()
        select_all_btn = QPushButton("✓ Tümünü Seç")
        select_all_btn.clicked.connect(self.select_all)
        deselect_all_btn = QPushButton("✗ Tümünü Kaldır")
        deselect_all_btn.clicked.connect(self.deselect_all)
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(deselect_all_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.classroom_list = QListWidget()
        self.load_classrooms()
        layout.addWidget(self.classroom_list)

        self.info_label = QLabel()
        self.update_info()
        self.classroom_list.itemChanged.connect(self.update_info)
        layout.addWidget(self.info_label)

        self.setLayout(layout)

    def load_classrooms(self):
        try:
            from src.core.db_raw import Database
            db = Database()

            if self.current_user['role'] == 'coordinator':
                classroom_rows = db.fetch_all(
                    "SELECT * FROM classrooms WHERE is_active = 1 AND department_id = ? ORDER BY code",
                    (self.current_user['department_id'],)
                )
            else:
                classroom_rows = db.fetch_all(
                    "SELECT * FROM classrooms WHERE is_active = 1 ORDER BY code"
                )

            classrooms = [dict(row) for row in classroom_rows]

            for classroom in classrooms:
                item = QListWidgetItem(
                    f"{classroom['code']} - Kapasite: {classroom['capacity']} "
                    f"({classroom['rows']}x{classroom['columns']})"
                )
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                item.setData(Qt.ItemDataRole.UserRole, classroom['id'])
                self.classroom_list.addItem(item)

        except Exception as e:
            logger.error(f"Derslikler yüklenirken hata: {str(e)}", exc_info=True)

    def select_all(self):
        for i in range(self.classroom_list.count()):
            self.classroom_list.item(i).setCheckState(Qt.CheckState.Checked)
        self.update_info()

    def deselect_all(self):
        for i in range(self.classroom_list.count()):
            self.classroom_list.item(i).setCheckState(Qt.CheckState.Unchecked)
        self.update_info()

    def update_info(self):
        selected = sum(1 for i in range(self.classroom_list.count())
                      if self.classroom_list.item(i).checkState() == Qt.CheckState.Checked)
        self.info_label.setText(f"✓ {selected} derslik seçildi")

    def validatePage(self):
        selected_classrooms = []
        for i in range(self.classroom_list.count()):
            item = self.classroom_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_classrooms.append(item.data(Qt.ItemDataRole.UserRole))

        if not selected_classrooms:
            QMessageBox.warning(self, "Derslik Seçilmedi", "En az 1 derslik seçmelisiniz!")
            return False

        # Wizard'da sakla
        self.wizard_parent.selected_classrooms = selected_classrooms
        return True


class SummaryPage(QWizardPage):
    

    def __init__(self, current_user, wizard_parent):
        super().__init__()
        self.current_user = current_user
        self.wizard_parent = wizard_parent

        self.setTitle("📋 Özet ve Onay")
        self.setSubTitle("Sınav programı bilgilerini kontrol edin.")

        layout = QVBoxLayout()

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setStyleSheet("""
            QTextEdit {
                background-color: gray;
                border: 1px solid #dcdde1;
                border-radius: 5px;
                padding: 10px;
                font-family: 'Consolas', monospace;
                color: #2c3e50;
            }
        """)
        layout.addWidget(self.summary_text)

        self.setLayout(layout)

    def initializePage(self):
        start_date = self.field("start_date")
        end_date = self.field("end_date")
        default_duration = self.field("default_duration")
        wait_duration = self.field("wait_duration")
        allow_parallel = self.field("allow_parallel")
        selected_courses = self.wizard_parent.selected_courses
        selected_classrooms = self.wizard_parent.selected_classrooms
        course_durations = self.wizard_parent.course_durations

        days = start_date.daysTo(end_date) + 1

        from src.core.db_raw import Database
        db = Database()
        total_capacity = 0

        for classroom_id in selected_classrooms:
            classroom_row = db.fetch_one("SELECT * FROM classrooms WHERE id = ?", (classroom_id,))
            if classroom_row:
                classroom = dict(classroom_row)
                total_capacity += classroom['capacity']
        
        custom_duration_count = len(course_durations)

        summary = f"""
📅 SINAV PROGRAMI ÖZETİ
{'='*50}

📆 Tarih Bilgileri:
   • Başlangıç: {start_date.date().toString('dd.MM.yyyy dddd')}
   • Bitiş: {end_date.date().toString('dd.MM.yyyy dddd')}
   • Toplam Gün: {days} gün

⚙️ Parametreler:
   • Varsayılan Sınav Süresi: {default_duration} dakika
   • Bekleme Süresi: {wait_duration} dakika
   • Paralel Sınav: {'Açık' if allow_parallel else 'Kapalı'}
   • Özel Süre Ayarlı Ders: {custom_duration_count} ders

📚 Dersler:
   • Seçilen Ders Sayısı: {len(selected_courses)} ders

🏫 Derslikler:
   • Seçilen Derslik Sayısı: {len(selected_classrooms)} derslik
   • Toplam Kapasite: {total_capacity} kişi

{'='*50}

✓ Sınav programı otomatik olarak oluşturulacaktır.
  (Zamanlama algoritması tüm kısıtları kontrol edecektir)
        """

        self.summary_text.setPlainText(summary)
