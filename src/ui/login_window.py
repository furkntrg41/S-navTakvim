 
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QPixmap

from pathlib import Path
import os

class LoginWindow(QMainWindow):

    login_successful = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.background_pixmap = None
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Giriş Yap")
        self.setWindowState(Qt.WindowState.WindowFullScreen)

        try:
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent
            image_path = project_root / "resources" / "kocaeli-universitesi.jpg"
            if image_path.exists():
                self.background_pixmap = QPixmap(str(image_path))
        except Exception as e:
            print(f"Arka plan resmi yüklenirken hata: {e}")

        container_widget = QWidget()
        self.setCentralWidget(container_widget)

        if not self.background_pixmap:
             container_widget.setStyleSheet("background-color: #2c3e50;")

        center_frame = QFrame()
        center_frame.setFixedSize(400, 450)
        center_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0.7);
                border-radius: 15px;
            }
        """)

        form_layout = QVBoxLayout(center_frame)
        form_layout.setContentsMargins(30, 30, 30, 30)
        form_layout.setSpacing(15)

        logo_label = QLabel()
        logo_size = 100
        try:
            logo_path = project_root / "resources" / "kou-logo.png"
            if logo_path.exists():
                logo_pixmap = QPixmap(str(logo_path))
                logo_label.setFixedSize(logo_size, logo_size)
                logo_label.setPixmap(logo_pixmap)
                logo_label.setScaledContents(True)
                logo_label.setStyleSheet(f"QLabel {{ border-radius: {logo_size // 2}px; border: 2px solid #ecf0f1; background-color: transparent; }}")
                form_layout.addWidget(logo_label, 0, Qt.AlignmentFlag.AlignCenter)
        except Exception as e:
            print(f"Logo yüklenirken hata oluştu: {e}")

        title = QLabel("Giriş Yap")
        title_font = QFont("Arial", 16, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: white; background: transparent;")
        form_layout.addWidget(title)

        form_layout.addSpacing(10)
        email_label = QLabel("E-posta:")
        email_label.setStyleSheet("color: #ecf0f1; background: transparent;")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("ornek@email.com")
        self.email_input.setStyleSheet("padding: 5px; border-radius: 3px;")
        form_layout.addWidget(email_label)
        form_layout.addWidget(self.email_input)

        password_label = QLabel("Şifre:")
        password_label.setStyleSheet("color: #ecf0f1; background: transparent;")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("••••••••")
        self.password_input.setStyleSheet("padding: 5px; border-radius: 3px;")
        form_layout.addWidget(password_label)
        form_layout.addWidget(self.password_input)
        form_layout.addSpacing(10)

        btn_layout = QHBoxLayout()
        self.login_btn = QPushButton("Giriş Yap")
        self.login_btn.clicked.connect(self.handle_login)
        self.login_btn.setStyleSheet("""
            QPushButton {{ background-color: #27ae60; color: white; padding: 10px; border: none; border-radius: 5px; font-weight: bold; }}
            QPushButton:hover {{ background-color: #229954; }}
        """)

        cancel_btn = QPushButton("Çıkış")
        cancel_btn.clicked.connect(self.close)
        cancel_btn.setStyleSheet("""
            QPushButton {{ background-color: #c0392b; color: white; padding: 10px; border: none; border-radius: 5px; }}
            QPushButton:hover {{ background-color: #a93226; }}
        """)
        btn_layout.addWidget(self.login_btn)
        btn_layout.addWidget(cancel_btn)
        form_layout.addLayout(btn_layout)

        main_layout = QVBoxLayout(container_widget)
        main_layout.addWidget(center_frame, alignment=Qt.AlignmentFlag.AlignCenter)

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

    def handle_login(self):
        email = self.email_input.text().strip()
        password = self.password_input.text()

        if not email or not password:
            QMessageBox.warning(self, "Uyarı", "Lütfen e-posta ve şifre alanlarını doldurun!")
            return

        from src.core.auth import authenticate_user
        try:
            user = authenticate_user(email, password)
            if user:
                self.login_successful.emit(user)
                self.close()
            else:
                QMessageBox.critical(self, "Hata", "❌ E-posta veya şifre hatalı!\n\nLütfen tekrar deneyin.")
                self.password_input.clear()
                self.password_input.setFocus()
        except Exception as e:
            QMessageBox.critical(self, "Kritik Hata", f"Giriş işlemi sırasında hata:\n{str(e)}")