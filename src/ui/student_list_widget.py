from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTableWidget, QTableWidgetItem, QLineEdit, QComboBox,
    QLabel, QMessageBox, QFileDialog, QHeaderView
)
from PyQt6.QtCore import Qt
from src.core.db_raw import get_db
import csv
import logging

logger = logging.getLogger(__name__)


class StudentListWidget(QWidget):
    
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.db = get_db()
        self.students = []
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("👨‍🎓 Öğrenci Listesi")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)
        
        top_bar = QHBoxLayout()
        
        search_label = QLabel("Öğrenci No:")
        search_label.setStyleSheet("color: #34495e; font-weight: bold;")
        top_bar.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Öğrenci no veya adını girin...")
        self.search_input.setMinimumWidth(250)
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

        self.search_input.textChanged.connect(self.filter_table)

        top_bar.addWidget(self.search_input)

        search_btn = QPushButton("🔍 Ara")
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        search_btn.clicked.connect(self.search_student)
        top_bar.addWidget(search_btn)

        top_bar.addSpacing(20)

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
        self.class_filter.addItems(["Tümü", "1", "2", "3", "4", "5"])
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
        clear_btn.clicked.connect(self.clear_all_students)
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
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Öğrenci No", "Ad Soyad", "Bölüm", "Sınıf", "Kayıtlı Ders Sayısı"
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

        self.table.cellDoubleClicked.connect(self.show_student_detail)

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

            if self.current_user['role'] == 'admin':
                for row in dept_rows:
                    dept = dict(row)
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
                    SELECT s.*, 
                           d.name as dept_name, 
                           d.code as dept_code,
                           COUNT(sc.id) as course_count
                    FROM students s
                    JOIN departments d ON s.department_id = d.id
                    LEFT JOIN student_courses sc ON s.id = sc.student_id
                    WHERE s.department_id = ?
                    GROUP BY s.id
                    ORDER BY s.student_number
                """, (self.current_user['department_id'],))
            else:
                rows = self.db.fetch_all("""
                    SELECT s.*, 
                           d.name as dept_name, 
                           d.code as dept_code,
                           COUNT(sc.id) as course_count
                    FROM students s
                    JOIN departments d ON s.department_id = d.id
                    LEFT JOIN student_courses sc ON s.id = sc.student_id
                    GROUP BY s.id
                    ORDER BY s.student_number
                """)

            self.students = [dict(row) for row in rows]

            self.filter_table()

            logger.info(f"✓ {len(self.students)} öğrenci yüklendi")

        except Exception as e:
            logger.error(f"Öğrenciler yüklenirken hata: {str(e)}")
            QMessageBox.critical(self, "Hata", f"Öğrenciler yüklenemedi:\n{str(e)}")

    def filter_table(self):
        search_text = self.search_input.text().lower()
        department_id = self.department_filter.currentData()
        class_level = self.class_filter.currentText()

        filtered_students = []
        for student in self.students:
            if search_text:
                if (search_text not in student['student_number'].lower() and
                    search_text not in student['full_name'].lower()):
                    continue
            if department_id and student['department_id'] != department_id:
                continue
            if class_level != "Tümü":
                if not student.get('class_level'):
                    continue
                if not student['class_level'].startswith(class_level + "."):
                    continue

            filtered_students.append(student)

        # Tabloyu doldur
        self.populate_table(filtered_students)

    def populate_table(self, students):
        self.table.setRowCount(len(students))

        for row, student in enumerate(students):
            number_item = QTableWidgetItem(student['student_number'])
            number_item.setData(Qt.ItemDataRole.UserRole, student['id'])
            self.table.setItem(row, 0, number_item)

            self.table.setItem(row, 1, QTableWidgetItem(student['full_name']))

            dept_name = student.get('dept_code', '-')
            self.table.setItem(row, 2, QTableWidgetItem(dept_name))

            class_level = str(student['class_level']) if student.get('class_level') else "-"
            class_item = QTableWidgetItem(class_level)
            class_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, class_item)

            course_count = student.get('course_count', 0)
            count_item = QTableWidgetItem(str(course_count))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, count_item)

        total = len(self.students)
        shown = len(students)
        self.info_label.setText(f"Toplam {total} öğrenci • {shown} öğrenci gösteriliyor")

    def search_student(self):
        student_number = self.search_input.text().strip()

        if not student_number:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir öğrenci numarası girin.")
            return

        student_row = self.db.fetch_one("""
            SELECT s.*, d.name as dept_name, d.code as dept_code
            FROM students s
            LEFT JOIN departments d ON s.department_id = d.id
            WHERE s.student_number = ?
        """, (student_number,))

        if not student_row:
            QMessageBox.information(
                self,
                "Bulunamadı",
                f"'{student_number}' numaralı öğrenci bulunamadı."
            )
            return

        student = dict(student_row)

        course_rows = self.db.fetch_all("""
            SELECT c.*
            FROM courses c
            JOIN student_courses sc ON c.id = sc.course_id
            WHERE sc.student_id = ?
            ORDER BY c.class_level, c.code
        """, (student['id'],))
        courses = [dict(row) for row in course_rows]

        detail_html = f"""
