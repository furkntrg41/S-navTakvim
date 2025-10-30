from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QComboBox, QGroupBox, QGridLayout, QScrollArea, QWidget,
    QProgressDialog, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
from datetime import datetime

from src.core.seating_manager import SeatingManager
from src.core.db_raw import Database
import logging

logger = logging.getLogger(__name__)


class SeatingGeneratorThread(QThread):
    finished = pyqtSignal(dict)
    
    def __init__(self, db, exam_id, strategy=None):
        super().__init__()
        self.db = db
        self.exam_id = exam_id
    
    def run(self):
        manager = SeatingManager(self.db)
        result = manager.generate_seating_for_exam(self.exam_id)
        self.finished.emit(result)


class SeatingPlanViewer(QDialog):
    
    def __init__(self, exam_schedule: dict, db: Database, parent=None):
        super().__init__(parent)
        self.exam_schedule = exam_schedule
        self.db = db
        self.selected_exam = None
        self.seating_data = None
        
        self.setWindowTitle(f"Oturma Planı - {exam_schedule['name']}")
        self.resize(1000, 700)
        
        self.init_ui()
        self.load_exams()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        title = QLabel(f"📋 Oturma Planı: {self.exam_schedule['name']}")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; padding: 10px;")
        layout.addWidget(title)
        
        control_layout = QHBoxLayout()
        
        control_layout.addWidget(QLabel("Sınav:"))
        self.exam_combo = QComboBox()
        self.exam_combo.currentIndexChanged.connect(self.on_exam_selected)
        control_layout.addWidget(self.exam_combo)
        
        control_layout.addStretch()
        
        self.generate_btn = QPushButton("Oturma Planı Oluştur")
        self.generate_btn.clicked.connect(self.generate_seating)
        self.generate_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 5px 15px;")
        control_layout.addWidget(self.generate_btn)
        
        self.view_btn = QPushButton("Görüntüle")
        self.view_btn.clicked.connect(self.view_seating)
        self.view_btn.setEnabled(False)
        control_layout.addWidget(self.view_btn)
        
        self.pdf_btn = QPushButton("PDF Export")
        self.pdf_btn.clicked.connect(self.export_pdf)
        self.pdf_btn.setEnabled(False)
        control_layout.addWidget(self.pdf_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        self.info_group = QGroupBox("Sınav Bilgileri")
        info_layout = QVBoxLayout()
        self.info_label = QLabel("Sınav seçilmedi")
        self.info_label.setStyleSheet("padding: 10px;")
        info_layout.addWidget(self.info_label)
        self.info_group.setLayout(info_layout)
        layout.addWidget(self.info_group)
        
        legend_group = QGroupBox("📖 Açıklama")
        legend_layout = QHBoxLayout()
        legend_layout.setSpacing(20)
        
        full_label = QLabel()
        full_label.setPixmap(self.create_legend_box("#3498db", "Dolu Koltuk"))
        legend_layout.addWidget(full_label)
        
        empty_label = QLabel()
        empty_label.setPixmap(self.create_legend_box("#ecf0f1", "Boş Koltuk"))
        legend_layout.addWidget(empty_label)
        
        legend_layout.addStretch()
        legend_group.setLayout(legend_layout)
        layout.addWidget(legend_group)
        
        self.classrooms_scroll = QScrollArea()
        self.classrooms_scroll.setWidgetResizable(True)
        self.classrooms_scroll.setMinimumHeight(500)  # Daha geniş alan
        self.classrooms_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                background-color: #fafbfc;
            }
        """)
        self.classrooms_widget = QWidget()
        self.classrooms_layout = QVBoxLayout()
        self.classrooms_layout.setSpacing(20)  # Derslikler arası boşluk
        self.classrooms_widget.setLayout(self.classrooms_layout)
        self.classrooms_scroll.setWidget(self.classrooms_widget)
        layout.addWidget(self.classrooms_scroll)
        
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def create_legend_box(self, color: str, text: str):
        from PyQt6.QtGui import QPixmap, QPainter, QColor
        from PyQt6.QtCore import Qt, QRect
        
        pixmap = QPixmap(150, 30)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setBrush(QColor(color))
        painter.setPen(QColor("#2c3e50"))
        painter.drawRoundedRect(QRect(5, 5, 25, 20), 3, 3)
        
        painter.setPen(QColor("#2c3e50"))
        painter.drawText(QRect(35, 5, 115, 20), Qt.AlignmentFlag.AlignVCenter, text)
        
        painter.end()
        return pixmap
    
    def load_exams(self):
        try:
            exam_rows = self.db.fetch_all("""
                SELECT e.*, c.code as course_code, c.name as course_name
                FROM exams e
                JOIN courses c ON e.course_id = c.id
                WHERE e.schedule_id = ?
                ORDER BY e.exam_date, e.start_time
            """, (self.exam_schedule['id'],))
            
            exams = [dict(row) for row in exam_rows]
            
            self.exam_combo.clear()
            for exam in exams:
                if isinstance(exam['exam_date'], str):
                    exam_date = datetime.fromisoformat(exam['exam_date'])
                else:
                    exam_date = exam['exam_date']
                
                if isinstance(exam['start_time'], str):
                    start_time = datetime.fromisoformat(f"2000-01-01 {exam['start_time']}")
                else:
                    start_time = exam['start_time']
                
                display_text = (
                    f"{exam['course_code']} - {exam['course_name']} "
                    f"({exam_date.strftime('%d.%m.%Y')} {start_time.strftime('%H:%M')})"
                )
                self.exam_combo.addItem(display_text, exam['id'])
            
            logger.info(f"[OK] {len(exams)} sınav yüklendi")
            
        except Exception as e:
            logger.error(f"Sınav yükleme hatası: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"Sınavlar yüklenemedi:\n{str(e)}")
    
    def on_exam_selected(self, index):
        if index < 0:
            return
        
        exam_id = self.exam_combo.itemData(index)
        if exam_id:
            exam_row = self.db.fetch_one("""
                SELECT e.*, c.code as course_code, c.name as course_name
                FROM exams e
                JOIN courses c ON e.course_id = c.id
                WHERE e.id = ?
            """, (exam_id,))
            
            if exam_row:
                self.selected_exam = dict(exam_row)
                self.update_info()
                self.check_existing_seating()
    
    def update_info(self):
        if not self.selected_exam:
            return
        
        try:
            session_rows = self.db.fetch_all("""
                SELECT es.*, cl.code as classroom_code, cl.capacity as classroom_capacity,
                       cl.seating_arrangement
                FROM exam_sessions es
                JOIN classrooms cl ON es.classroom_id = cl.id
                WHERE es.exam_id = ?
            """, (self.selected_exam['id'],))
            
            exam_sessions = [dict(row) for row in session_rows]
            
            total_capacity = sum(session['classroom_capacity'] for session in exam_sessions)
            student_count = self.selected_exam['student_count']
            
            classrooms_text = ", ".join(
                f"{session['classroom_code']} ({session['classroom_capacity']})"
                for session in exam_sessions
            )
            
            if isinstance(self.selected_exam['exam_date'], str):
                exam_date = datetime.fromisoformat(self.selected_exam['exam_date'])
            else:
                exam_date = self.selected_exam['exam_date']
            
            if isinstance(self.selected_exam['start_time'], str):
                start_time = datetime.fromisoformat(f"2000-01-01 {self.selected_exam['start_time']}")
            else:
                start_time = self.selected_exam['start_time']
            
            info_html = f"""
            <b>Ders:</b> {self.selected_exam['course_code']} - {self.selected_exam['course_name']}<br>
            <b>Tarih/Saat:</b> {exam_date.strftime('%d.%m.%Y')} - 
            {start_time.strftime('%H:%M')}<br>
            <b>Öğrenci Sayısı:</b> {student_count}<br>
            <b>Derslikler:</b> {classrooms_text}<br>
            <b>Toplam Kapasite:</b> {total_capacity} koltuk
            """
            
            if student_count > total_capacity:
                info_html += f"<br><span style='color: red;'><b>⚠ UYARI:</b> Kapasite yetersiz!</span>"
            
            self.info_label.setText(info_html)
            
        except Exception as e:
            logger.error(f"Bilgi güncelleme hatası: {e}", exc_info=True)
    
    def check_existing_seating(self):
        if not self.selected_exam:
            return
        
        try:
            has_seating = False
            session_rows = self.db.fetch_all(
                "SELECT id FROM exam_sessions WHERE exam_id = ?",
                (self.selected_exam['id'],)
            )
            
            for session_row in session_rows:
                session = dict(session_row)
                count_row = self.db.fetch_one(
                    "SELECT COUNT(*) as cnt FROM seating_assignments WHERE exam_session_id = ?",
                    (session['id'],)
                )
                if count_row and count_row['cnt'] > 0:
                    has_seating = True
                    break
            
            self.view_btn.setEnabled(has_seating)
            self.pdf_btn.setEnabled(has_seating)
            
            if has_seating:
                self.generate_btn.setText("Yeniden Oluştur")
            else:
                self.generate_btn.setText("Oturma Planı Oluştur")
        
        except Exception as e:
            logger.error(f"Kontrol hatası: {e}", exc_info=True)
    
    def generate_seating(self):
        if not self.selected_exam:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir sınav seçin!")
            return
        
        reply = QMessageBox.question(
            self,
            "Oturma Planı Oluştur",
            f"Seçilen sınav için oturma planı oluşturulsun mu?\n\n"
            f"Ders: {self.selected_exam['course_code']}\n"
            f"Öğrenci: {self.selected_exam['student_count']}\n"
            f"(Derslik düzenine göre otomatik yerleştirme)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        progress = QProgressDialog("Oturma planı oluşturuluyor...", "İptal", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        self.thread = SeatingGeneratorThread(self.db, self.selected_exam['id'], None)
        self.thread.finished.connect(lambda result: self.on_seating_generated(result, progress))
        self.thread.start()
    
    def on_seating_generated(self, result, progress):
        progress.close()
        
        if result["success"]:
            initial_classrooms = result.get('initial_classrooms', 0)
            final_classrooms = len(result['sessions'])
            added_classrooms = final_classrooms - initial_classrooms
            
            message = (
                f"✓ Oturma planı başarıyla oluşturuldu!\n\n"
                f"📊 Toplam Öğrenci: {result['total_students']}\n"
                f"✅ Yerleştirilen: {result['assigned_students']}\n"
            )
            
            if added_classrooms > 0:
                message += f"\n🏫 Otomatik {added_classrooms} derslik eklendi (kapasite yetersizdi)\n"
            
            message += "\n📍 Derslik Dağılımı:\n" + "\n".join(
                f"  • {s['classroom_code']}: {s['assigned']}/{s['capacity']} koltuk"
                for s in result['sessions']
            )
            
            QMessageBox.information(self, "Başarılı", message)
            self.check_existing_seating()
            self.view_seating()
        else:
            QMessageBox.critical(
                self,
                "Hata",
                f"❌ Oturma planı oluşturulamadı!\n\n{result['message']}"
            )
    
    def view_seating(self):
        if not self.selected_exam:
            return
        
        try:
            while self.classrooms_layout.count():
                child = self.classrooms_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            
            session_rows = self.db.fetch_all("""
                SELECT es.*, cl.code as classroom_code, cl.rows, cl.columns,
                       cl.seating_arrangement
                FROM exam_sessions es
                JOIN classrooms cl ON es.classroom_id = cl.id
                WHERE es.exam_id = ?
            """, (self.selected_exam['id'],))
            
            for session_row in session_rows:
                exam_session = dict(session_row)
                
                count_row = self.db.fetch_one(
                    "SELECT COUNT(*) as cnt FROM seating_assignments WHERE exam_session_id = ?",
                    (exam_session['id'],)
                )
                assigned_count = count_row['cnt'] if count_row else 0
                
                group = QGroupBox(f"🏫 {exam_session['classroom_code']} - Kuş Bakışı Görünüm")
                group.setStyleSheet("""
                    QGroupBox {
                        font-weight: bold;
                        font-size: 13px;
                        border: 2px solid #3498db;
                        border-radius: 8px;
                        margin-top: 10px;
                        padding-top: 15px;
                    }
                    QGroupBox::title {
                        color: #2c3e50;
                        subcontrol-origin: margin;
                        subcontrol-position: top center;
                        padding: 5px 10px;
                    }
                """)
                group_layout = QVBoxLayout()
                
                capacity = exam_session['rows'] * exam_session['columns']
                
                info = QLabel(
                    f"📊 <b>Kapasite:</b> {capacity} koltuk | "
                    f"<b>Düzen:</b> {exam_session['rows']} sıra × {exam_session['columns']} sütun | "
                    f"<b>Dolu:</b> {assigned_count}/{capacity}"
                )
                info.setStyleSheet("color: #34495e; padding: 8px; font-size: 11px;")
                group_layout.addWidget(info)
                
                grid_widget = self.create_seating_grid(exam_session)
                group_layout.addWidget(grid_widget)
                
                group.setLayout(group_layout)
                self.classrooms_layout.addWidget(group)
            
            self.classrooms_layout.addStretch()
            
        except Exception as e:
            logger.error(f"Görüntüleme hatası: {e}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"Görüntüleme başarısız:\n{str(e)}")
    
    def create_seating_grid(self, exam_session: dict) -> QWidget:
        widget = QWidget()
        layout = QGridLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)
        
        rows = exam_session['rows']
        cols = exam_session['columns']
        
        assignment_rows = self.db.fetch_all("""
            SELECT sa.*, s.student_number, s.full_name
            FROM seating_assignments sa
            JOIN students s ON sa.student_id = s.id
            WHERE sa.exam_session_id = ?
        """, (exam_session['id'],))
        
        assignments = [dict(row) for row in assignment_rows]
        
        assignment_map = {
            (a['row_number'], a['column_number']): a
            for a in assignments
        }
        
        seating_arrangement = exam_session.get('seating_arrangement', 2)
        
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
        layout.addWidget(corner, 0, 0)
        
        masa_no = 1
        for col in range(1, cols + 1, seating_arrangement):
            masa_label = QLabel(f"Masa {masa_no}")
            masa_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            masa_label.setStyleSheet(header_style)
            masa_label.setMinimumWidth(85 * seating_arrangement)
            
            remaining_cols = min(seating_arrangement, cols - col + 1)
            layout.addWidget(masa_label, 0, col, 1, remaining_cols)
            masa_no += 1
        
        for row in range(1, rows + 1):
            row_label = QLabel(f"Sıra {row}")
            row_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row_label.setStyleSheet(header_style)
            row_label.setMinimumHeight(75)
            layout.addWidget(row_label, row, 0)
        
        for row in range(1, rows + 1):
            for col in range(1, cols + 1):
                assignment = assignment_map.get((row, col))
                
                is_table_boundary = (col % seating_arrangement == 0) and (col < cols)
                border_right = "4px solid #34495e" if is_table_boundary else "2px solid #2980b9"
                border_right_empty = "4px solid #7f8c8d" if is_table_boundary else "2px dashed #bdc3c7"
                
                if assignment:
                    full_name = assignment['full_name']
                    name_parts = full_name.split()
                    if len(name_parts) >= 2:
                        name_display = f"{name_parts[0][:8]}\n{name_parts[-1][:8]}"
                    else:
                        name_display = full_name[:10]
                    
                    cell = QLabel(
                        f"<b>Koltuk {assignment['seat_number']}</b><br>"
                        f"<small>{assignment['student_number']}</small><br>"
                        f"<span style='font-size: 9px;'>{name_display}</span>"
                    )
                    cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    cell.setStyleSheet(f"""
                        QLabel {{
                            background-color: #3498db;
                            color: white;
                            border: 2px solid #2980b9;
                            border-right: {border_right};
                            border-radius: 5px;
                            padding: 8px;
                            font-size: 10px;
                        }}
                    """)
                    cell.setMinimumSize(85, 75)
                else:
                    cell = QLabel(
                        f"<b>Koltuk {(row-1)*cols + col}</b><br>"
                        f"<br>"
                        f"<span style='color: #95a5a6;'>⚪ BOŞ</span>"
                    )
                    cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    cell.setStyleSheet(f"""
                        QLabel {{
                            background-color: #ecf0f1;
                            color: #7f8c8d;
                            border: 2px dashed #bdc3c7;
                            border-right: {border_right_empty};
                            border-radius: 5px;
                            padding: 8px;
                            font-size: 10px;
                        }}
                    """)
                    cell.setMinimumSize(85, 75)
                
                layout.addWidget(cell, row, col)
        
        widget.setLayout(layout)
        return widget
    
    def export_pdf(self):
        """Oturma planını PDF'e aktar (RAW SQL)"""
        if not self.selected_exam:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir sınav seçin!")
            return
        
        # Oturma planı var mı kontrol et
        has_seating = False
        session_rows = self.db.fetch_all(
            "SELECT id FROM exam_sessions WHERE exam_id = ?",
            (self.selected_exam['id'],)
        )
        
        for session_row in session_rows:
            session = dict(session_row)
            count_row = self.db.fetch_one(
                "SELECT COUNT(*) as cnt FROM seating_assignments WHERE exam_session_id = ?",
                (session['id'],)
            )
            if count_row and count_row['cnt'] > 0:
                has_seating = True
                break
        
        if not has_seating:
            QMessageBox.warning(
                self,
                "Uyarı",
                "Bu sınav için henüz oturma planı oluşturulmamış!\n\n"
                "Önce 'Oturma Planı Oluştur' butonuna basın."
            )
            return
        
        # Dosya adı öner
        # Tarih parse
        if isinstance(self.selected_exam['exam_date'], str):
            exam_date = datetime.fromisoformat(self.selected_exam['exam_date'])
        else:
            exam_date = self.selected_exam['exam_date']
        
        suggested_name = f"oturma_plani_{self.selected_exam['course_code']}_{exam_date.strftime('%Y%m%d')}.pdf"
        
        # Dosya kaydetme dialog'u
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "PDF Olarak Kaydet",
            suggested_name,
            "PDF Dosyası (*.pdf)"
        )
        
        if not file_path:
            return
        
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            
            # Türkçe karakter desteği için font yükle
            try:
                pdfmetrics.registerFont(TTFont('DejaVu', 'DejaVuSans.ttf'))
                pdfmetrics.registerFont(TTFont('DejaVu-Bold', 'DejaVuSans-Bold.ttf'))
                default_font = 'DejaVu'
                bold_font = 'DejaVu-Bold'
            except:
                # Font bulunamazsa varsayılan kullan
                default_font = 'Helvetica'
                bold_font = 'Helvetica-Bold'
            
            # PDF oluştur
            doc = SimpleDocTemplate(
                file_path,
                pagesize=landscape(A4),
                rightMargin=1*cm,
                leftMargin=1*cm,
                topMargin=1.5*cm,
                bottomMargin=1.5*cm
            )
            
            elements = []
            styles = getSampleStyleSheet()
            
            # Özel stiller
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontName=bold_font,
                fontSize=16,
                textColor=colors.HexColor('#2c3e50'),
                alignment=TA_CENTER,
                spaceAfter=10
            )
            
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Normal'],
                fontName=default_font,
                fontSize=10,
                textColor=colors.HexColor('#7f8c8d'),
                alignment=TA_CENTER,
                spaceAfter=15
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontName=bold_font,
                fontSize=12,
                textColor=colors.HexColor('#2c3e50'),
                spaceAfter=10
            )
            
            # Her derslik için sayfa
            # Exam sessions al (RAW SQL)
            session_rows = self.db.fetch_all("""
                SELECT es.*, cl.code as classroom_code, cl.rows, cl.columns, 
                       cl.seating_arrangement
                FROM exam_sessions es
                JOIN classrooms cl ON es.classroom_id = cl.id
                WHERE es.exam_id = ?
            """, (self.selected_exam['id'],))
            
            exam_sessions = [dict(row) for row in session_rows]
            
            for idx, exam_session in enumerate(exam_sessions):
                if idx > 0:
                    elements.append(PageBreak())
                
                # Başlık
                title = Paragraph(
                    f"{self.selected_exam['course_code']} - {self.selected_exam['course_name']}",
                    title_style
                )
                elements.append(title)
                
                # Saat parse
                if isinstance(self.selected_exam['start_time'], str):
                    start_time = datetime.fromisoformat(f"2000-01-01 {self.selected_exam['start_time']}")
                else:
                    start_time = self.selected_exam['start_time']
                
                # Alt başlık (tarih, saat, derslik)
                subtitle = Paragraph(
                    f"Tarih: {exam_date.strftime('%d.%m.%Y')} | "
                    f"Saat: {start_time.strftime('%H:%M')} | "
                    f"Derslik: {exam_session['classroom_code']}",
                    subtitle_style
                )
                elements.append(subtitle)
                
                elements.append(Spacer(1, 0.5*cm))
                
                # Oturma düzeni başlığı
                seating_heading = Paragraph("Oturma Düzeni", heading_style)
                elements.append(seating_heading)
                
                # Oturma grid'i (RAW SQL)
                assignment_rows = self.db.fetch_all("""
                    SELECT sa.*, s.student_number, s.full_name
                    FROM seating_assignments sa
                    JOIN students s ON sa.student_id = s.id
                    WHERE sa.exam_session_id = ?
                """, (exam_session['id'],))
                
                assignments = [dict(row) for row in assignment_rows]
                
                # Assignment map oluştur
                assignment_map = {
                    (a['row_number'], a['column_number']): a
                    for a in assignments
                }
                
                rows = exam_session['rows']
                cols = exam_session['columns']
                seating_arrangement = exam_session.get('seating_arrangement', 2)
                
                # Gerçek kapasite hesapla
                total_seats = rows * cols
                if seating_arrangement == 2:
                    capacity = rows * (cols // 2)
                elif seating_arrangement == 3:
                    capacity = rows * ((cols // 3) * 2)
                elif seating_arrangement == 4:
                    capacity = rows * ((cols // 4) * 2)
                else:
                    capacity = total_seats // 2
                
                # Grid tablosu oluştur
                grid_data = [[''] + [chr(64 + col) for col in range(1, cols + 1)]]  # Başlık
                
                for row in range(1, rows + 1):
                    row_data = [f'Sıra {row}']
                    for col in range(1, cols + 1):
                        assignment = assignment_map.get((row, col))
                        if assignment:
                            # Öğrenci bilgisini kısalt
                            full_name = assignment['full_name']
                            name_parts = full_name.split()
                            short_name = f"{name_parts[0][:8]}\n{name_parts[-1][:8]}" if len(name_parts) >= 2 else full_name[:12]
                            cell_text = f"K{assignment['seat_number']}\n{assignment['student_number']}\n{short_name}"
                        else:
                            cell_text = "BOŞ"
                        row_data.append(cell_text)
                    grid_data.append(row_data)
                
                # Dinamik sütun genişliği
                col_width = min(2.5*cm, (landscape(A4)[0] - 4*cm) / (cols + 1))
                col_widths = [2*cm] + [col_width] * cols
                
                grid_table = Table(grid_data, colWidths=col_widths)
                
                # Grid stili
                table_style = [
                    # Başlık
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                    ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#34495e')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('TEXTCOLOR', (0, 1), (0, -1), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (0, 0), (-1, 0), bold_font),
                    ('FONTNAME', (0, 1), (0, -1), bold_font),
                    ('FONTSIZE', (0, 0), (-1, -1), 7),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]
                
                # Dolu/boş koltuk renkleri
                for row in range(1, rows + 1):
                    for col in range(1, cols + 1):
                        assignment = assignment_map.get((row, col))
                        if assignment:
                            # Mavi (dolu)
                            table_style.append(
                                ('BACKGROUND', (col, row), (col, row), colors.HexColor('#3498db'))
                            )
                            table_style.append(
                                ('TEXTCOLOR', (col, row), (col, row), colors.whitesmoke)
                            )
                        else:
                            # Gri (boş)
                            table_style.append(
                                ('BACKGROUND', (col, row), (col, row), colors.HexColor('#ecf0f1'))
                            )
                
                grid_table.setStyle(TableStyle(table_style))
                elements.append(grid_table)
                
                # İstatistik
                elements.append(Spacer(1, 0.5*cm))
                stats = Paragraph(
                    f"<b>Toplam Kapasite:</b> {capacity} | "
                    f"<b>Yerleştirilen:</b> {len(assignments)} | "
                    f"<b>Boş:</b> {capacity - len(assignments)}",
                    ParagraphStyle(
                        'Stats',
                        parent=styles['Normal'],
                        fontName=default_font,
                        fontSize=9,
                        textColor=colors.HexColor('#7f8c8d'),
                        alignment=TA_CENTER
                    )
                )
                elements.append(stats)
            
            # PDF'i oluştur
            doc.build(elements)
            
            logger.info(f"PDF export başarılı: {file_path}")
            
            # Derslik sayısını al (RAW SQL)
            from src.core.db_raw import Database
            db = Database()
            session_count = db.fetch_one(
                "SELECT COUNT(*) as cnt FROM exam_sessions WHERE exam_id = ?",
                (self.selected_exam['id'],)
            )['cnt']
            
            QMessageBox.information(
                self,
                "Başarılı",
                f"✓ Oturma planı PDF olarak kaydedildi!\n\n"
                f"Dosya: {file_path}\n"
                f"Derslik Sayısı: {session_count}"
            )
            
        except ImportError:
            QMessageBox.critical(
                self,
                "Hata",
                "PDF oluşturmak için 'reportlab' kütüphanesi gerekli!\n\n"
                "Kurulum için:\npip install reportlab"
            )
        except Exception as e:
            logger.error(f"PDF export hatası: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Hata",
                f"PDF oluşturulamadı:\n{str(e)}"
            )
    
    def closeEvent(self, event):
        """Dialog kapatılırken"""
        # Thread'i durdur (eğer çalışıyorsa)
        if hasattr(self, 'thread') and hasattr(self.thread, 'isRunning'):
            if self.thread.isRunning():
                self.thread.terminate()
                self.thread.wait()
        event.accept()
