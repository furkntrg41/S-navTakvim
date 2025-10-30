 
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QMessageBox, QStatusBar, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPainter, QPixmap
from src.config import APP_NAME, APP_VERSION
from src.utils.error_handler import exception_handler, handle_exception, log_operation
from src.utils.logger import logger
from pathlib import Path


class MainWindow(QMainWindow):

    def __init__(self, user=None,restart_callback = None):
        super().__init__()
        self.current_user = user
        self.restart_callback = restart_callback
        self.background_pixmap = None
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setWindowState(Qt.WindowState.WindowFullScreen)

        try:
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent
            image_path = project_root / "resources" / "kocaeli-universitesi.jpg"
            if image_path.exists():
                self.background_pixmap = QPixmap(str(image_path))
        except Exception as e:
            print(f"Ana pencere arkaplanı yüklenirken hata: {e}")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(50, 50, 50, 50)

        content_panel = QFrame()
        content_panel.setObjectName("contentPanel")
        content_panel.setStyleSheet("""
            #contentPanel {
                background-color: rgba(255, 255, 255, 0.92);
                border-radius: 15px;
            }
        """)
        panel_layout = QVBoxLayout(content_panel)
        panel_layout.setContentsMargins(25, 25, 25, 25)
        panel_layout.setSpacing(20)

        header_layout = QHBoxLayout()
        title_label = QLabel("🎓 Sınav Takvimi Yönetim Sistemi")
        title_font = QFont("Arial", 20, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #2c3e50; background: transparent;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        if self.current_user:
            user_info_text = f"👤 {self.current_user['email']}"
            if self.current_user['role'] == 'admin':
                user_info_text += " (Yönetici)"
            else:
                dept_name = self.get_department_name()
                user_info_text += f" (Koordinatör - {dept_name})"
            user_info_label = QLabel(user_info_text)
            user_info_label.setStyleSheet("font-size: 12px; color: #34495e; padding: 5px; background: transparent;")
            header_layout.addWidget(user_info_label)

            change_pass_btn = QPushButton("🔑 Şifre Değiştir")
            change_pass_btn.clicked.connect(self.change_password)
            change_pass_btn.setStyleSheet("""
                QPushButton { background-color: #f39c12; color: white; border: none; padding: 5px 10px; border-radius: 3px; font-size: 11px; }
                QPushButton:hover { background-color: #e67e22; }
            """)
            header_layout.addWidget(change_pass_btn)

            switch_account_btn = QPushButton("🔄 Hesap Değiştir")
            switch_account_btn.clicked.connect(self.switch_account)
            switch_account_btn.setStyleSheet("""
                            QPushButton { background-color: #3498db; color: white; border: none; padding: 5px 10px; border-radius: 3px; font-size: 11px; }
                            QPushButton:hover { background-color: #2980b9; }
                        """)
            header_layout.addWidget(switch_account_btn)

            logout_btn = QPushButton("🚪 Çıkış")
            logout_btn.clicked.connect(self.logout)
            logout_btn.setStyleSheet("""
                QPushButton { background-color: #e74c3c; color: white; border: none; padding: 5px 10px; border-radius: 3px; font-size: 11px; }
                QPushButton:hover { background-color: #c0392b; }
            """)
            header_layout.addWidget(logout_btn)

        panel_layout.addLayout(header_layout)

        from PyQt6.QtWidgets import QStackedWidget
        self.content_stack = QStackedWidget()
        panel_layout.addWidget(self.content_stack)

        dashboard_widget = QWidget()
        dashboard_layout = QVBoxLayout(dashboard_widget)

        button_grid = QGridLayout()
        button_grid.setSpacing(15)

        self.btn_classrooms = QPushButton("📚 Derslik Yönetimi")
        self.btn_classrooms.setStyleSheet("QPushButton { background-color: #3498db; color: white; border: none; border-radius: 5px; font-size: 14px; font-weight: bold; } QPushButton:hover { background-color: #2980b9; }")

        self.btn_import = QPushButton("📥 Excel İçe Aktar")
        self.btn_import.setStyleSheet("QPushButton { background-color: #27ae60; color: white; border: none; border-radius: 5px; font-size: 14px; font-weight: bold; } QPushButton:hover { background-color: #229954; }")

        self.btn_courses = QPushButton("📚 Ders Listesi")
        self.btn_courses.setStyleSheet("QPushButton { background-color: #9b59b6; color: white; border: none; border-radius: 5px; font-size: 14px; font-weight: bold; } QPushButton:hover { background-color: #8e44ad; }")

        self.btn_students = QPushButton("👨‍🎓 Öğrenci Listesi")
        self.btn_students.setStyleSheet("QPushButton { background-color: #e67e22; color: white; border: none; border-radius: 5px; font-size: 14px; font-weight: bold; } QPushButton:hover { background-color: #d68910; }")

        self.btn_schedule = QPushButton("📅 Sınav Programı Oluştur")
        self.btn_schedule.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; border: none; border-radius: 5px; font-size: 14px; font-weight: bold; } QPushButton:hover { background-color: #c0392b; }")

        self.btn_view_schedules = QPushButton("📋 Sınav Programlarını Görüntüle")
        self.btn_view_schedules.setStyleSheet("QPushButton { background-color: #27ae60; color: white; border: none; border-radius: 5px; font-size: 14px; font-weight: bold; } QPushButton:hover { background-color: #229954; }")

        buttons = [
            (self.btn_classrooms, 0, 0), (self.btn_import, 0, 1), (self.btn_schedule, 0, 2),
            (self.btn_courses, 1, 0), (self.btn_students, 1, 1), (self.btn_view_schedules, 1, 2)
        ]

        for btn, row, col in buttons:
            btn.setMinimumHeight(80)
            button_grid.addWidget(btn, row, col)

        self.btn_classrooms.clicked.connect(self.show_classroom_management)
        self.btn_import.clicked.connect(self.show_import_wizard)
        self.btn_courses.clicked.connect(self.show_course_list)
        self.btn_students.clicked.connect(self.show_student_list)
        self.btn_schedule.clicked.connect(self.show_exam_wizard)
        self.btn_view_schedules.clicked.connect(self.show_exam_schedules)

        dashboard_layout.addLayout(button_grid)
        dashboard_layout.addStretch()

        test_db_btn = QPushButton("🔧 Veritabanı Bağlantısını Test Et")
        test_db_btn.clicked.connect(self.test_db_connection)
        test_db_btn.setStyleSheet("QPushButton { background-color: #16a085; color: white; border: none; padding: 10px; border-radius: 5px; font-size: 12px; } QPushButton:hover { background-color: #138d75; }")
        dashboard_layout.addWidget(test_db_btn, 0, Qt.AlignmentFlag.AlignRight)

        self.content_stack.addWidget(dashboard_widget)
        self.classroom_widget = None
        main_layout.addWidget(content_panel)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.show_dashboard()

    def paintEvent(self, event):
        if self.background_pixmap:
            painter = QPainter(self)
            scaled_pixmap = self.background_pixmap.scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation
            )
            point = self.rect().center() - scaled_pixmap.rect().center()
            painter.drawPixmap(point, scaled_pixmap)
            painter.end()
        else:
            super().paintEvent(event)

    def get_department_name(self):
        try:
            if not self.current_user or not self.current_user.get('department_id'): return "Bilinmiyor"
            from src.core.db_raw import get_db
            db = get_db()
            dept = db.fetch_one("SELECT name FROM departments WHERE id = ?", (self.current_user['department_id'],))
            return dept['name'] if dept else "Bilinmiyor"
        except Exception as e:
            logger.error(f"Bölüm adı alınamadı: {e}")
            return "Bilinmiyor"

    def show_classroom_management(self):
        try:
            if self.classroom_widget is None:
                from src.ui.classroom_management import ClassroomManagementWidget
                self.classroom_widget = ClassroomManagementWidget(self.current_user)
                self.content_stack.addWidget(self.classroom_widget)
            else:
                self.classroom_widget.load_classrooms()
            self.content_stack.setCurrentWidget(self.classroom_widget)
            self.statusBar.showMessage("📚 Derslik Yönetimi")
            self._show_back_button()
        except Exception as e:
            from src.utils.error_handler import show_error_dialog
            show_error_dialog(self, "Hata", f"Derslik yönetimi ekranı açılamadı:\n{str(e)}")

    def show_import_wizard(self):
        try:
            if not hasattr(self, 'import_widget') or self.import_widget is None:
                from src.ui.import_wizard import ImportWizardWidget
                self.import_widget = ImportWizardWidget(self.current_user)
                self.content_stack.addWidget(self.import_widget)
            self.content_stack.setCurrentWidget(self.import_widget)
            self.statusBar.showMessage("📥 Excel İçe Aktarım")
            self._show_back_button()
        except Exception as e:
            from src.utils.error_handler import show_error_dialog
            show_error_dialog(self, "Hata", f"Excel içe aktarım ekranı açılamadı:\n{str(e)}")

    def show_course_list(self):
        try:
            if not hasattr(self, 'course_list_widget') or self.course_list_widget is None:
                from src.ui.course_list_widget import CourseListWidget
                self.course_list_widget = CourseListWidget(self.current_user)
                self.content_stack.addWidget(self.course_list_widget)
            else:
                self.course_list_widget.load_data()
            self.content_stack.setCurrentWidget(self.course_list_widget)
            self.statusBar.showMessage("📚 Ders Listesi")
            self._show_back_button()
        except Exception as e:
            from src.utils.error_handler import show_error_dialog
            show_error_dialog(self, "Hata", f"Ders listesi ekranı açılamadı:\n{str(e)}")

    def show_student_list(self):
        try:
            if not hasattr(self, 'student_list_widget') or self.student_list_widget is None:
                from src.ui.student_list_widget import StudentListWidget
                self.student_list_widget = StudentListWidget(self.current_user)
                self.content_stack.addWidget(self.student_list_widget)
            else:
                self.student_list_widget.load_data()
            self.content_stack.setCurrentWidget(self.student_list_widget)
            self.statusBar.showMessage("👨‍🎓 Öğrenci Listesi")
            self._show_back_button()
        except Exception as e:
            from src.utils.error_handler import show_error_dialog
            show_error_dialog(self, "Hata", f"Öğrenci listesi ekranı açılamadı:\n{str(e)}")

    def show_exam_wizard(self):
        try:
            from src.ui.exam_wizard import ExamWizard
            wizard = ExamWizard(self.current_user, self)
            wizard.exec()
            self.show_dashboard()
        except Exception as e:
            from src.utils.error_handler import show_error_dialog
            show_error_dialog(self, "Hata", f"Sınav programı wizard açılamadı:\n{str(e)}")

    def show_exam_schedules(self):
        if not hasattr(self, 'exam_schedule_viewer') or self.exam_schedule_viewer is None:
            from src.ui.exam_schedule_viewer import ExamScheduleViewer
            self.exam_schedule_viewer = ExamScheduleViewer(self.current_user)
            self.content_stack.addWidget(self.exam_schedule_viewer)
        else:
            self.exam_schedule_viewer.load_schedules()
        self.content_stack.setCurrentWidget(self.exam_schedule_viewer)
        self.statusBar.showMessage("Sinav Programlari")
        self._show_back_button()

    def _show_back_button(self):
        if not hasattr(self, 'back_to_menu_btn'):
            self.back_to_menu_btn = QPushButton("🏠 Ana Menü")
            self.back_to_menu_btn.clicked.connect(self.show_dashboard)
            self.back_to_menu_btn.setStyleSheet("""
                QPushButton { background-color: #34495e; color: white; border: none; padding: 8px 15px; border-radius: 5px; font-size: 12px; }
                QPushButton:hover { background-color: #2c3e50; }
            """)
            self.statusBar.addPermanentWidget(self.back_to_menu_btn)
        self.back_to_menu_btn.setVisible(True)

    def show_dashboard(self):
        self.content_stack.setCurrentIndex(0)
        if hasattr(self, 'back_to_menu_btn'):
            self.back_to_menu_btn.setVisible(False)
        status_text = "✓ Sistem hazır"
        if self.current_user:
            if self.current_user['role'] == 'admin':
                status_text += " - Yönetici Yetkisi: Tüm İşlemler"
            else:
                status_text += f" - Koordinatör: {self.get_department_name()}"
        self.statusBar.showMessage(status_text)

    def switch_account(self):
        
        reply = QMessageBox.question(self, "Hesap Değiştir",
                                     "Mevcut oturumu kapatıp giriş ekranına dönmek istediğinize emin misiniz?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            if self.restart_callback:
                logger.info(f"Hesap değiştirme başlatıldı: {self.current_user['email']}")
                self.restart_callback()

    def change_password(self):
        try:
            from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox
            from src.utils.error_handler import validate_input

            dialog = QDialog(self)
            dialog.setWindowTitle("Şifre Değiştir")
            dialog.setFixedSize(400, 220)

            dialog.setStyleSheet("""
                QDialog {
                    background-color: #fafbfc;
                }
                QLabel {
                    color: #24292e;
                    font-weight: bold;
                    font-size: 13px;
                }
                QLineEdit {
                    background-color: white;
                    color: #24292e;
                    border: 1px solid #d1d5da;
                    border-radius: 6px;
                    padding: 8px;
                    font-size: 13px;
                }
                QLineEdit:focus {
                    border: 1px solid #0366d6;
                }
                QPushButton {
                    background-color: #2ea44f;
                    color: white;
                    border: 1px solid rgba(27, 31, 35, 0.15);
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #2c974b;
                }
            """)

            layout = QFormLayout()
            layout.setSpacing(10)  # Elemanlar arası boşluk

            old_pass_input = QLineEdit()
            old_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
            layout.addRow("Mevcut Şifre:", old_pass_input)

            new_pass_input = QLineEdit()
            new_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
            layout.addRow("Yeni Şifre:", new_pass_input)

            confirm_pass_input = QLineEdit()
            confirm_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
            layout.addRow("Yeni Şifre (Tekrar):", confirm_pass_input)

            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
            )
            buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Değiştir")
            buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("İptal")

            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addRow(buttons)

            dialog.setLayout(layout)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                old_pass = old_pass_input.text()
                new_pass = new_pass_input.text()
                confirm_pass = confirm_pass_input.text()

                try:
                    validate_input(old_pass, "Mevcut Şifre", required=True, min_length=1)
                    validate_input(new_pass, "Yeni Şifre", required=True, min_length=6)
                except Exception as e:
                    from src.utils.error_handler import show_warning_dialog
                    show_warning_dialog(self, "Validasyon Hatası", str(e))
                    return

                if new_pass != confirm_pass:
                    from src.utils.error_handler import show_warning_dialog
                    show_warning_dialog(self, "Şifreler Eşleşmiyor", "Yeni şifreler eşleşmiyor!")
                    return

                from src.core.auth import change_password
                success, message = change_password(self.current_user['id'], old_pass, new_pass)

                if success:
                    from src.utils.error_handler import show_info_dialog
                    show_info_dialog(self, "Başarılı", message)
                    log_operation(f"Şifre Değiştirildi: {self.current_user['email']}", success=True)
                else:
                    from src.utils.error_handler import show_error_dialog
                    show_error_dialog(self, "Şifre Değiştirme Hatası", message)
                    log_operation(f"Şifre Değiştirme Başarısız: {message}", success=False)
        except Exception as e:
            from src.utils.error_handler import show_error_dialog
            show_error_dialog(self, "Hata", f"Şifre değiştirilemedi:\n{str(e)}")


    def logout(self):
        reply = QMessageBox.question(self, "Çıkış", "Çıkış yapmak istediğinize emin misiniz?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            logger.info(f"✓ Kullanıcı çıkış yaptı: {self.current_user['email']}")
            self.close()
            import sys
            sys.exit(0)

    def test_db_connection(self):
        from src.core.db_raw import Database
        try:
            db = Database()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]
                QMessageBox.information(self, "Başarılı", f"✓ Veritabanı bağlantısı başarılı!\n\nVeritabanı konumu:\n{self.get_db_path()}\n\nTablo sayısı: {table_count}")
        except Exception as e:
            QMessageBox.critical(self, "Kritik Hata", f"Veritabanı test edilirken hata:\n{str(e)}")

    def get_db_path(self):
        from src.config import DATABASE_PATH
        return str(DATABASE_PATH)