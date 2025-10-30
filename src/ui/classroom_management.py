from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QMessageBox, QDialog, QFormLayout,
    QSpinBox, QComboBox, QGroupBox, QGridLayout, QHeaderView, QFrame,
    QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QPalette
from src.core.db_raw import Database
from src.utils.logger import logger
from src.utils.error_handler import (
    exception_handler, handle_exception, log_operation,
    validate_input, validate_number, show_error_dialog, show_info_dialog
)


class ClassroomManagementWidget(QWidget):

    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.db = Database()
        self.departments = []
        self.classrooms = []
        self.init_ui()
        self.load_departments()
        self.load_classrooms()

    def init_ui(self):
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#f4f6f7"))
        self.setPalette(palette)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        title = QLabel("📚 Derslik Yönetimi")
        title_font = QFont("Arial", 16, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #2c3e50; background: transparent;")
        layout.addWidget(title)
        control_layout = QHBoxLayout()
        search_label = QLabel("Ara:")
        search_label.setStyleSheet("color: #34495e; font-weight: bold;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Derslik kodu veya bölüm...")
        self.search_input.textChanged.connect(self.filter_classrooms)
        control_layout.addWidget(search_label)
        control_layout.addWidget(self.search_input)
        dept_label = QLabel("Bölüm:")
        dept_label.setStyleSheet("color: #34495e; font-weight: bold;")
        self.dept_filter = QComboBox()
        self.dept_filter.addItem("Tümü", None)
        self.dept_filter.currentIndexChanged.connect(self.filter_classrooms)
        control_layout.addWidget(dept_label)
        control_layout.addWidget(self.dept_filter)
        control_layout.addStretch()
        self.add_btn = QPushButton("➕ Yeni Derslik")
        self.add_btn.clicked.connect(self.add_classroom)
        self.add_btn.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; padding: 8px 15px; border: none; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #229954; }
        """)
        control_layout.addWidget(self.add_btn)
        refresh_btn = QPushButton("🔄 Yenile")
        refresh_btn.clicked.connect(self.load_classrooms)
        refresh_btn.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; padding: 8px 15px; border: none; border-radius: 5px; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        control_layout.addWidget(refresh_btn)
        layout.addLayout(control_layout)
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["🏫 Derslik", "📂 Bölüm", "👥 Kapasite", "↕ Satır", "↔ Sütun", "💺 Oturma", "📌 Durum", "⚙ İşlemler"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        self.table.setStyleSheet("""
            QTableWidget { gridline-color: #d5dbdb; selection-background-color: #d6eaf8; selection-color: #1c2833; border: 2px solid #bdc3c7; border-radius: 8px; background-color: #ffffff; }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid #ecf0f1; }
            QTableWidget::item:alternate { background-color: #f8f9fa; }
            QHeaderView::section { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #34495e, stop:1 #2c3e50); color: white; padding: 10px; font-weight: bold; font-size: 12px; border: none; border-right: 1px solid #1c2833; }
            QHeaderView::section:first { border-top-left-radius: 8px; }
            QHeaderView::section:last { border-top-right-radius: 8px; border-right: none; }
        """)
        layout.addWidget(self.table)
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel("Toplam: 0 derslik")
        self.stats_label.setStyleSheet("color: #34495e; padding: 5px; background: transparent; font-weight: bold;")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)

    def load_departments(self):
        from src.core.auth import can_access_department
        try:
            rows = self.db.fetch_all("SELECT * FROM departments ORDER BY name")
            all_depts = [dict(row) for row in rows]
            self.departments = [d for d in all_depts if can_access_department(self.current_user, d['id'])]
            self.dept_filter.clear()
            self.dept_filter.addItem("Tümü", None)
            for dept in self.departments:
                self.dept_filter.addItem(dept['name'], dept['id'])
        except Exception as e:
            logger.error(f"Bölümler yüklenirken hata: {e}")
            QMessageBox.critical(self, "Hata", f"Bölümler yüklenemedi:\n{str(e)}")

    def load_classrooms(self):
        try:
            log_operation("Derslikler Yükleniyor")
            from src.core.auth import can_access_department
            rows = self.db.fetch_all("""SELECT c.*, d.id as dept_id, d.name as dept_name, d.code as dept_code FROM classrooms c JOIN departments d ON c.department_id = d.id ORDER BY d.name, c.code""")
            all_classrooms = [dict(row) for row in rows]
            self.classrooms = [cr for cr in all_classrooms if can_access_department(self.current_user, cr['dept_id'])]
            self.populate_table()
            logger.info(f"✓ {len(self.classrooms)} derslik yüklendi")
        except Exception as e:
            logger.error(f"Derslikler yüklenirken hata: {e}", exc_info=True)
            show_error_dialog(self, "Derslik Yükleme Hatası", str(e))

    def populate_table(self):
        self.table.setRowCount(0)
        for classroom in self.classrooms:
            row = self.table.rowCount()
            self.table.insertRow(row)
            code_item = QTableWidgetItem(classroom['code'])
            code_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            code_item.setForeground(QColor("#2c3e50"))
            self.table.setItem(row, 0, code_item)
            dept_item = QTableWidgetItem(f"📂 {classroom['dept_name']}")
            dept_item.setForeground(QColor("#34495e"))
            self.table.setItem(row, 1, dept_item)
            capacity_item = QTableWidgetItem(str(classroom['capacity']))
            capacity_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            capacity_item.setFont(QFont("Arial", 11, QFont.Weight.Bold))
            capacity_item.setForeground(QColor("#e74c3c"))
            self.table.setItem(row, 2, capacity_item)
            row_item = QTableWidgetItem(f"↕ {classroom['rows']}")
            row_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            row_item.setForeground(QColor("#34495e"))
            self.table.setItem(row, 3, row_item)
            col_item = QTableWidgetItem(f"↔ {classroom['columns']}")
            col_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            col_item.setForeground(QColor("#34495e"))
            self.table.setItem(row, 4, col_item)
            if classroom['seating_arrangement'] == 2:
                seating, seating_color = "💺💺 İkili", QColor("#3498db")
            elif classroom['seating_arrangement'] == 3:
                seating, seating_color = "💺💺💺 Üçlü", QColor("#9b59b6")
            else:
                seating, seating_color = "💺💺💺💺 Dörtlü", QColor("#e74c3c")
            seating_item = QTableWidgetItem(seating)
            seating_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            seating_item.setForeground(seating_color)
            seating_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            self.table.setItem(row, 5, seating_item)
            status_item = QTableWidgetItem("✅ Aktif" if classroom['is_active'] else "❌ Pasif")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            status_item.setForeground(QColor("#27ae60") if classroom['is_active'] else QColor("#e74c3c"))
            status_item.setBackground(QColor("#d5f4e6") if classroom['is_active'] else QColor("#fadbd8"))
            self.table.setItem(row, 6, status_item)
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)
            view_btn = QPushButton("👁")
            view_btn.setToolTip("Sınıfı Görüntüle")
            view_btn.setFixedSize(35, 28)
            view_btn.setStyleSheet("QPushButton { background-color: #3498db; color: white; border: none; border-radius: 5px; font-size: 16px; } QPushButton:hover { background-color: #2980b9; }")
            view_btn.clicked.connect(lambda ch, c=classroom: self.view_classroom(c))
            btn_layout.addWidget(view_btn)
            edit_btn = QPushButton("✏")
            edit_btn.setToolTip("Düzenle")
            edit_btn.setFixedSize(35, 28)
            edit_btn.setStyleSheet("QPushButton { background-color: #f39c12; color: white; border: none; border-radius: 5px; font-size: 14px; } QPushButton:hover { background-color: #e67e22; }")
            edit_btn.clicked.connect(lambda ch, c=classroom: self.edit_classroom(c))
            btn_layout.addWidget(edit_btn)
            delete_btn = QPushButton("🗑")
            delete_btn.setToolTip("Sil")
            delete_btn.setFixedSize(35, 28)
            delete_btn.setStyleSheet("QPushButton { background-color: #e74c3c; color: white; border: none; border-radius: 5px; font-size: 14px; } QPushButton:hover { background-color: #c0392b; }")
            delete_btn.clicked.connect(lambda ch, c=classroom: self.delete_classroom(c))
            btn_layout.addWidget(delete_btn)
            self.table.setCellWidget(row, 7, btn_widget)
            self.table.setRowHeight(row, 45)
        total_capacity = sum(c['capacity'] for c in self.classrooms)
        self.stats_label.setText(f"📊 Toplam: {len(self.classrooms)} derslik  |  👥 Toplam Kapasite: {total_capacity} öğrenci")
        self.stats_label.setStyleSheet("QLabel { color: #2c3e50; font-size: 13px; font-weight: bold; padding: 8px; background-color: #ecf0f1; border-radius: 5px; }")

    def filter_classrooms(self):
        search_text = self.search_input.text().lower()
        dept_id = self.dept_filter.currentData()
        for row in range(self.table.rowCount()):
            show = True
            if search_text:
                if search_text not in self.table.item(row, 0).text().lower() and search_text not in self.table.item(row, 1).text().lower(): show = False
            if dept_id is not None:
                classroom = next((c for c in self.classrooms if c['code'] == self.table.item(row, 0).text()), None)
                if classroom and classroom['dept_id'] != dept_id: show = False
            self.table.setRowHidden(row, not show)

    def add_classroom(self):
        dialog = ClassroomDialog(self, self.current_user, self.departments)
        if dialog.exec() == QDialog.DialogCode.Accepted: self.load_classrooms()

    def view_classroom(self, classroom):
        dialog = ClassroomViewDialog(self, classroom)
        dialog.exec()

    def edit_classroom(self, classroom):
        dialog = ClassroomDialog(self, self.current_user, self.departments, classroom)
        if dialog.exec() == QDialog.DialogCode.Accepted: self.load_classrooms()

    def delete_classroom(self, classroom):
        try:
            usage_check = self.db.fetch_one("SELECT COUNT(*) as cnt FROM exam_sessions WHERE classroom_id = ?", (classroom['id'],))
            if usage_check and usage_check['cnt'] > 0:
                exam_count = usage_check['cnt']
                reply = QMessageBox.warning(self, "Derslik Kullanımda", f"'{classroom['code']}' dersliği {exam_count} sınav oturumunda kullanılıyor!", QMessageBox.StandardButton.Ok)
                return
            else:
                reply = QMessageBox.question(self, "Derslik Sil", f"'{classroom['code']}' dersliğini silmek istediğinize emin misiniz?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply != QMessageBox.StandardButton.Yes: return
            log_operation(f"Derslik Siliniyor: {classroom['code']}")
            self.db.execute("DELETE FROM classrooms WHERE id = ?", (classroom['id'],))
            show_info_dialog(self, "Başarılı", "Derslik başarıyla silindi!")
            self.load_classrooms()
        except Exception as e:
            show_error_dialog(self, "Derslik Silme Hatası", f"Derslik silinemedi:\n{str(e)}")

class ClassroomDialog(QDialog):

    def __init__(self, parent, current_user, departments, classroom=None):
        super().__init__(parent)
        self.current_user = current_user
        self.departments = departments
        self.classroom = classroom
        self.is_edit = classroom is not None
        self.init_ui()

    def init_ui(self):
        title_text = "✏ Derslik Düzenle" if self.is_edit else "➕ Yeni Derslik Ekle"
        self.setWindowTitle(title_text)
        self.setFixedSize(550, 500)
        self.setStyleSheet("""
            QDialog { background-color: #f5f5f5; }
            QLabel { color: #2c3e50; font-size: 13px; background-color: transparent; }
        """)
        layout = QVBoxLayout()
        layout.setSpacing(15)
        title_label = QLabel(title_text)
        title_label.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3498db, stop:1 #2980b9);
                color: white; font-size: 18px; font-weight: bold; padding: 15px; border-radius: 8px;
            }
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        form_container = QWidget()
        form_container.setStyleSheet("""
            QWidget { background-color: #ffffff; border-radius: 10px; padding: 15px; border: 1px solid #e0e0e0; }
        """)
        form = QFormLayout(form_container)
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        input_style = """
            QLineEdit, QSpinBox, QComboBox {
                padding: 12px; border: 2px solid #3498db; border-radius: 6px; background-color: #ffffff;
                color: #000000; font-size: 14px; min-height: 35px;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 3px solid #2980b9; background-color: #eaf2f8; }
            QComboBox::drop-down { border: none; background-color: #3498db; width: 30px; }
            QComboBox QAbstractItemView {
                background-color: white; color: #000000; selection-background-color: #3498db;
                selection-color: white; font-size: 14px;
            }
        """
        label_style = "QLabel { font-size: 14px; color: #000000; background-color: transparent; padding: 5px; }"
        code_label = QLabel("🏫 Derslik Kodu:")
        code_label.setStyleSheet(label_style)
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Örn: D201, A101, AMFI-1")
        self.code_input.setStyleSheet(input_style)
        if self.is_edit: self.code_input.setText(self.classroom['code'])
        form.addRow(code_label, self.code_input)
        dept_label = QLabel("📂 Bölüm:")
        dept_label.setStyleSheet(label_style)
        self.dept_combo = QComboBox()
        self.dept_combo.setStyleSheet(input_style)
        for dept in self.departments: self.dept_combo.addItem(f"{dept['name']}", dept['id'])
        if self.is_edit: self.dept_combo.setCurrentIndex(self.dept_combo.findData(self.classroom['department_id']))
        form.addRow(dept_label, self.dept_combo)
        capacity_label = QLabel("👥 Kapasite:")
        capacity_label.setStyleSheet(label_style)
        self.capacity_spin = QSpinBox()
        self.capacity_spin.setRange(10, 500)
        self.capacity_spin.setValue(self.classroom['capacity'] if self.is_edit else 60)
        self.capacity_spin.setSuffix(" öğrenci")
        self.capacity_spin.setStyleSheet(input_style)
        form.addRow(capacity_label, self.capacity_spin)
        rows_label = QLabel("↕ Satır Sayısı:")
        rows_label.setStyleSheet(label_style)
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 50)
        self.rows_spin.setValue(self.classroom['rows'] if self.is_edit else 10)
        self.rows_spin.setSuffix(" satır")
        self.rows_spin.setStyleSheet(input_style)
        self.rows_spin.valueChanged.connect(self.update_capacity_suggestion)
        form.addRow(rows_label, self.rows_spin)
        columns_label = QLabel("↔ Sütun Sayısı:")
        columns_label.setStyleSheet(label_style)
        self.columns_spin = QSpinBox()
        self.columns_spin.setRange(1, 50)
        self.columns_spin.setValue(self.classroom['columns'] if self.is_edit else 6)
        self.columns_spin.setSuffix(" sütun")
        self.columns_spin.setStyleSheet(input_style)
        self.columns_spin.valueChanged.connect(self.update_capacity_suggestion)
        form.addRow(columns_label, self.columns_spin)
        seating_label = QLabel("💺 Oturma Düzeni:")
        seating_label.setStyleSheet(label_style)
        self.seating_combo = QComboBox()
        self.seating_combo.addItem("İkili Oturma (2-2)", 2)
        self.seating_combo.addItem("Üçlü Oturma (3-3)", 3)
        self.seating_combo.addItem("Dörtlü Oturma (4-4)", 4)
        self.seating_combo.setStyleSheet(input_style)
        if self.is_edit: self.seating_combo.setCurrentIndex(self.seating_combo.findData(self.classroom['seating_arrangement']))
        self.seating_combo.currentIndexChanged.connect(self.update_capacity_suggestion)
        form.addRow(seating_label, self.seating_combo)
        self.capacity_suggestion = QLabel()
        self.capacity_suggestion.setStyleSheet("""
            QLabel { background-color: #fff3cd; color: #000000; padding: 15px; border-radius: 8px; border: 2px solid #ffc107; font-size: 13px; }
        """)
        self.update_capacity_suggestion()
        form.addRow("", self.capacity_suggestion)
        status_label = QLabel("📌 Durum:")
        status_label.setStyleSheet(label_style)
        self.active_combo = QComboBox()
        self.active_combo.addItem("Aktif ✅", True)
        self.active_combo.addItem("Pasif ❌", False)
        self.active_combo.setStyleSheet(input_style)
        if self.is_edit: self.active_combo.setCurrentIndex(0 if self.classroom['is_active'] else 1)
        form.addRow(status_label, self.active_combo)
        layout.addWidget(form_container)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        save_btn = QPushButton("💾 Kaydet")
        save_btn.clicked.connect(self.save_classroom)
        save_btn.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; padding: 12px 25px; border: none; border-radius: 8px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background-color: #229954; }
        """)
        save_btn.setMinimumWidth(150)
        cancel_btn = QPushButton("❌ İptal")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton { background-color: #95a5a6; color: white; padding: 12px 25px; border: none; border-radius: 8px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background-color: #7f8c8d; }
        """)
        cancel_btn.setMinimumWidth(150)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def update_capacity_suggestion(self):
        rows, cols, seating = self.rows_spin.value(), self.columns_spin.value(), self.seating_combo.currentData()
        total_seats = rows * cols
        if seating == 2:
            suggested, seating_text = rows * (cols // 2), "ikili (her sırada sağ tarafa)"
        elif seating == 3:
            suggested, seating_text = rows * ((cols // 3) * 2), "üçlü (kenarlara, ortası boş)"
        elif seating == 4:
            suggested, seating_text = rows * ((cols // 4) * 2), "4'lü (kenarlara, ortalar boş)"
        else:
            suggested, seating_text = total_seats // 2, f"{seating}'li (satranç deseni)"
        self.capacity_spin.setValue(suggested)
        self.capacity_suggestion.setText(f"💡 ÖNERİLEN KAPASİTE: {suggested} öğrenci\n📐 {rows} satır × {cols} sütun = {total_seats} koltuk\n💺 {seating_text} → {suggested} öğrenci oturabilir")

    def save_classroom(self):
        code = self.code_input.text().strip()
        if not code:
            QMessageBox.warning(self, "Uyarı", "Derslik kodu zorunludur!")
            return
        dept_id, capacity, rows, cols, seating, is_active = self.dept_combo.currentData(), self.capacity_spin.value(), self.rows_spin.value(), self.columns_spin.value(), self.seating_combo.currentData(), self.active_combo.currentData()
        db = Database()
        try:
            if self.is_edit:
                db.execute("UPDATE classrooms SET code = ?, department_id = ?, capacity = ?, rows = ?, columns = ?, seating_arrangement = ?, is_active = ? WHERE id = ?", (code, dept_id, capacity, rows, cols, seating, is_active, self.classroom['id']))
                message = f"Derslik güncellendi: {code}"
            else:
                if db.fetch_one("SELECT * FROM classrooms WHERE code = ?", (code,)):
                    QMessageBox.warning(self, "Uyarı", f"'{code}' kodlu derslik zaten mevcut!")
                    return
                db.execute("INSERT INTO classrooms (code, department_id, capacity, rows, columns, seating_arrangement, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)", (code, dept_id, capacity, rows, cols, seating, is_active))
                message = f"Yeni derslik eklendi: {code}"
            logger.info(f"✓ {message}")
            QMessageBox.information(self, "Başarılı", message)
            self.accept()
        except Exception as e:
            logger.error(f"Derslik kaydedilirken hata: {e}")
            QMessageBox.critical(self, "Hata", f"İşlem başarısız:\n{str(e)}")

class ClassroomViewDialog(QDialog):

    def __init__(self, parent, classroom):
        super().__init__(parent)
        self.classroom = classroom
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"📚 Derslik Görünümü - {self.classroom['code']}")

        width = max(900, min(1400, self.classroom['columns'] * 80 + 250))
        height = max(600, min(900, self.classroom['rows'] * 60 + 300))
        self.resize(width, height)

        layout = QVBoxLayout()
        layout.setSpacing(15)

        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2980b9);
                border-radius: 10px;
                padding: 15px;
            }
        """)
        header_layout = QHBoxLayout(header_widget)

        db = Database()
        dept_row = db.fetch_one(
            "SELECT name FROM departments WHERE id = ?",
            (self.classroom['department_id'],)
        )
        dept_name = dict(dept_row)['name'] if dept_row else "Bilinmiyor"

        left_info = QVBoxLayout()

        title_label = QLabel(f"🏫 {self.classroom['code']}")
        title_label.setStyleSheet("color: white; font-size: 20px; font-weight: bold; background: transparent;")
        left_info.addWidget(title_label)

        dept_label = QLabel(f"📂 {dept_name}")
        dept_label.setStyleSheet("color: white; font-size: 13px; background: transparent;")
        left_info.addWidget(dept_label)

        header_layout.addLayout(left_info)
        header_layout.addStretch()

        capacity_widget = QWidget()
        capacity_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 10px;
            }
        """)
        capacity_layout = QVBoxLayout(capacity_widget)
        capacity_layout.setSpacing(2)

        capacity_num = QLabel(str(self.classroom['capacity']))
        capacity_num.setStyleSheet("color: white; font-size: 28px; font-weight: bold; background: transparent;")
        capacity_num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        capacity_layout.addWidget(capacity_num)

        capacity_text = QLabel("👥 KAPASİTE")
        capacity_text.setStyleSheet("color: white; font-size: 11px; background: transparent;")
        capacity_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        capacity_layout.addWidget(capacity_text)

        header_layout.addWidget(capacity_widget)

        right_info = QVBoxLayout()
        right_info.setAlignment(Qt.AlignmentFlag.AlignRight)

        arrangement = self.classroom['seating_arrangement']
        if arrangement == 2:
            seating_text = "2'li Oturma (2-2)"
        elif arrangement == 3:
            seating_text = "3'lü Oturma (3-3)"
        else:
            seating_text = f"{arrangement}'lü Oturma ({arrangement}-{arrangement})"

        seating_label = QLabel(f"💺 {seating_text}")
        seating_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold; background: transparent;")
        seating_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_info.addWidget(seating_label)

        grid_info = QLabel(f"📐 {self.classroom['rows']} Satır × {self.classroom['columns']} Sütun")
        grid_info.setStyleSheet("color: white; font-size: 12px; background: transparent;")
        grid_info.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_info.addWidget(grid_info)

        header_layout.addLayout(right_info)

        layout.addWidget(header_widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 2px solid #bdc3c7;
                border-radius: 10px;
                background-color: #f8f9fa;
            }
        """)

        classroom_widget = QWidget()
        classroom_layout = QVBoxLayout(classroom_widget)
        classroom_layout.setSpacing(15)
        classroom_layout.setContentsMargins(20, 20, 20, 20)

        board_label = QLabel("🎓 TAHTA (Öğretmen)")
        board_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        board_label.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c3e50, stop:1 #34495e);
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
                border-radius: 8px;
                border: 3px solid #1a252f;
            }
        """)
        board_label.setMinimumHeight(60)
        classroom_layout.addWidget(board_label)

        classroom_layout.addSpacing(20)

        grid_container = QWidget()
        grid = QGridLayout(grid_container)

        seat_spacing = 8 if self.classroom['columns'] <= 10 else 5
        grid.setSpacing(seat_spacing)
        grid.setContentsMargins(10, 10, 10, 10)

        seating_arrangement = self.classroom.get('seating_arrangement', 2)

        header_style = """
            QLabel {
                background-color: #34495e;
                color: white;
                border: none;
                font-weight: bold;
                font-size: 11px;
                padding: 5px;
            }
        """

        corner = QLabel("🪑 Masa")
        corner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        corner.setStyleSheet(header_style)
        corner.setMinimumSize(85, 35)
        grid.addWidget(corner, 0, 0)

        masa_no = 1
        for col in range(1, self.classroom['columns'] + 1, seating_arrangement):
            masa_label = QLabel(f"Masa {masa_no}")
            masa_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            masa_label.setStyleSheet(header_style)
            masa_label.setMinimumWidth(85 * seating_arrangement)

            remaining_cols = min(seating_arrangement, self.classroom['columns'] - col + 1)
            grid.addWidget(masa_label, 0, col, 1, remaining_cols)
            masa_no += 1

        for row in range(1, self.classroom['rows'] + 1):
            row_label = QLabel(f"Sıra {row}")
            row_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row_label.setStyleSheet(header_style)
            row_label.setMinimumHeight(75)
            row_label.setMinimumWidth(85)
            grid.addWidget(row_label, row, 0)

        for row in range(1, self.classroom['rows'] + 1):
            for col in range(1, self.classroom['columns'] + 1):
                is_table_boundary = (col % seating_arrangement == 0) and (col < self.classroom['columns'])
                border_right_used = "4px solid #34495e" if is_table_boundary else "2px solid #2980b9"
                border_right_empty = "4px solid #7f8c8d" if is_table_boundary else "2px dashed #bdc3c7"

                seat_num = (row - 1) * self.classroom['columns'] + col

                is_usable = False
                if seating_arrangement == 2:
                    is_usable = (col % 2 == 0)
                elif seating_arrangement == 3:
                    col_in_group = ((col - 1) % 3) + 1
                    is_usable = (col_in_group == 1 or col_in_group == 3)
                elif seating_arrangement == 4:
                    col_in_group = ((col - 1) % 4) + 1
                    is_usable = (col_in_group == 1 or col_in_group == 4)
                else:
                    is_usable = ((row + col) % 2 == 0)

                if is_usable:
                    cell = QLabel(f"<b>Koltuk {seat_num}</b><br><span style='font-size: 20px;'>💺</span><br><small>{row}-{col}</small>")
                    cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    cell.setStyleSheet(f"""
                        QLabel {{ background-color: #d5f4e6; color: #27ae60; border: 2px solid #27ae60; border-right: {border_right_used}; border-radius: 5px; padding: 8px; font-size: 10px; font-weight: bold; }}
                        QLabel:hover {{ background-color: #a9dfbf; border: 2px solid #229954; border-right: {border_right_used}; color: #1e8449; }}
                    """)
                else:
                    cell = QLabel(f"<b>Koltuk {seat_num}</b><br><span style='font-size: 20px;'>⛔</span><br><small>BOŞ</small>")
                    cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    cell.setStyleSheet(f"""
                        QLabel {{ background-color: #fadbd8; color: #e74c3c; border: 2px dashed #e74c3c; border-right: {border_right_empty}; border-radius: 5px; padding: 8px; font-size: 10px; }}
                        QLabel:hover {{ background-color: #f5b7b1; border: 2px dashed #c0392b; border-right: {border_right_empty}; color: #c0392b; }}
                    """)

                cell.setMinimumSize(85, 75)
                grid.addWidget(cell, row, col)

        classroom_layout.addWidget(grid_container)

        info_panel = QWidget()
        info_panel.setStyleSheet("""
            QWidget { background-color: #ecf0f1; border-radius: 8px; padding: 10px; }
        """)
        info_panel_layout = QHBoxLayout(info_panel)

        legend_label = QLabel("📌 Bilgi:")
        legend_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        info_panel_layout.addWidget(legend_label)

        total_seats = self.classroom['rows'] * self.classroom['columns']
        if seating_arrangement == 2:
            usable_capacity = self.classroom['rows'] * (self.classroom['columns'] // 2)
            arrangement_text = "2'li oturma: Sadece sağ taraf"
        elif seating_arrangement == 3:
            usable_capacity = self.classroom['rows'] * ((self.classroom['columns'] // 3) * 2)
            arrangement_text = "3'lü oturma: Kenarlara (ortası boş)"
        elif seating_arrangement == 4:
            usable_capacity = self.classroom['rows'] * ((self.classroom['columns'] // 4) * 2)
            arrangement_text = "4'lü oturma: Kenarlara (ortalar boş)"
        else:
            usable_capacity = total_seats // 2
            arrangement_text = f"{seating_arrangement}'li oturma"

        seat_info = QLabel(f"💺 = Kullanılabilir Koltuk ({usable_capacity} koltuk)  |  ⛔ = Boş Koltuk ({total_seats - usable_capacity} koltuk)  |  {arrangement_text}")
        seat_info.setStyleSheet("color: #34495e; font-size: 12px;")
        info_panel_layout.addWidget(seat_info)
        info_panel_layout.addStretch()

        status_text = "✅ Aktif" if self.classroom['is_active'] else "❌ Pasif"
        status_label = QLabel(f"Durum: {status_text}")
        status_label.setStyleSheet(f"QLabel {{ color: {'#27ae60' if self.classroom['is_active'] else '#e74c3c'}; font-weight: bold; font-size: 13px; }}")
        info_panel_layout.addWidget(status_label)

        classroom_layout.addWidget(info_panel)

        scroll.setWidget(classroom_widget)
        layout.addWidget(scroll)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("✖ Kapat")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton { background-color: #95a5a6; color: white; padding: 12px 30px; border: none; border-radius: 8px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: #7f8c8d; }
        """)
        close_btn.setMinimumWidth(150)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)