<div style='font-family: Arial; font-size: 13px;'>
    <h3 style='color: #2c3e50; margin-bottom: 15px;'>👨‍🎓 Öğrenci Bilgileri</h3>
    
    <div style='background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 8px; padding: 15px; margin-bottom: 15px;'>
        <p style='margin: 3px 0; font-size: 13px; color: #2c3e50;'><b>Öğrenci:</b> {student['full_name']}</p>
        <p style='margin: 3px 0; font-size: 13px; color: #2c3e50;'><b>Numara:</b> {student['student_number']}</p>
        <p style='margin: 3px 0; font-size: 13px; color: #2c3e50;'><b>Bölüm:</b> {student.get('dept_name', '-')}</p>
        <p style='margin: 3px 0; font-size: 13px; color: #2c3e50;'><b>Sınıf:</b> {student.get('class_level', '-')}</p>
    </div>
    
    <h3 style='color: #2c3e50; margin-top: 15px; margin-bottom: 10px;'>� Aldığı Dersler ({len(courses)} ders):</h3>
"""

        if courses:
            detail_html += "<div style='background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 5px; padding: 10px;'>"
            for i, course in enumerate(courses, 1):
                detail_html += f"""
    <p style='margin: 0; padding: 8px; border-bottom: 1px solid #f0f0f0; color: #34495e; font-size: 13px;'>
        {i}. <b>{course['code']}</b> - {course['name']}
    </p>
"""
            detail_html += "</div>"
        else:
            detail_html += """
    <p style='color: #566573; font-style: italic; padding: 20px;'>
        Bu öğrencinin kayıtlı dersi bulunmamaktadır.
    </p>
"""

            detail_html += "</div>\n"

            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Öğrenci Detayları")
            msg_box.setTextFormat(Qt.TextFormat.RichText)
            msg_box.setText(detail_html)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setMinimumWidth(500)
            msg_box.exec()

    def show_student_detail(self, row, column):
        student_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        student_row = self.db.fetch_one("""
            SELECT s.*, d.name as dept_name
            FROM students s
            LEFT JOIN departments d ON s.department_id = d.id
            WHERE s.id = ?
        """, (student_id,))

        if not student_row:
            return

        student = dict(student_row)

        course_rows = self.db.fetch_all("""
            SELECT c.*
            FROM courses c
            JOIN student_courses sc ON c.id = sc.course_id
            WHERE sc.student_id = ?
            ORDER BY c.class_level, c.code
        """, (student_id,))
        courses = [dict(row) for row in course_rows]

        detail_html = f"""
<div style='font-family: Arial; font-size: 13px;'>
    <h3 style='color: #2c3e50; margin-bottom: 15px;'>👨‍🎓 Öğrenci Bilgileri</h3>
    
    <div style='background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 8px; padding: 15px; margin-bottom: 15px;'>
        <p style='margin: 3px 0; font-size: 13px; color: #2c3e50;'><b>Öğrenci:</b> {student['full_name']}</p>
        <p style='margin: 3px 0; font-size: 13px; color: #2c3e50;'><b>Numara:</b> {student['student_number']}</p>
        <p style='margin: 3px 0; font-size: 13px; color: #2c3e50;'><b>Bölüm:</b> {student.get('dept_name', '-')}</p>
        <p style='margin: 3px 0; font-size: 13px; color: #2c3e50;'><b>Sınıf:</b> {student.get('class_level', '-')}</p>
    </div>
    
    <h3 style='color: #2c3e50; margin-top: 15px; margin-bottom: 10px;'>� Aldığı Dersler ({len(courses)} ders):</h3>
