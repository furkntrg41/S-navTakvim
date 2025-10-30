from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QTextEdit, QGroupBox, QComboBox, QMessageBox,
    QDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from pathlib import Path
from typing import Optional
from datetime import datetime
from src.core.excel_importer import ExcelImporter
from src.utils.logger import logger


class ImportWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(int, int, list)  # success, error, errors_list
    error = pyqtSignal(str)

    def __init__(self, file_path: str, import_type: str, department_id: int):
        super().__init__()
        self.file_path = file_path
        self.import_type = import_type
        self.department_id = department_id
        self.importer = ExcelImporter()

    def run(self):
        try:
            self.progress.emit(10)

            if self.import_type == "courses":
                success, error, errors = self.importer.import_courses(
                    self.file_path, self.department_id
                )
            else:  # students
                success, error, errors = self.importer.import_students(
                    self.file_path, self.department_id
                )

            self.progress.emit(100)
            self.finished.emit(success, error, errors)

        except Exception as e:
            logger.error(f"Import worker hatası: {e}")
            self.error.emit(str(e))


class ImportWizardWidget(QWidget):
    
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.current_file = None
        self.current_errors = []
        self.worker = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("📥 Excel İçe Aktarım")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #2c3e50; margin: 10px;")
        layout.addWidget(title)

        file_group = QGroupBox("1️⃣ Dosya Seçimi")
        file_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #3498db;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                color: #2c3e50;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        file_layout = QVBoxLayout()

        type_layout = QHBoxLayout()
        type_label = QLabel("📋 İçe Aktarım Tipi:")
        type_label.setStyleSheet("color: #34495e; font-weight: bold;")
        type_layout.addWidget(type_label)

        self.type_combo = QComboBox()
        self.type_combo.addItem("📖 Ders Listesi", "courses")
        self.type_combo.addItem("👥 Öğrenci Listesi", "students")
        self.type_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 4px;
                font-size: 13px;
                background-color: grey; /* Arkaplan rengi eklendi */
            }
            QComboBox:focus {
                border: 2px solid #3498db;
            }
        """)
        type_layout.addWidget(self.type_combo, 1)
        file_layout.addLayout(type_layout)

        dept_layout = QHBoxLayout()
        dept_label = QLabel("🏫 Bölüm:")
        dept_label.setStyleSheet("color: #34495e; font-weight: bold;")
        dept_layout.addWidget(dept_label)

        self.dept_combo = QComboBox()
        self._populate_departments()
        self.dept_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 4px;
                font-size: 13px;
                background-color: grey; /* Arkaplan rengi eklendi */
            }
            QComboBox:focus {
                border: 2px solid #3498db;
            }
        """)
        dept_layout.addWidget(self.dept_combo, 1)
        file_layout.addLayout(dept_layout)

        path_layout = QHBoxLayout()
        self.file_label = QLabel("📄 Dosya: Seçilmedi")
        self.file_label.setStyleSheet("""
            QLabel {
                padding: 8px;
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                color: #566573; /* Renk koyulaştırıldı */
            }
        """)
        path_layout.addWidget(self.file_label, 1)

        self.browse_btn = QPushButton("🔍 Dosya Seç")
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        self.browse_btn.clicked.connect(self.browse_file)
        path_layout.addWidget(self.browse_btn)

        file_layout.addLayout(path_layout)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        import_layout = QHBoxLayout()
        import_layout.addStretch()

        self.import_btn = QPushButton("⬆️ İçe Aktar")
        self.import_btn.setEnabled(False)
        self.import_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 12px 40px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.import_btn.clicked.connect(self.start_import)
        import_layout.addWidget(self.import_btn)
        import_layout.addStretch()

        layout.addLayout(import_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                height: 25px;
                color: black; /* Yazı rengi eklendi */
            }
            QProgressBar::chunk {
                background-color: #3498db;
            }
        """)
        layout.addWidget(self.progress_bar)

        result_group = QGroupBox("2️⃣ İçe Aktarım Sonuçları")
        result_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #27ae60;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                color: #2c3e50; /* Grup başlığı rengi eklendi */
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        result_layout = QVBoxLayout()

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(150)
        self.result_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 8px;
                font-family: Consolas, monospace;
                font-size: 12px;
                color: #2c3e50; /* Yazı rengi eklendi */
            }
        """)
        result_layout.addWidget(self.result_text)

        error_btn_layout = QHBoxLayout()
        error_btn_layout.addStretch()
        self.error_report_btn = QPushButton("📄 Hata Raporu Kaydet")
        self.error_report_btn.setEnabled(False)
        self.error_report_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.error_report_btn.clicked.connect(self.save_error_report)
        error_btn_layout.addWidget(self.error_report_btn)
        result_layout.addLayout(error_btn_layout)

        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        layout.addStretch()

    def _populate_departments(self):
        from src.core.db_raw import Database

        db = Database()
        try:
            if self.user['role'] == "admin":
                dept_rows = db.fetch_all("SELECT * FROM departments ORDER BY code")
                departments = [dict(row) for row in dept_rows]
            else:
                dept_row = db.fetch_one(
                    "SELECT * FROM departments WHERE id = ?",
                    (self.user['department_id'],)
                )
                departments = [dict(dept_row)] if dept_row else []

            for dept in departments:
                self.dept_combo.addItem(f"{dept['code']} - {dept['name']}", dept['id'])

            if self.user['role'] == "coordinator":
                self.dept_combo.setEnabled(False)

        except Exception as e:
            logger.error(f"Department populate hatası: {e}")
            QMessageBox.warning(self, "Hata", f"Bölümler yüklenemedi:\n{str(e)}")

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Excel Dosyası Seç",
            "",
            "Excel Dosyaları (*.xlsx *.xls)"
        )

        if file_path:
            self.current_file = file_path
            self.file_label.setText(f"📄 Dosya: {Path(file_path).name}")
            self.file_label.setStyleSheet("""
                QLabel {
                    padding: 8px;
                    background-color: #d5f4e6;
                    border: 1px solid #27ae60;
                    border-radius: 4px;
                    color: #21618c;
                    font-weight: bold;
                }
            """)
            self.import_btn.setEnabled(True)

    def start_import(self):
        if not self.current_file:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce bir dosya seçin!")
            return

        department_id = self.dept_combo.currentData()
        import_type = self.type_combo.currentData()

        self.import_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.type_combo.setEnabled(False)
        if self.user['role'] == "admin":
             self.dept_combo.setEnabled(False)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.result_text.clear()
        self.current_errors = []

        self.worker = ImportWorker(self.current_file, import_type, department_id)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.import_finished)
        self.worker.error.connect(self.import_error)
        self.worker.start()

        logger.info(f"İçe aktarım başlatıldı: {import_type} - {self.current_file}")

    def update_progress(self, value: int):
        self.progress_bar.setValue(value)

    def import_finished(self, success_count: int, error_count: int, errors: list):
        self.current_errors = errors

        # Sonuçları göster
        result_html = f"""
        <div style="font-size: 13px; color: #2c3e50;">
            <p style="color: #27ae60; font-weight: bold;">✅ Başarılı: {success_count} kayıt</p>
            <p style="color: #e74c3c; font-weight: bold;">❌ Hatalı: {error_count} kayıt</p>
        """

        if errors:
            result_html += "<hr><p><b>İlk 5 Hata:</b></p><ul>"
            for error in errors[:5]:
                result_html += f"<li>Satır {error['row']}: {error['error']}</li>"
            if len(errors) > 5:
                result_html += f"<li><i>... ve {len(errors)-5} hata daha</i></li>"
            result_html += "</ul>"

        result_html += "</div>"
        self.result_text.setHtml(result_html)

        self.error_report_btn.setEnabled(bool(errors))

        self.import_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.type_combo.setEnabled(True)
        if self.user['role'] == "admin":
            self.dept_combo.setEnabled(True)

        if error_count == 0:
            QMessageBox.information(
                self,
                "Başarılı",
                f"✅ {success_count} kayıt başarıyla içe aktarıldı!"
            )
        else:
            QMessageBox.warning(
                self,
                "Kısmi Başarı",
                f"⚠️ {success_count} kayıt başarılı, {error_count} kayıt hatalı.\n\nHata raporunu kaydetmek için 'Hata Raporu Kaydet' butonuna tıklayın."
            )

        logger.info(f"İçe aktarım tamamlandı: {success_count} başarılı, {error_count} hatalı")

    def import_error(self, error_msg: str):
        self.result_text.setHtml(f"""
        <div style="color: #e74c3c; font-size: 13px;">
            <p><b>❌ Kritik Hata:</b></p>
            <p>{error_msg}</p>
        </div>
        """)

        self.import_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.type_combo.setEnabled(True)
        if self.user['role'] == "admin":
            self.dept_combo.setEnabled(True)

        QMessageBox.critical(self, "Hata", f"❌ İçe aktarım hatası:\n\n{error_msg}")

    def save_error_report(self):
        if not self.current_errors:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Hata Raporunu Kaydet",
            f"import_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Dosyaları (*.csv)"
        )

        if file_path:
            importer = ExcelImporter()
            importer.generate_error_csv(self.current_errors, file_path)
            QMessageBox.information(
                self,
                "Başarılı",
                f"✅ Hata raporu kaydedildi:\n{file_path}"
            )

    def closeEvent(self, event):
        if self.worker and hasattr(self.worker, 'isRunning'):
            if self.worker.isRunning():
                self.worker.terminate()
                self.worker.wait()
        event.accept()