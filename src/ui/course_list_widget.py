from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTableWidget, QTableWidgetItem, QLineEdit, QComboBox,
    QLabel, QMessageBox, QFileDialog, QHeaderView, QDialog,
    QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from src.core.db_raw import get_db
import csv
import logging

logger = logging.getLogger(__name__)


class CourseListWidget(QWidget):
    
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.db = get_db()
        self.courses = []
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("📚 Ders Listesi")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)
        
        top_bar = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Ders kodu veya adı ile ara...")
        self.search_input.textChanged.connect(self.filter_table)
        self.search_input.setMinimumWidth(300)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #dcdde1;
                border-radius: 5px;
                padding: 7px;
                color: #2c3e50;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
            }
        """)
        top_bar.addWidget(self.search_input)

        dept_label = QLabel("Bölüm:")
        dept_label.setStyleSheet("color: #34495e; font-weight: bold;")
        top_bar.addWidget(dept_label)
        self.department_filter = QComboBox()
        self.department_filter.addItem("Tümü", None)
        self.load_departments()
        self.department_filter.currentIndexChanged.connect(self.filter_table)
        self.department_filter.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 1px solid #dcdde1;
                border-radius: 5px;
                padding: 7px;
                color: #2c3e50;
            }
        """)
        top_bar.addWidget(self.department_filter)

        class_label = QLabel("Sınıf:")
        class_label.setStyleSheet("color: #34495e; font-weight: bold;")
        top_bar.addWidget(class_label)
        self.class_filter = QComboBox()
        self.class_filter.addItems(["Tümü", "1", "2", "3", "4"])
        self.class_filter.currentIndexChanged.connect(self.filter_table)
        self.class_filter.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 1px solid #dcdde1;
                border-radius: 5px;
                padding: 7px;
                color: #2c3e50;
            }
        """)
        top_bar.addWidget(self.class_filter)

        type_label = QLabel("Tür:")
        type_label.setStyleSheet("color: #34495e; font-weight: bold;")
        top_bar.addWidget(type_label)
        self.type_filter = QComboBox()
        self.type_filter.addItems(["Tümü", "Zorunlu", "Seçmeli"])
        self.type_filter.currentIndexChanged.connect(self.filter_table)
        self.type_filter.setStyleSheet("""
            QComboBox {
                background-color: white;
                border: 1px solid #dcdde1;
                border-radius: 5px;
                padding: 7px;
                color: #2c3e50;
            }
        """)
        top_bar.addWidget(self.type_filter)

        top_bar.addStretch()

        clear_btn = QPushButton("🗑️ Listeyi Sıfırla")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        clear_btn.clicked.connect(self.clear_all_courses)
        top_bar.addWidget(clear_btn)

        refresh_btn = QPushButton("🔄 Yenile")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #7f8c8d; }
        """)
        refresh_btn.clicked.connect(self.load_data)
        top_bar.addWidget(refresh_btn)

        export_btn = QPushButton("📥 CSV İndir")
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #229954; }
        """)
        export_btn.clicked.connect(self.export_to_csv)
        top_bar.addWidget(export_btn)

        layout.addLayout(top_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Ders Kodu", "Ders Adı", "Eğitmen", "Bölüm",
            "Sınıf", "Tür"
        ])

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #dcdde1;
                border-radius: 5px;
                background-color: #ffffff;
            }
            QTableWidget::item {
                padding: 8px;
                color: #2c3e50;
            }
            QTableWidget::item:alternate {
                background-color: #f8f9fa;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QHeaderView::section {
                background-color: #ecf0f1;
                padding: 10px;
                border: none;
                font-weight: bold;
                color: #2c3e50;
            }
        """)

        self.table.cellClicked.connect(self.show_course_students)

        layout.addWidget(self.table)

        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: #566573; font-size: 12px;")
        layout.addWidget(self.info_label)

        self.setLayout(layout)

    def load_departments(self):
        try:
            dept_rows = self.db.fetch_all(
                "SELECT id, name FROM departments ORDER BY name"
            )
            departments = [dict(row) for row in dept_rows]

            if self.current_user['role'] == 'admin':
                for dept in departments:
                    self.department_filter.addItem(dept['name'], dept['id'])
            else:
                dept_row = self.db.fetch_one(
                    "SELECT id, name FROM departments WHERE id = ?",
                    (self.current_user['department_id'],)
                )
                if dept_row:
                    dept = dict(dept_row)
                    self.department_filter.addItem(dept['name'], dept['id'])
                    self.department_filter.setCurrentIndex(1)
                    self.department_filter.setEnabled(False)

        except Exception as e:
            logger.error(f"Bölümler yüklenirken hata: {str(e)}")

    def load_data(self):
        try:
            if self.current_user['role'] == 'coordinator':
                rows = self.db.fetch_all("""
                    SELECT c.*, d.name as department_name, d.code as department_code
                    FROM courses c
                    JOIN departments d ON c.department_id = d.id
                    WHERE c.department_id = ?
                    ORDER BY c.code
                """, (self.current_user['department_id'],))
            else:
                rows = self.db.fetch_all("""
                    SELECT c.*, d.name as department_name, d.code as department_code
                    FROM courses c
                    JOIN departments d ON c.department_id = d.id
                    ORDER BY c.code
                """)

            self.courses = [dict(row) for row in rows]

            self.filter_table()

            logger.info(f"✓ {len(self.courses)} ders yüklendi")

        except Exception as e:
            logger.error(f"Dersler yüklenirken hata: {str(e)}")
            QMessageBox.critical(self, "Hata", f"Dersler yüklenemedi:\n{str(e)}")

    def filter_table(self):
        search_text = self.search_input.text().lower()
        department_id = self.department_filter.currentData()
        class_level = self.class_filter.currentText()
        course_type = self.type_filter.currentText()

        filtered_courses = []
        for course in self.courses:
            if search_text:
                if (search_text not in course['code'].lower() and
                    search_text not in course['name'].lower()):
                    continue
            if department_id and course['department_id'] != department_id:
                continue
            if class_level != "Tümü":
                if not course.get('class_level') or str(course['class_level']) != class_level:
                    continue
            if course_type == "Zorunlu" and not course['is_mandatory']:
                continue
            elif course_type == "Seçmeli" and course['is_mandatory']:
                continue

            filtered_courses.append(course)

        # Tabloyu doldur
        self.populate_table(filtered_courses)

    def populate_table(self, courses):
        self.table.setRowCount(len(courses))

        for row, course in enumerate(courses):
            code_item = QTableWidgetItem(course['code'])
            code_item.setData(Qt.ItemDataRole.UserRole, course['id'])
            self.table.setItem(row, 0, code_item)

            self.table.setItem(row, 1, QTableWidgetItem(course['name']))

            instructor = course['instructor'] if course.get('instructor') else "-"
            self.table.setItem(row, 2, QTableWidgetItem(instructor))

            dept_name = course.get('department_code', '-')
            self.table.setItem(row, 3, QTableWidgetItem(dept_name))

            class_level = str(course['class_level']) if course.get('class_level') else "-"
            class_item = QTableWidgetItem(class_level)
            class_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, class_item)

            course_type = "Zorunlu" if course['is_mandatory'] else "Seçmeli"
            type_item = QTableWidgetItem(course_type)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if course['is_mandatory']:
                type_item.setBackground(QColor("#e8f5e9"))
                type_item.setForeground(QColor("#2e7d32"))
            else:
                type_item.setBackground(QColor("#fff3e0"))
                type_item.setForeground(QColor("#e65100"))
            self.table.setItem(row, 5, type_item)

        total = len(self.courses)
        shown = len(courses)
        self.info_label.setText(f"Toplam {total} ders • {shown} ders gösteriliyor")

    def show_course_students(self, row, column):
        course_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        course_row = self.db.fetch_one("""
            SELECT c.*, d.name as department_name, d.code as department_code
            FROM courses c
            JOIN departments d ON c.department_id = d.id
            WHERE c.id = ?
        """, (course_id,))

        if not course_row:
            return

        course = dict(course_row)

        student_rows = self.db.fetch_all("""
            SELECT s.* FROM students s
            JOIN student_courses sc ON s.id = sc.student_id
            WHERE sc.course_id = ?
            ORDER BY s.student_number
        """, (course['id'],))

        students = [dict(row) for row in student_rows]

        dialog = QDialog(self)
        dialog.setWindowTitle("Ders Detayları")
        dialog.setMinimumWidth(700)
        dialog.setMinimumHeight(600)
        dialog.setStyleSheet("background-color: #f5f6f7;")

        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("📚 Ders Bilgileri")
        title.setStyleSheet("""
            font-size: 18px; 
            font-weight: bold; 
            color: #2c3e50;
        """)
        layout.addWidget(title)

        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)

        course_info = f"""
<p style='margin: 3px 0; font-size: 13px; color: #2c3e50;'><b>Ders:</b> {course['code']} - {course['name']}</p>
<p style='margin: 3px 0; font-size: 13px; color: #2c3e50;'><b>Eğitmen:</b> {course.get('instructor') or '-'}</p>
<p style='margin: 3px 0; font-size: 13px; color: #2c3e50;'><b>Bölüm:</b> {course.get('department_name', '-')}</p>
<p style='margin: 3px 0; font-size: 13px; color: #2c3e50;'><b>Sınıf:</b> {course.get('class_level') or '-'}</p>
<p style='margin: 3px 0; font-size: 13px; color: #2c3e50;'><b>Tür:</b> {'Zorunlu' if course['is_mandatory'] else 'Seçmeli'}</p>
        """
        info_label = QLabel(course_info)
        info_label.setTextFormat(Qt.TextFormat.RichText)
        info_layout.addWidget(info_label)
        layout.addWidget(info_frame)

        students_title = QLabel(f"👥 Dersi Alan Öğrenciler ({len(students)} öğrenci):")
        students_title.setStyleSheet("""
            font-size: 15px; 
            font-weight: bold; 
            color: #2c3e50; 
            margin-top: 10px;
        """)
        layout.addWidget(students_title)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #dee2e6;
                border-radius: 5px;
            }
        """)

        students_widget = QWidget()
        students_widget.setStyleSheet("background-color: #ffffff;")
        students_layout = QVBoxLayout(students_widget)
        students_layout.setSpacing(5)
        students_layout.setContentsMargins(10, 10, 10, 10)

        if students:
            for i, student in enumerate(students, 1):
                student_label = QLabel(f"{i}. <b>{student['student_number']}</b> - {student['full_name']}")
                student_label.setTextFormat(Qt.TextFormat.RichText)
                student_label.setStyleSheet("""
                    QLabel {
                        padding: 8px;
                        border-bottom: 1px solid #f0f0f0;
                        color: #34495e;
                        font-size: 13px;
                    }
                """)
                students_layout.addWidget(student_label)
        else:
            no_students_label = QLabel("Bu dersi alan öğrenci bulunmamaktadır.")
            no_students_label.setStyleSheet("""
                color: #566573; 
                font-style: italic; 
                padding: 20px;
            """)
            students_layout.addWidget(no_students_label)

        students_layout.addStretch()
        scroll_area.setWidget(students_widget)
        layout.addWidget(scroll_area)

        close_btn = QPushButton("Kapat")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 10px 30px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        close_btn.clicked.connect(dialog.accept)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        dialog.exec()

    def export_to_csv(self):
        if not self.courses:
            QMessageBox.warning(self, "Uyarı", "Dışa aktarılacak ders bulunamadı.")
            return

        try:
            dept_code = "tum"
            if self.current_user['role'] == 'coordinator':
                dept_row = self.db.fetch_one(
                    "SELECT code FROM departments WHERE id = ?",
                    (self.current_user['department_id'],)
                )
                if dept_row:
                    dept = dict(dept_row)
                    dept_code = dept['code'].lower()

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "CSV Olarak Kaydet",
                f"ders_listesi_{dept_code}.csv",
                "CSV Files (*.csv)"
            )

            if not file_path:
                return

            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)

                writer.writerow([
                    "Ders Kodu", "Ders Adı", "Eğitmen", "Bölüm",
                    "Sınıf", "Tür"
                ])

                for course in self.courses:
                    writer.writerow([
                        course['code'],
                        course['name'],
                        course.get('instructor') or "",
                        course.get('department_code', ""),
                        course.get('class_level') or "",
                        "Zorunlu" if course['is_mandatory'] else "Seçmeli"
                    ])

            QMessageBox.information(
                self,
                "Başarılı",
                f"✓ {len(self.courses)} ders CSV olarak kaydedildi:\n{file_path}"
            )
            logger.info(f"✓ Ders listesi export edildi: {file_path}")

        except Exception as e:
            logger.error(f"CSV export hatası: {str(e)}")
            QMessageBox.critical(self, "Hata", f"CSV kaydedilemedi:\n{str(e)}")
    
    def clear_all_courses(self):
        reply = QMessageBox.question(
            self,
            "Dersleri Sil",
            "⚠️ TÜM DERSLERİ SİLMEK İSTEDİĞİNİZDEN EMİN MİSİNİZ?\n\n"
            "Bu işlem GERİ ALINAMAZ!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            count_row = self.db.fetch_one("SELECT COUNT(*) as cnt FROM courses")
            deleted_count = count_row['cnt'] if count_row else 0
            
            self.db.execute("DELETE FROM seating_assignments WHERE exam_session_id IN (SELECT id FROM exam_sessions WHERE exam_id IN (SELECT id FROM exams WHERE course_id IN (SELECT id FROM courses)))")
            self.db.execute("DELETE FROM exam_proctors WHERE exam_session_id IN (SELECT id FROM exam_sessions WHERE exam_id IN (SELECT id FROM exams WHERE course_id IN (SELECT id FROM courses)))")
            self.db.execute("DELETE FROM exam_sessions WHERE exam_id IN (SELECT id FROM exams WHERE course_id IN (SELECT id FROM courses))")
            self.db.execute("DELETE FROM exams WHERE course_id IN (SELECT id FROM courses)")
            self.db.execute("DELETE FROM student_courses")
            self.db.execute("DELETE FROM courses")
            self.load_data()
            
            QMessageBox.information(
                self,
                "Başarılı",
                f"✓ {deleted_count} ders başarıyla silindi!\n\n"
                "Tüm ilişkili kayıtlar (öğrenci-ders, sınavlar, oturma planları) da temizlendi."
            )
            logger.info(f"✓ Tüm dersler ve ilişkili kayıtlar silindi ({deleted_count} ders)")
            
        except Exception as e:
            logger.error(f"Ders silme hatası: {str(e)}")
            QMessageBox.critical(self, "Hata", f"Dersler silinirken hata:\n{str(e)}")

    def closeEvent(self, event):
        event.accept()