"""

        if courses:
            detail_html += "<div style='background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 5px; padding: 10px;'>"
            for i, course in enumerate(courses, 1):
                detail_html += f"""
    <p style='margin: 0; padding: 8px; border-bottom: 1px solid #f0f0f0; color: #34495e; font-size: 13px;'>
        {i}. <b>{course['code']}</b> - {course['name']}
    </p>
"""
            detail_html += "</div>"
        else:
            detail_html += """
    <p style='color: #566573; font-style: italic; padding: 20px;'>
        Bu öğrencinin kayıtlı dersi bulunmamaktadır.
    </p>
"""

        detail_html += "</div>\n"

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Öğrenci Detayları")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(detail_html)
        msg_box.setMinimumWidth(500)
        msg_box.exec()

    def export_to_csv(self):
        if not self.students:
            QMessageBox.warning(self, "Uyarı", "Dışa aktarılacak öğrenci bulunamadı.")
            return

        try:
            dept_code = "tum"
            if self.current_user['role'] == 'coordinator':
                dept_row = self.db.fetch_one("""
                    SELECT code FROM departments WHERE id = ?
                """, (self.current_user['department_id'],))
                if dept_row:
                    dept = dict(dept_row)
                    dept_code = dept['code']

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "CSV Olarak Kaydet",
                f"ogrenci_listesi_{dept_code}.csv",
                "CSV Files (*.csv)"
            )

            if not file_path:
                return

            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)

                writer.writerow([
                    "Öğrenci No", "Ad Soyad", "Bölüm", "Sınıf", "Kayıtlı Dersler"
                ])

                for student in self.students:
                    course_rows = self.db.fetch_all("""
                        SELECT c.code
                        FROM courses c
                        JOIN student_courses sc ON c.id = sc.course_id
                        WHERE sc.student_id = ?
                    """, (student['id'],))
                    course_codes = ", ".join([row['code'] for row in course_rows])

                    writer.writerow([
                        student['student_number'],
                        student['full_name'],
                        student.get('dept_code', ''),
                        student.get('class_level', ''),
                        course_codes
                    ])

            QMessageBox.information(
                self,
                "Başarılı",
                f"✓ {len(self.students)} öğrenci CSV olarak kaydedildi:\n{file_path}"
            )
            logger.info(f"✓ Öğrenci listesi export edildi: {file_path}")

        except Exception as e:
            logger.error(f"CSV export hatası: {str(e)}")
            QMessageBox.critical(self, "Hata", f"CSV kaydedilemedi:\n{str(e)}")
    
    def clear_all_students(self):
        reply = QMessageBox.question(
            self,
            "Öğrencileri Sil",
            "⚠️ TÜM ÖĞRENCİLERİ SİLMEK İSTEDİĞİNİZDEN EMİN MİSİNİZ?\n\n"
            "Bu işlem:\n"
            "• Tüm öğrencileri silecek\n"
            "• Öğrenci-ders kayıtlarını silecek\n"
            "• Oturma planlarını etkileyecek\n\n"
            "Bu işlem GERİ ALINAMAZ!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            count_row = self.db.fetch_one("SELECT COUNT(*) as cnt FROM students")
            deleted_count = count_row['cnt'] if count_row else 0
            
            self.db.execute("DELETE FROM seating_assignments WHERE student_id IN (SELECT id FROM students)")
            
            self.db.execute("DELETE FROM students")
            
            self.load_data()
            
            QMessageBox.information(
                self,
                "Başarılı",
                f"✓ {deleted_count} öğrenci başarıyla silindi!\n\n"
                "Tüm öğrenci-ders kayıtları ve oturma planları da temizlendi."
            )
            logger.info(f"✓ Tüm öğrenciler silindi ({deleted_count} kayıt)")
            
        except Exception as e:
            logger.error(f"Öğrenci silme hatası: {str(e)}")
            QMessageBox.critical(self, "Hata", f"Öğrenciler silinirken hata:\n{str(e)}")