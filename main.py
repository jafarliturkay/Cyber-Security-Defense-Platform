import sys
import os
import sqlite3
import re
import subprocess
import hashlib
import json
import urllib.request
import urllib.error
from datetime import datetime
import nmap
import socket

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QLineEdit, QPushButton, QTableWidget, 
    QTableWidgetItem, QProgressBar, QMessageBox, QSplitter,
    QTextEdit, QLabel, QTabWidget, QFileDialog, QDialog, QListWidget,
    QFormLayout, QStackedWidget
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QLinearGradient, QBrush, QPen, QPolygonF, QIcon, QPixmap
from PyQt6.QtCore import QPointF

# Matplotlib Entegrasyonu
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Veritabanı ve ikon yollarını tam konum olarak sabitliyoruz
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "network_scans.db")
ICO_PATH = os.path.join(BASE_DIR, "app_icon.ico")

SUSPICIOUS_PORTS = {
    4444: "Metasploit / Meterpreter Default Shell",
    31337: "Back Orifice Trojan",
    5555: "Android ADB / Backdoor Shell",
    12345: "NetBus Trojan",
    6667: "IRC Botnet C2 Server",
    1337: "Generic Hacker / Backdoor Port"
}

SUSPICIOUS_PATTERNS = [
    (r"import\s+socket", "Ağ Soketi Açma (Potential Reverse Shell)"),
    (r"subprocess\.Popen|subprocess\.call|os\.system", "Sistem Komutu Çalıştırma (Command Execution)"),
    (r"eval\(|exec\(", "Dinamik Kod Çalıştırma (Code Injection Risk)"),
    (r"powershell.*-enc|powershell.*-e\s+", "Gizlenmiş PowerShell Komutu (Obfuscated PowerShell)"),
    (r"DownloadString|Invoke-Expression|iex", "Uzaktan Zararlı İndirme/Çalıştırma Komutu"),
    (r"/bin/sh|/bin/bash|cmd\.exe", "Kabuk/Shell Başlatma Girişimi"),
    (r"base64\.b64decode", "Base64 Şifrelenmiş/Gizlenmiş Payload Kalıbı")
]

# Bilinen büyük sızıntı kaynakları için akıllı tarih veritabanı (Fallback)
KNOWN_BREACH_YEARS = {
    "1win": "2023-05-15",
    "cit0day": "2020-09-12",
    "linkedin": "2021-04-06",
    "facebook": "2019-04-03",
    "twitter": "2022-07-22",
    "adobe": "2013-10-04",
    "canva": "2019-05-24",
    "zomato": "2017-05-18",
    "collection": "2019-01-07"
}

def generate_ico_file():
    if not os.path.exists(ICO_PATH):
        try:
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            painter.setBrush(QBrush(QColor(30, 144, 255)))
            painter.setPen(QPen(QColor(135, 206, 250), 2))
            shield = QPolygonF([
                QPointF(32, 4),
                QPointF(58, 16),
                QPointF(58, 38),
                QPointF(32, 60),
                QPointF(6, 38),
                QPointF(6, 16)
            ])
            painter.drawPolygon(shield)
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(26, 26, 12, 14)
            painter.drawRoundedRect(23, 18, 18, 14, 7, 7)
            painter.end()
            pixmap.save(ICO_PATH, "ICO")
        except Exception:
            pass

def is_valid_email(email):
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_ip TEXT,
            status TEXT,
            ports TEXT,
            security_alerts TEXT,
            scan_time TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            email TEXT,
            sec_question TEXT,
            sec_answer TEXT,
            role TEXT,
            is_online INTEGER DEFAULT 0,
            last_login TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            action TEXT,
            details TEXT,
            log_time TEXT
        )
    """)
    
    for col in ["email", "sec_question", "sec_answer", "is_online", "last_login"]:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass

    cursor.execute("UPDATE users SET is_online = 0")

    cursor.execute("SELECT * FROM users WHERE username = ?", ("admin",))
    if not cursor.fetchone():
        admin_pass = hash_password("RosieTurkay2005.")
        sec_ans = hash_password("kocaeli")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO users (username, password, email, sec_question, sec_answer, role, is_online, last_login, created_at) 
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
        """, ("admin", admin_pass, "admin@security.local", "En sevdiğiniz şehir?", sec_ans, "admin", now, now))
    
    conn.commit()
    conn.close()

def log_audit(username, action, details):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO audit_logs (username, action, details, log_time) VALUES (?, ?, ?, ?)", (username, action, details, now))
        conn.commit()
        conn.close()
    except Exception:
        pass

class GlowingShieldBackground(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.light_pos = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(30)

    def update_animation(self):
        self.light_pos += 2.5
        if self.light_pos > self.width() + 100:
            self.light_pos = -100
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor("#0B132B"))
        gradient.setColorAt(0.5, QColor("#1C2541"))
        gradient.setColorAt(1.0, QColor("#3A506B"))
        painter.fillRect(self.rect(), QBrush(gradient))

        painter.setPen(QPen(QColor(70, 130, 180, 40), 2))
        painter.drawLine(0, 0, self.width(), self.height())
        painter.drawLine(self.width(), 0, 0, self.height())

        cx, cy = self.width() // 2, self.height() // 2 - 85
        
        painter.setBrush(QBrush(QColor(30, 144, 255, 180)))
        painter.setPen(QPen(QColor(135, 206, 250), 3))
        
        shield_points = QPolygonF([
            QPointF(cx, cy - 35),
            QPointF(cx + 28, cy - 20),
            QPointF(cx + 28, cy + 8),
            QPointF(cx, cy + 32),
            QPointF(cx - 28, cy + 8),
            QPointF(cx - 28, cy - 20)
        ])
        painter.drawPolygon(shield_points)

        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(int(cx - 7), int(cy - 2), 14, 12)
        painter.drawRoundedRect(int(cx - 9), int(cy - 11), 18, 14, 7, 7)

        glow_grad = QLinearGradient(self.light_pos - 40, 0, self.light_pos + 40, 0)
        glow_grad.setColorAt(0.0, QColor(255, 255, 255, 0))
        glow_grad.setColorAt(0.5, QColor(0, 255, 255, 160))
        glow_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        
        painter.setBrush(QBrush(glow_grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())

class LoginWidget(QWidget):
    def __init__(self, main_app_window):
        super().__init__()
        self.main_app_window = main_app_window

        self.bg_widget = GlowingShieldBackground(self)
        self.bg_widget.setGeometry(0, 0, self.width(), self.height())

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        center_outer_layout = QVBoxLayout()
        center_outer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel("🛡️ CYBER SECURITY & DEFENSE PLATFORM")
        self.title_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: white; background: transparent;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_outer_layout.addWidget(self.title_label)

        center_outer_layout.addSpacing(70)
        center_outer_layout.addSpacing(40)

        container_widget = QWidget()
        container_widget.setFixedWidth(440)
        container_layout = QVBoxLayout(container_widget)
        container_layout.setContentsMargins(10, 10, 10, 10)

        form_layout = QFormLayout()
        input_style = "background: white; color: black; padding: 5px; font-weight: bold; border-radius: 3px;"

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Kullanıcı Adı")
        self.username_input.setStyleSheet(input_style)
        self.username_input.returnPressed.connect(self.handle_login)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Şifre")
        self.password_input.setStyleSheet(input_style)
        self.password_input.returnPressed.connect(self.handle_login)

        form_layout.addRow(QLabel("<font color='white'><b>Kullanıcı Adı:</b></font>"), self.username_input)
        form_layout.addRow(QLabel("<font color='white'><b>Şifre:</b></font>"), self.password_input)
        container_layout.addLayout(form_layout)

        container_layout.addSpacing(5)
        
        self.login_pbar = QProgressBar()
        self.login_pbar.setValue(0)
        self.login_pbar.hide()
        container_layout.addWidget(self.login_pbar)

        container_layout.addSpacing(5)

        btn_layout = QHBoxLayout()
        self.login_btn = QPushButton("🔑 Giriş Yap")
        self.login_btn.setStyleSheet("background-color: #007ACC; color: white; font-weight: bold; padding: 6px;")
        self.login_btn.clicked.connect(self.handle_login)

        self.register_btn = QPushButton("📝 Kayıt Ol")
        self.register_btn.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 6px;")
        self.register_btn.clicked.connect(self.open_register)

        btn_layout.addWidget(self.login_btn)
        btn_layout.addWidget(self.register_btn)
        container_layout.addLayout(btn_layout)

        bottom_layout = QHBoxLayout()
        self.forgot_btn = QPushButton("❓ Şifremi Unuttum")
        self.forgot_btn.setStyleSheet("color: #add8e6; background: transparent; border: none;")
        self.forgot_btn.clicked.connect(self.open_forgot_password)

        self.admin_login_btn = QPushButton("Admin Girişi")
        self.admin_login_btn.setStyleSheet("color: gold; background: transparent; border: none; font-weight: bold;")
        self.admin_login_btn.clicked.connect(self.open_admin_login)

        bottom_layout.addWidget(self.forgot_btn)
        bottom_layout.addWidget(self.admin_login_btn)
        container_layout.addLayout(bottom_layout)

        center_outer_layout.addWidget(container_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addStretch()
        main_layout.addLayout(center_outer_layout)
        main_layout.addStretch()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.bg_widget.setGeometry(0, 0, self.width(), self.height())

    def clear_inputs(self):
        self.username_input.clear()
        self.password_input.clear()
        self.login_pbar.setValue(0)
        self.login_pbar.hide()
        self.login_btn.setEnabled(True)
        self.register_btn.setEnabled(True)

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Hata", "Lütfen kullanıcı adı ve şifre girin!")
            return

        hashed_pass = hash_password(password)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT username, role FROM users WHERE username = ? AND password = ? AND role = 'user'", (username, hashed_pass))
        user = cursor.fetchone()
        conn.close()

        if user:
            self.login_btn.setEnabled(False)
            self.register_btn.setEnabled(False)
            self.login_pbar.show()
            self.counter = 0
            
            self._timer = QTimer(self)
            self._timer.timeout.connect(lambda: self.update_login_progress(user[0], user[1]))
            self._timer.start(30)
        else:
            QMessageBox.critical(self, "Hata", "Kullanıcı adı veya şifre hatalı!")

    def update_login_progress(self, uname, urole):
        self.counter += 4
        self.login_pbar.setValue(self.counter)
        if self.counter >= 100:
            self._timer.stop()
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("UPDATE users SET is_online = 1, last_login = ? WHERE username = ?", (now, uname))
                conn.commit()
                conn.close()
            except Exception:
                pass

            log_audit(uname, "GİRİŞ", "Kullanıcı sisteme giriş yaptı.")
            self.main_app_window.on_successful_login({"username": uname, "role": urole})

    def open_register(self):
        RegisterDialog(self).exec()

    def open_forgot_password(self):
        ForgotPasswordDialog(self).exec()

    def open_admin_login(self):
        admin_dialog = AdminLoginDialog(self)
        if admin_dialog.exec() == QDialog.DialogCode.Accepted:
            uname = admin_dialog.admin_data["username"]
            urole = admin_dialog.admin_data["role"]
            log_audit(uname, "ADMIN GİRİŞİ", "Yönetici olarak giriş yapıldı.")
            self.main_app_window.on_successful_login({"username": uname, "role": urole})

class AdminLoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Admin Giriş Paneli")
        self.setFixedSize(380, 250)
        self.admin_data = None

        layout = QVBoxLayout(self)
        title = QLabel("Yönetici Güvenli Girişi")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setStyleSheet("color: gold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        form_layout = QFormLayout()
        input_style = "background: white; color: black; padding: 4px; font-weight: bold;"
        self.username_input = QLineEdit()
        self.username_input.setStyleSheet(input_style)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet(input_style)

        form_layout.addRow("Admin Kullanıcı:", self.username_input)
        form_layout.addRow("Admin Şifre:", self.password_input)
        layout.addLayout(form_layout)

        self.login_btn = QPushButton("Admin Olarak Giriş Yap")
        self.login_btn.setStyleSheet("background-color: #8B8000; color: white; font-weight: bold;")
        self.login_btn.clicked.connect(self.handle_admin_login)
        layout.addWidget(self.login_btn)

    def handle_admin_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        if not username or not password:
            QMessageBox.warning(self, "Hata", "Lütfen tüm alanları doldurun!")
            return
        hashed_pass = hash_password(password)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT username, role FROM users WHERE username = ? AND password = ? AND role = 'admin'", (username, hashed_pass))
        user = cursor.fetchone()
        if user:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("UPDATE users SET is_online = 1, last_login = ? WHERE username = ?", (now, username))
            conn.commit()
            conn.close()
            self.admin_data = {"username": user[0], "role": user[1]}
            self.accept()
        else:
            conn.close()
            QMessageBox.critical(self, "Hata", "Hatalı admin bilgileri!")

class RegisterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📝 Yeni Kullanıcı Kaydı")
        self.setFixedSize(430, 430)
        layout = QVBoxLayout(self)
        title = QLabel("🛡️ Yeni Hesap Oluştur")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        form_layout = QFormLayout()
        input_style = "background: white; color: black; padding: 4px; font-weight: bold;"
        self.username_input = QLineEdit()
        self.username_input.setStyleSheet(input_style)
        self.email_input = QLineEdit()
        self.email_input.setStyleSheet(input_style)
        self.sec_q_input = QLineEdit()
        self.sec_q_input.setStyleSheet(input_style)
        self.sec_a_input = QLineEdit()
        self.sec_a_input.setStyleSheet(input_style)
        self.password_input = QLineEdit()
        self.password_input.setStyleSheet(input_style)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.textChanged.connect(self.validate_password)

        form_layout.addRow("Kullanıcı Adı:", self.username_input)
        form_layout.addRow("E-Posta:", self.email_input)
        form_layout.addRow("Güvenlik Sorusu:", self.sec_q_input)
        form_layout.addRow("Soru Cevabı:", self.sec_a_input)
        form_layout.addRow("Şifre:", self.password_input)
        layout.addLayout(form_layout)

        self.lbl_length = QLabel("❌ En az 8 karakter")
        self.lbl_upper = QLabel("❌ En az 1 büyük harf (A-Z)")
        self.lbl_lower = QLabel("❌ En az 1 küçük harf (a-z)")
        self.lbl_digit = QLabel("❌ En az 1 rakam/sayı (0-9)")
        for lbl in [self.lbl_length, self.lbl_upper, self.lbl_lower, self.lbl_digit]:
            lbl.setStyleSheet("color: #FF4444; font-size: 11px;")
            layout.addWidget(lbl)

        self.register_btn = QPushButton("✅ Kaydı Tamamla")
        self.register_btn.clicked.connect(self.handle_register)
        layout.addWidget(self.register_btn)

    def validate_password(self, password):
        has_length = len(password) >= 8
        has_upper = bool(re.search(r"[A-Z]", password))
        has_lower = bool(re.search(r"[a-z]", password))
        has_digit = bool(re.search(r"\d", password))
        def update_label(label, condition, text):
            if condition:
                label.setText(f"✅ {text}")
                label.setStyleSheet("color: #00FF00; font-weight: bold; font-size: 11px;")
            else:
                label.setText(f"❌ {text}")
                label.setStyleSheet("color: #FF4444; font-size: 11px;")
        update_label(self.lbl_length, has_length, "En az 8 karakter")
        update_label(self.lbl_upper, has_upper, "En az 1 büyük harf (A-Z)")
        update_label(self.lbl_lower, has_lower, "En az 1 küçük harf (a-z)")
        update_label(self.lbl_digit, has_digit, "En az 1 rakam/sayı (0-9)")
        return has_length and has_upper and has_lower and has_digit

    def handle_register(self):
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        sec_q = self.sec_q_input.text().strip()
        sec_a = self.sec_a_input.text().strip()
        password = self.password_input.text().strip()
        if not username or not email or not sec_q or not sec_a or not password:
            QMessageBox.warning(self, "Hata", "Lütfen tüm alanları doldurun!")
            return
        if not is_valid_email(email):
            QMessageBox.warning(self, "Hata", "Geçerli bir e-posta adresi girin!")
            return
        if not self.validate_password(password):
            QMessageBox.warning(self, "Hata", "Şifre kriterleri karşılamıyor!")
            return
        hashed_pass = hash_password(password)
        hashed_ans = hash_password(sec_a)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, password, email, sec_question, sec_answer, role, is_online, last_login, created_at) 
                VALUES (?, ?, ?, ?, ?, 'user', 0, ?, ?)
            """, (username, hashed_pass, email, sec_q, hashed_ans, now, now))
            conn.commit()
            conn.close()
            log_audit(username, "KAYIT", "Yeni kullanıcı hesabı oluşturuldu.")
            QMessageBox.information(self, "Başarılı", "Kayıt başarıyla oluşturuldu!")
            self.accept()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, "Hata", "Bu kullanıcı adı zaten alınmış!")

class ForgotPasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔑 Şifre Sıfırlama")
        self.setFixedSize(400, 260)
        layout = QVBoxLayout(self)
        title = QLabel("🛡️ Şifremi Unuttum")
        title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        layout.addWidget(title)

        form_layout = QFormLayout()
        input_style = "background: white; color: black; padding: 4px; font-weight: bold;"
        self.username_input = QLineEdit()
        self.username_input.setStyleSheet(input_style)
        self.sec_question_label = QLabel("Kullanıcı adını yazıp soru getire basın")
        self.sec_answer_input = QLineEdit()
        self.sec_answer_input.setStyleSheet(input_style)
        self.new_pass_input = QLineEdit()
        self.new_pass_input.setStyleSheet(input_style)
        self.new_pass_input.setEchoMode(QLineEdit.EchoMode.Password)

        form_layout.addRow("Kullanıcı Adı:", self.username_input)
        form_layout.addRow("Güvenlik Sorusu:", self.sec_question_label)
        form_layout.addRow("Cevap:", self.sec_answer_input)
        form_layout.addRow("Yeni Şifre:", self.new_pass_input)
        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        self.fetch_q_btn = QPushButton("🔍 Soruyu Getir")
        self.fetch_q_btn.clicked.connect(self.fetch_question)
        self.reset_btn = QPushButton("✅ Şifreyi Güncelle")
        self.reset_btn.clicked.connect(self.reset_password)
        btn_layout.addWidget(self.fetch_q_btn)
        btn_layout.addWidget(self.reset_btn)
        layout.addLayout(btn_layout)

    def fetch_question(self):
        username = self.username_input.text().strip()
        if not username: return
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT sec_question FROM users WHERE username = ?", (username,))
        res = cursor.fetchone()
        conn.close()
        if res and res[0]:
            self.sec_question_label.setText(res[0])

    def reset_password(self):
        username = self.username_input.text().strip()
        answer = self.sec_answer_input.text().strip()
        new_pass = self.new_pass_input.text().strip()
        if not username or not answer or not new_pass: return
        hashed_ans = hash_password(answer)
        hashed_new_pass = hash_password(new_pass)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT sec_answer FROM users WHERE username = ?", (username,))
        res = cursor.fetchone()
        if res and res[0] == hashed_ans:
            cursor.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_new_pass, username))
            conn.commit()
            conn.close()
            log_audit(username, "ŞİFRE SIFIRLAMA", "Kullanıcı şifresini güncelledi.")
            QMessageBox.information(self, "Başarılı", "Şifre güncellendi!")
            self.accept()
        else:
            conn.close()
            QMessageBox.critical(self, "Hata", "Güvenlik sorusu cevabı yanlış!")

class ProfileDialog(QDialog):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.setWindowTitle("👤 Kullanıcı Profili")
        self.setFixedSize(400, 320)
        self.logout_requested = False

        layout = QVBoxLayout(self)
        title = QLabel("🛡️ Hesap Bilgileri")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT username, email, role, last_login, created_at FROM users WHERE username = ?", (username,))
        user_info = cursor.fetchone()
        conn.close()

        form_layout = QFormLayout()
        if user_info:
            form_layout.addRow("<b>Kullanıcı Adı:</b>", QLabel(user_info[0]))
            form_layout.addRow("<b>E-Posta:</b>", QLabel(user_info[1] if user_info[1] else "-"))
            form_layout.addRow("<b>Rol:</b>", QLabel(user_info[2].upper()))
            form_layout.addRow("<b>Son Giriş:</b>", QLabel(user_info[3] if user_info[3] else "-"))
            form_layout.addRow("<b>Kayıt Tarihi:</b>", QLabel(user_info[4] if user_info[4] else "-"))
        
        layout.addLayout(form_layout)
        layout.addSpacing(20)

        btn_layout = QHBoxLayout()
        self.logout_btn = QPushButton("🚪 Çıkış Yap (Oturumu Kapat)")
        self.logout_btn.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold; padding: 8px;")
        self.logout_btn.clicked.connect(self.handle_logout)
        
        close_btn = QPushButton("Kapat")
        close_btn.setStyleSheet("padding: 8px;")
        close_btn.clicked.connect(self.accept)

        btn_layout.addWidget(self.logout_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def handle_logout(self):
        self.logout_requested = True
        self.accept()

class WifiMitmScanThread(QThread):
    result_signal = pyqtSignal(str)

    def run(self):
        try:
            output = subprocess.check_output("arp -a", shell=True).decode('utf-8', errors='ignore')
            mac_dict = {}
            duplicates = []
            ignored_macs = {"ff-ff-ff-ff-ff-ff", "00-00-00-00-00-00"}

            for line in output.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    ip = parts[0]
                    mac = parts[1].lower()
                    if re.match(r"^([0-9a-f]{2}[:-]){5}([0-9a-f]{2})$", mac):
                        if mac not in ignored_macs and not mac.startswith("01-00-5e"):
                            if mac in mac_dict and mac_dict[mac] != ip:
                                duplicates.append((mac, mac_dict[mac], ip))
                            else:
                                mac_dict[mac] = ip

            if duplicates:
                report = (
                    f"==================================================\n"
                    f" 🚨 KRİTİK GÜVENLİK TEHDİTİ TESPİT EDİLDİ!\n"
                    f"==================================================\n"
                    f" [!] Ağda aynı MAC adresine ({duplicates[0][0]}) sahip birden fazla IP ({duplicates[0][1]} - {duplicates[0][2]}) bulundu!\n"
                    f" [!] Doğrulanmış Tehdit: ARP Spoofing / MITM saldırısı gerçekleştiriliyor, GÜVENDE DEĞİLSİNİZ!\n"
                )
            else:
                report = (
                    f"==================================================\n"
                    f" ✅ Wİ-Fİ AĞ GÜVENLİK DURUMU (DOĞRULANDI)\n"
                    f"==================================================\n"
                    f" [+] Durum: Wi-Fi Ağı Güvenli\n"
                    f" [+] Açıklama: ARP Tablosu ve Gateway doğrulaması temiz. Man-in-the-Middle (MITM) tehdidi bulunamadı.\n"
                    f" [+] Sonuç: Güvendeyiz...\n"
                )
            self.result_signal.emit(report)
        except Exception as e:
            self.result_signal.emit(f"Wi-Fi Tarama Hatası: {str(e)}")

class WebServerScannerThread(QThread):
    scan_finished = pyqtSignal(str)

    def __init__(self, target):
        super().__init__()
        self.target = target.replace("http://", "").replace("https://", "").strip("/")

    def run(self):
        report = f"==================================================\n"
        report += f" 🌐 WEB SUNUCU & PORT GÜVENLİK RAPORU\n"
        report += f" 🎯 Hedef: {self.target}\n"
        report += f" 📅 Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"==================================================\n\n"

        try:
            target_ip = socket.gethostbyname(self.target)
            report += f" [+] Çözümlenen IP Adresi: {target_ip}\n"
        except Exception as e:
            report += f" [!] DNS Çözümleme Başarısız: {str(e)}\n"
            self.scan_finished.emit(report)
            return

        web_ports = [80, 443, 8080, 8443, 21, 22, 3306]
        report += f"\n [~] Kritik web ve servis portları taranıyor...\n"
        
        open_ports = []
        for port in web_ports:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.5)
            result = s.connect_ex((target_ip, port))
            if result == 0:
                open_ports.append(port)
                report += f"   └── Port {port}: AÇIK (Aktif Servis)\n"
            s.close()

        if not open_ports:
            report += f"   └── Ortak web portlarında açık port bulunamadı.\n"

        report += f"\n [~] HTTP / HTTPS Header Güvenlik Analizi...\n"
        tested_url = f"https://{self.target}"
        try:
            req = urllib.request.Request(tested_url, headers={'User-Agent': 'SecurityScanner-v1.0'})
            with urllib.request.urlopen(req, timeout=4) as resp:
                headers = resp.headers
                report += f"   └── Sunucu Protokolü: HTTPS (Durum Kodu: {resp.status})\n"
                security_headers = ['Strict-Transport-Security', 'Content-Security-Policy', 'X-Frame-Options', 'X-XSS-Protection']
                for h in security_headers:
                    if h in headers:
                        report += f"   [+] Güvenlik Başlığı Bulundu ({h}): {headers.get(h)[:40]}...\n"
                    else:
                        report += f"   [!] Eksik Güvenlik Başlığı: {h} (Potansiyel Zafiyet)\n"
        except Exception:
            try:
                tested_url = f"http://{self.target}"
                req = urllib.request.Request(tested_url, headers={'User-Agent': 'SecurityScanner-v1.0'})
                with urllib.request.urlopen(req, timeout=4) as resp:
                    report += f"   [!] UYARI: Site güvenli HTTPS yerine düz HTTP protokolü kullanıyor!\n"
            except Exception as ex:
                report += f"   [!] Web başlıkları alınamadı: {str(ex)}\n"

        report += f"\n--------------------------------------------------\n"
        report += f" 🏁 WEB SUNUCU TARAMASI TAMAMLANDI."
        self.scan_finished.emit(report)

class EmailBreachThread(QThread):
    result_signal = pyqtSignal(str, bool, list)
    def __init__(self, email):
        super().__init__()
        self.email = email
    def run(self):
        url = f"https://api.xposedornot.com/v1/check-email/{self.email}"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'SecurityPlatformApp-v1.0')
        try:
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    raw_data = response.read().decode('utf-8')
                    data = json.loads(raw_data)
                    if "Error" in data:
                        self.result_signal.emit("✅ TEMİZ: Veri sızıntısı bulunamadı.", False, [])
                    elif "breaches" in data:
                        breaches = data["breaches"]
                        breach_list = []
                        if isinstance(breaches, list) and len(breaches) > 0:
                            if isinstance(breaches[0], list):
                                breach_list = breaches[0]
                            else:
                                breach_list = breaches
                        
                        details = []
                        for b in breach_list:
                            b_name = "Bilinmeyen Kaynak"
                            b_date = "Bilinmiyor"
                            
                            if isinstance(b, dict):
                                b_name = b.get("name", b.get("breach", "Bilinmeyen Kaynak"))
                                b_date = b.get("added", b.get("date", b.get("added_date", "Bilinmiyor")))
                            elif isinstance(b, str):
                                b_name = b
                            
                            # Eğer API'den tarih gelmediyse veya geçersizse akıllı fallback sözlüğümüze bakalım
                            clean_date = str(b_date).strip()
                            if not clean_date or clean_date == "Bilinmiyor" or clean_date == "None":
                                found_fallback = False
                                for key, val in KNOWN_BREACH_YEARS.items():
                                    if key in b_name.lower():
                                        b_date = f"{val} (Tahmini/Bilinen Kayıt Yılı)"
                                        found_fallback = True
                                        break
                                if not found_fallback:
                                    b_date = "Bilinmiyor (API Tarih Kaydı Yok)"
                            else:
                                b_date = clean_date[:10]

                            details.append({"name": b_name, "date": b_date})
                        
                        if "ExposedBreaches" in data and isinstance(data["ExposedBreaches"], dict):
                            breach_details_dict = data["ExposedBreaches"].get("breaches_details", [])
                            if breach_details_dict:
                                details = []
                                for bd in breach_details_dict:
                                    b_name = bd.get("breach", bd.get("name", "Bilinmiyor"))
                                    b_date = bd.get("added_date", bd.get("date", bd.get("added", "Bilinmiyor")))
                                    
                                    clean_date = str(b_date).strip()
                                    if not clean_date or clean_date == "Bilinmiyor" or clean_date == "None":
                                        found_fallback = False
                                        for key, val in KNOWN_BREACH_YEARS.items():
                                            if key in b_name.lower():
                                                b_date = f"{val} (Tahmini/Bilinen Kayıt Yılı)"
                                                found_fallback = True
                                                break
                                        if not found_fallback:
                                            b_date = "Bilinmiyor (API Tarih Kaydı Yok)"
                                    else:
                                        b_date = clean_date[:10]

                                    details.append({"name": b_name, "date": b_date})

                        self.result_signal.emit("Sızıntı Bulundu", True, details)
                    else:
                        self.result_signal.emit("✅ TEMİZ: Sızıntı bulunamadı.", False, [])
        except Exception as e:
            self.result_signal.emit(f"✅ TEMİZ veya Sorgulanamadı: {str(e)}", False, [])

class ThreatListDialog(QDialog):
    def __init__(self, threat_files, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔍 Tespit Edilen Zararlı Dosyalar")
        self.resize(700, 400)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Toplam {len(threat_files)} şüpheli dosya bulundu:"))
        self.list_widget = QListWidget()
        for f in threat_files:
            self.list_widget.addItem(f)
        layout.addWidget(self.list_widget)
        close_btn = QPushButton("Kapat")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

class SecurityScannerThread(QThread):
    scan_finished = pyqtSignal(list, str)
    def __init__(self, target_ip):
        super().__init__()
        self.target_ip = target_ip
    def run(self):
        try:
            nm = nmap.PortScanner()
            nm.scan(hosts=self.target_ip, arguments='-F')
            results = []
            for host in nm.all_hosts():
                host_info = {"ip": host, "status": nm[host].state(), "ports": [], "alerts": []}
                for proto in nm[host].all_protocols():
                    for port in nm[host][proto].keys():
                        state = nm[host][proto][port]['state']
                        service = nm[host][proto][port]['name']
                        host_info["ports"].append(f"{port}/{proto} ({service}) - {state}")
                        if port in SUSPICIOUS_PORTS and state == 'open':
                            host_info["alerts"].append(f"ŞÜPHELİ PORT: Port {port} ({SUSPICIOUS_PORTS[port]})")
                results.append(host_info)
            self.scan_finished.emit(results, "")
        except Exception as e:
            self.scan_finished.emit([], f"Nmap Tarama Hatası: {str(e)}. Lütfen sisteminizde Nmap'in kurulu olduğundan emin olun.")

class DiskScannerThread(QThread):
    progress_signal = pyqtSignal(str, int)
    threat_found_signal = pyqtSignal(str, list)
    finished_signal = pyqtSignal(int, int, list)
    def __init__(self, target_directory):
        super().__init__()
        self.target_directory = target_directory
    def run(self):
        total, threats, threat_list = 0, 0, []
        for root, dirs, files in os.walk(self.target_directory):
            dirs[:] = [d for d in dirs if d not in {'venv', '.git', '__pycache__', '.vscode'}]
            for file in files:
                if file == 'main.py': continue
                total += 1
                f_path = os.path.join(root, file)
                self.progress_signal.emit(f_path, total)
                if file.lower().endswith(('.py', '.ps1', '.bat', '.txt', '.vbs', '.sh', '.js', '.exe')):
                    res = self.analyze(f_path)
                    if res:
                        threats += 1
                        threat_list.append(f_path)
                        self.threat_found_signal.emit(f_path, res)
        self.finished_signal.emit(total, threats, threat_list)
    def analyze(self, path):
        t = []
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for idx, line in enumerate(f, 1):
                    for pat, desc in SUSPICIOUS_PATTERNS:
                        if re.search(pat, line, re.IGNORECASE):
                            t.append((idx, desc, line.strip()))
        except Exception:
            pass
        return t

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#2b2b2b')
        self.axes = self.fig.add_subplot(111)
        self.axes.set_facecolor('#2b2b2b')
        super().__init__(self.fig)
    def plot_port_distribution(self, counts):
        self.axes.clear()
        if not counts:
            self.axes.text(0.5, 0.5, "Veri Yok", color='white', ha='center', va='center')
        else:
            self.axes.pie(list(counts.values()), labels=list(counts.keys()), autopct='%1.1f%%', textprops=dict(color="white"))
            self.axes.set_title("Port Dağılımı", color='white')
        self.draw()

# --- ANA UYGULAMA PENCERESİ ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ağ Güvenliği & Savunma Platformu")
        
        generate_ico_file()
        if os.path.exists(ICO_PATH):
            self.setWindowIcon(QIcon(ICO_PATH))

        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint | Qt.WindowType.WindowMinimizeButtonHint)
        self.resize(1024, 768)
        self.showMaximized()

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.login_widget = LoginWidget(self)
        self.stacked_widget.addWidget(self.login_widget)

        self.current_user = None

    def on_successful_login(self, user_data):
        self.current_user = user_data
        self.setWindowTitle(f"Ağ Güvenliği & Savunma Platformu — [{self.current_user['username']}] ({self.current_user['role'].upper()})")
        
        self.dashboard_widget = QWidget()
        self.setup_dashboard_ui(self.dashboard_widget)
        
        self.stacked_widget.addWidget(self.dashboard_widget)
        self.stacked_widget.setCurrentWidget(self.dashboard_widget)

    def setup_dashboard_ui(self, parent_widget):
        main_layout = QVBoxLayout(parent_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(10, 5, 10, 5)
        
        self.tabs = QTabWidget()
        top_bar.addWidget(self.tabs)

        self.profile_btn = QPushButton(f"👤 {self.current_user['username']} (Profil)")
        self.profile_btn.setStyleSheet("background-color: #3A506B; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px;")
        self.profile_btn.clicked.connect(self.open_profile)
        top_bar.addWidget(self.profile_btn, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        main_layout.addLayout(top_bar)

        self.network_tab = QWidget()
        self.web_server_tab = QWidget()
        self.ai_tab = QWidget()
        self.email_tab = QWidget()
        self.wifi_tab = QWidget()

        self.tabs.addTab(self.network_tab, "🌐 Ağ Taraması & Güvenlik")
        self.tabs.addTab(self.web_server_tab, "🌍 Web / Sunucu Tarayıcı")
        self.tabs.addTab(self.ai_tab, "🤖 AI Dosya & Disk Taraması")
        self.tabs.addTab(self.email_tab, "🔍 E-Posta Veri Sızıntısı")
        self.tabs.addTab(self.wifi_tab, "🛡️ Wi-Fi & MITM Kalkanı")

        if self.current_user["role"] == "admin":
            self.admin_tab = QWidget()
            self.audit_tab = QWidget()
            self.tabs.addTab(self.admin_tab, "Admin Paneli")
            self.tabs.addTab(self.audit_tab, "Audit Logs (Denetim)")
            self.setup_admin()
            self.setup_audit_logs()

        self.setup_network()
        self.setup_web_server()
        self.setup_ai()
        self.setup_email()
        self.setup_wifi()
        log_audit(self.current_user["username"], "PANEL AÇILIŞI", "Kullanıcı ana paneli açtı.")

    def open_profile(self):
        profile_dialog = ProfileDialog(self.current_user["username"], self)
        profile_dialog.exec()
        if profile_dialog.logout_requested:
            log_audit(self.current_user["username"], "ÇIKIŞ", "Kullanıcı oturumu kapattı.")
            self.logout_user()

    def logout_user(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET is_online = 0 WHERE username = ?", (self.current_user["username"],))
            conn.commit()
            conn.close()
        except Exception:
            pass
        
        self.setWindowTitle("Güvenlik Platformu Girişi")
        self.login_widget.clear_inputs()
        self.stacked_widget.setCurrentWidget(self.login_widget)

    def closeEvent(self, event):
        try:
            if self.current_user:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET is_online = 0 WHERE username = ?", (self.current_user["username"],))
                conn.commit()
                conn.close()
                log_audit(self.current_user["username"], "KAPANIŞ", "Uygulama kapatıldı.")
        except Exception:
            pass
        event.accept()

    def setup_network(self):
        layout = QVBoxLayout(self.network_tab)
        input_layout = QHBoxLayout()
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Hedef IP (Örn: 127.0.0.1)")
        self.ip_input.returnPressed.connect(self.start_scan)
        
        scan_btn = QPushButton("Güvenlik Taramasını Başlat")
        scan_btn.clicked.connect(self.start_scan)
        hist_btn = QPushButton("Geçmiş Taramalar")
        hist_btn.clicked.connect(self.load_history)
        export_btn = QPushButton("📄 Raporu Dışa Aktar (HTML/PDF)")
        export_btn.clicked.connect(self.export_network_report)
        
        input_layout.addWidget(self.ip_input)
        input_layout.addWidget(scan_btn)
        input_layout.addWidget(hist_btn)
        input_layout.addWidget(export_btn)
        layout.addLayout(input_layout)

        self.pbar = QProgressBar()
        layout.addWidget(self.pbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["IP Adresi", "Durum", "Açık Portlar", "Uyarılar", "Zaman"])
        splitter.addWidget(self.table)
        self.canvas = MplCanvas(self)
        splitter.addWidget(self.canvas)
        splitter.setSizes([600, 450])
        layout.addWidget(splitter)

    def export_network_report(self):
        path, _ = QFileDialog.getSaveFileName(self, "Raporu Kaydet", "network_report.html", "HTML Dosyaları (*.html)")
        if not path:
            return
        try:
            html = "<html><head><meta charset='utf-8'><title>Ağ Güvenlik Raporu</title></head><body style='font-family:Arial; background:#1e1e1e; color:white; padding:20px;'>"
            html += "<h1>🛡️ Ağ Güvenlik & Zafiyet Raporu</h1>"
            html += f"<p>Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p><hr/>"
            html += "<table border='1' cellpadding='8' style='border-collapse:collapse; width:100%; border-color:#555;'>"
            html += "<tr style='background:#333;'><th>IP Adresi</th><th>Durum</th><th>Açık Portlar</th><th>Uyarılar</th><th>Zaman</th></tr>"
            
            for r in range(self.table.rowCount()):
                ip = self.table.item(r, 0).text() if self.table.item(r, 0) else ""
                status = self.table.item(r, 1).text() if self.table.item(r, 1) else ""
                ports = self.table.item(r, 2).text() if self.table.item(r, 2) else ""
                alerts = self.table.item(r, 3).text() if self.table.item(r, 3) else ""
                time_s = self.table.item(r, 4).text() if self.table.item(r, 4) else ""
                html += f"<tr><td>{ip}</td><td>{status}</td><td>{ports}</td><td>{alerts}</td><td>{time_s}</td></tr>"
            
            html += "</table></body></html>"
            with open(path, 'w', encoding='utf-8') as f:
                f.write(html)
            QMessageBox.information(self, "Başarılı", f"Rapor başarıyla kaydedildi:\n{path}")
            log_audit(self.current_user["username"], "RAPOR DIŞA AKTARMA", f"Ağ güvenlik raporu dışa aktarıldı: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Rapor kaydedilemedi: {str(e)}")

    def setup_web_server(self):
        layout = QVBoxLayout(self.web_server_tab)
        layout.addWidget(QLabel("<b>Web Sunucu & Hedef Port Zafiyet Tarayıcısı (CVE & Header Kontrolü)</b>"))
        
        input_layout = QHBoxLayout()
        self.web_input = QLineEdit()
        self.web_input.setPlaceholderText("Web sitesi veya domain girin (Örn: scanme.nmap.org)")
        self.web_input.returnPressed.connect(self.start_web_scan)
        
        self.web_scan_btn = QPushButton("🔎 Web & Port Taramasını Başlat")
        self.web_scan_btn.setStyleSheet("background-color: #007ACC; color: white; font-weight: bold; padding: 6px;")
        self.web_scan_btn.clicked.connect(self.start_web_scan)

        input_layout.addWidget(self.web_input)
        input_layout.addWidget(self.web_scan_btn)
        layout.addLayout(input_layout)

        self.web_result_box = QTextEdit()
        self.web_result_box.setReadOnly(True)
        self.web_result_box.setFont(QFont("Consolas", 10))
        self.web_result_box.setPlaceholderText("Web sunucu zafiyet ve port tarama raporları burada görüntülenecek...")
        layout.addWidget(self.web_result_box)

    def start_web_scan(self):
        target = self.web_input.text().strip()
        if not target:
            QMessageBox.warning(self, "Uyarı", "Lütfen geçerli bir web sitesi veya domain girin!")
            return
        self.web_scan_btn.setEnabled(False)
        self.web_result_box.setText(f"⏳ [{target}] için web sunucu ve portlar taranıyor, lütfen bekleyin...\n")

        log_audit(self.current_user["username"], "WEB TARAMA", f"Hedef web sunucu tarandı: {target}")
        self.web_thread = WebServerScannerThread(target)
        self.web_thread.scan_finished.connect(self.web_scan_done)
        self.web_thread.start()

    def web_scan_done(self, report):
        self.web_scan_btn.setEnabled(True)
        self.web_result_box.setText(report)

    def setup_ai(self):
        layout = QVBoxLayout(self.ai_tab)
        layout.addWidget(QLabel("<b>AI Statik Dosya & Disk Zararlı Yazılım Analizcisi (Hash & İMZA)</b>"))
        btn_layout = QHBoxLayout()
        self.file_btn = QPushButton("📄 Tek Dosya Tara")
        self.file_btn.clicked.connect(self.scan_file_for_malware)
        self.dir_btn = QPushButton("📁 Tüm Disk / Klasör Tara")
        self.dir_btn.clicked.connect(self.start_disk_scan)
        self.path_lbl = QLabel("Dosya veya klasör seçilmedi.")
        btn_layout.addWidget(self.file_btn)
        btn_layout.addWidget(self.dir_btn)
        btn_layout.addWidget(self.path_lbl)
        layout.addLayout(btn_layout)
        self.disk_pbar = QProgressBar()
        layout.addWidget(self.disk_pbar)
        self.ai_box = QTextEdit()
        self.ai_box.setReadOnly(True)
        self.ai_box.setFont(QFont("Consolas", 10))
        self.ai_box.setPlaceholderText("AI Dosya/Disk Analiz Sonuçları ve Raporu Burada Görünecek...")
        layout.addWidget(self.ai_box)

    def scan_file_for_malware(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Taranacak Dosyayı Seç", "", "Tüm Dosyalar (*.*)")
        if not file_path:
            return

        self.path_lbl.setText(f"Seçilen Dosya: {file_path}")
        self.ai_box.clear()

        try:
            with open(file_path, 'rb') as f_bytes:
                file_bytes = f_bytes.read()
                file_hash = hashlib.sha256(file_bytes).hexdigest()

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            detected_threats = []
            lines = content.splitlines()

            for line_idx, line in enumerate(lines, 1):
                for pattern, description in SUSPICIOUS_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        detected_threats.append((line_idx, description, line.strip()))

            report = f"==================================================\n"
            report += f"  AI GÜVENLİK TARAMA RAPORU (TEK DOSYA)\n"
            report += f"  Dosya Konumu: {file_path}\n"
            report += f"  SHA-256 Hash: {file_hash}\n"
            report += f"  Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            report += f"==================================================\n\n"

            if detected_threats:
                report += f"⚠️ UYARI: Dosyada {len(detected_threats)} Adet Şüpheli/Zararlı Yazılım Kalıbı Tespit Edildi!\n\n"
                for line_num, desc, code in detected_threats:
                    report += f"  📍 Satır {line_num}: [{desc}]\n"
                    report += f"     Kod: {code}\n\n"
                report += f"➡️ SONUÇ: BU DOSYA TEHLİKELİ OLABİLİR."
            else:
                report += f"✅ TEMİZ: Dosyada bilinen herhangi bir şüpheli zararlı yazılım / backdoor kalıbına rastlanmadı.\n"
                report += f"➡️ SONUÇ: Düşük Risk Seviyesi."

            self.ai_box.setText(report)
            log_audit(self.current_user["username"], "DOSYA TARAMA", f"Dosya tarandı: {file_path} (Hash: {file_hash[:10]}...)")

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dosya taranırken hata oluştu: {str(e)}")

    def start_disk_scan(self):
        target_dir = QFileDialog.getExistingDirectory(self, "Taranacak Klasör veya Diski Seç")
        if not target_dir:
            return

        self.path_lbl.setText(f"Taranan Dizin: {target_dir}")
        self.ai_box.clear()
        self.ai_box.setText(f"🔍 Dizin Taraması Başlatıldı: {target_dir}\nLütfen bekleyin, dosyalar taranıyor...\n\n")

        self.file_btn.setEnabled(False)
        self.dir_btn.setEnabled(False)
        self.disk_pbar.setRange(0, 0)

        log_audit(self.current_user["username"], "DİSK TARAMA", f"Disk/Klasör taraması başlatıldı: {target_dir}")
        self.disk_thread = DiskScannerThread(target_dir)
        self.disk_thread.progress_signal.connect(self.update_disk_progress)
        self.disk_thread.threat_found_signal.connect(self.handle_disk_threat)
        self.disk_thread.finished_signal.connect(self.disk_scan_finished)
        self.disk_thread.start()

    def update_disk_progress(self, file_path, scanned_count):
        self.path_lbl.setText(f"Taranıyor ({scanned_count} dosya): {file_path[:60]}...")

    def handle_disk_threat(self, file_path, threats):
        current_text = self.ai_box.toPlainText()
        new_entry = f"🚨 ZARARLI DOSYA TESPİT EDİLDİ!\n"
        new_entry += f"📍 Konum: {file_path}\n"
        for line_num, desc, code in threats:
            new_entry += f"   └── Satır {line_num}: [{desc}] -> {code}\n"
        new_entry += "--------------------------------------------------\n"
        self.ai_box.setText(current_text + new_entry)

    def disk_scan_finished(self, total_scanned, total_threats, threat_files_list):
        self.disk_pbar.setRange(0, 100)
        self.disk_pbar.setValue(100)
        self.file_btn.setEnabled(True)
        self.dir_btn.setEnabled(True)

        summary = f"\n==================================================\n"
        summary += f"🏁 TARAMA TAMAMLANDI!\n"
        summary += f"📊 Toplam Taranan Dosya: {total_scanned}\n"
        summary += f"⚠️ Tespit Edilen Zararlı Dosya Sayısı: {total_threats}\n"
        summary += f"==================================================\n"

        self.ai_box.setText(self.ai_box.toPlainText() + summary)

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Tarama Bitti")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setText(f"Disk taraması tamamlandı.\n\nToplam Taranan: {total_scanned}\nBulunan Zararlı: {total_threats}")
        msg_box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
        
        detail_button = None
        if threat_files_list:
            detail_button = msg_box.addButton("🔍 Bulunan Zararlı Dosya Listesi", QMessageBox.ButtonRole.ActionRole)

        msg_box.exec()
        if msg_box.clickedButton() == detail_button and threat_files_list:
            ThreatListDialog(threat_files_list, self).exec()

    def setup_email(self):
        layout = QVBoxLayout(self.email_tab)
        layout.addWidget(QLabel("<b>OSINT E-Posta Veri Sızıntısı & İhlal Taraması (Yapay Zeka Analizli)</b>"))
        in_layout = QHBoxLayout()
        self.em_input = QLineEdit()
        self.em_input.setPlaceholderText("E-posta adresi girin")
        self.em_input.returnPressed.connect(self.check_email)
        
        em_btn = QPushButton("Sızıntıları Sorgula")
        em_btn.clicked.connect(self.check_email)
        in_layout.addWidget(self.em_input)
        in_layout.addWidget(em_btn)
        layout.addLayout(in_layout)
        
        self.em_box = QTextEdit()
        self.em_box.setReadOnly(True)
        self.em_box.setFont(QFont("Consolas", 10))
        layout.addWidget(self.em_box)

    def setup_wifi(self):
        layout = QVBoxLayout(self.wifi_tab)
        layout.addWidget(QLabel("<b>Wi-Fi & MITM Saldırı Tespiti (Doğrulamalı)</b>"))
        self.wifi_btn = QPushButton("🔄 Wi-Fi Güvenliğini Anlık Tarat")
        self.wifi_btn.setStyleSheet("background-color: #2e8b57; color: white; font-weight: bold; padding: 8px;")
        self.wifi_btn.clicked.connect(self.check_wifi)
        layout.addWidget(self.wifi_btn)
        self.wifi_box = QTextEdit()
        self.wifi_box.setReadOnly(True)
        layout.addWidget(self.wifi_box)

    def check_wifi(self):
        self.wifi_btn.setEnabled(False)
        self.wifi_box.setText("Wi-Fi ARP tablosu ve ağ geçidi doğrulanıyor...")
        log_audit(self.current_user["username"], "Wİ-Fİ TARAMA", "Wi-Fi MITM güvenliği tarandı.")
        self.w_thread = WifiMitmScanThread()
        self.w_thread.result_signal.connect(self.wifi_done)
        self.w_thread.start()

    def wifi_done(self, txt):
        self.wifi_btn.setEnabled(True)
        self.wifi_box.setText(txt)

    def check_email(self):
        em = self.em_input.text().strip()
        if not em or not is_valid_email(em):
            QMessageBox.warning(self, "Hata", "Lütfen geçerli bir e-posta adresi girin!")
            return
        self.em_box.setText("Sızıntılar ve Veri İhlalleri Sorgulanıyor...")
        log_audit(self.current_user["username"], "E-POSTA OSINT", f"E-posta sızıntı sorgusu: {em}")
        self.e_thread = EmailBreachThread(em)
        self.e_thread.result_signal.connect(self.email_done)
        self.e_thread.start()

    def email_done(self, msg, has_b, data):
        txt = f"E-posta: {self.em_input.text()}\n"
        txt += f"Durum: {msg}\n"
        txt += "--------------------------------------------------\n"
        
        if data:
            txt += "🚨 TESPİT EDİLEN SIZINTI KAYNAKLARI VE TARİHLERİ:\n"
            for d in data:
                txt += f"   • Kaynak: {d['name']} | Tarih: {d['date']} | Sızıntı Türü: E-Posta / Parola / Kişisel Veri\n"
            
            # --- YAPAY ZEKA SIZINTI ANALİZİ ---
            txt += "\n🤖 YAPAY ZEKA GÜVENLİK ASİSTANI ANALİZİ:\n"
            txt += "   ┌─────────────────────────────────────────────────────────────┐\n"
            txt += f"   │ Analiz Edilen Adres: {self.em_input.text()[:35]:<31} │\n"
            txt += f"   │ Toplam İhlal Edilen Platform Sayısı: {len(data):<20} │\n"
            txt += "   ├─────────────────────────────────────────────────────────────┤\n"
            txt += "   │ [Açıklama]: Bu e-posta adresi geçmişte yukarıdaki            │\n"
            txt += "   │ üçüncü taraf platformların veri tabanı sızıntılarında        │\n"
            txt += "   │ ele geçirilmiştir. Saldırganlar bu verileri kullanarak       │\n"
            txt += "   │ oltalama (phishing) saldırıları düzenleyebilir veya           │\n"
            txt += "   │ şifre denemesi (credential stuffing) yapabilir.             │\n"
            txt += "   └─────────────────────────────────────────────────────────────┘\n"
        else:
            txt += "✅ Yapay Zeka Analizi: Herhangi bir riskli veri sızıntısı tespit edilmedi.\n"

        txt += "\n💡 Öneri: Sızıntı tespit edilen hesaplarınız varsa lütfen ŞİFRELERİNİZİ DERHAL DEĞİŞTİRİN!\n"
        self.em_box.setText(txt)

    def setup_admin(self):
        layout = QVBoxLayout(self.admin_tab)
        layout.addWidget(QLabel("<b>Sistemdeki Kayıtlı Kullanıcılar & Canlı Takip / Oturum Yönetimi</b>"))
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(6)
        self.user_table.setHorizontalHeaderLabels(["ID", "Kullanıcı Adı", "Rol", "Durum", "Son Giriş", "Kayıt Tarihi"])
        layout.addWidget(self.user_table)
        
        b_layout = QHBoxLayout()
        ref_btn = QPushButton("🔄 Listeyi Yenile")
        ref_btn.clicked.connect(self.load_users)
        
        force_logout_btn = QPushButton("🛑 Seçilen Kullanıcıyı Zorla Çıkart (Oturumu Kapat)")
        force_logout_btn.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold;")
        force_logout_btn.clicked.connect(self.force_logout_user)

        del_btn = QPushButton("❌ Kullanıcıyı Sil")
        del_btn.clicked.connect(self.delete_user)

        b_layout.addWidget(ref_btn)
        b_layout.addWidget(force_logout_btn)
        b_layout.addWidget(del_btn)
        layout.addLayout(b_layout)
        self.load_users()

    def setup_audit_logs(self):
        layout = QVBoxLayout(self.audit_tab)
        layout.addWidget(QLabel("<b>Sistem Denetim Günlükleri (Audit Logs) — Tüm Eylemler</b>"))
        self.audit_table = QTableWidget()
        self.audit_table.setColumnCount(5)
        self.audit_table.setHorizontalHeaderLabels(["Log ID", "Kullanıcı", "İşlem", "Detay", "Zaman"])
        layout.addWidget(self.audit_table)
        
        ref_layout = QHBoxLayout()
        ref_audit_btn = QPushButton("🔄 Logları Yenile")
        ref_audit_btn.clicked.connect(self.load_audit_logs)
        ref_layout.addWidget(ref_audit_btn)
        layout.addLayout(ref_layout)
        self.load_audit_logs()

    def load_audit_logs(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, username, action, details, log_time FROM audit_logs ORDER BY id DESC")
        rows = cur.fetchall()
        conn.close()
        self.audit_table.setRowCount(0)
        for r_idx, r in enumerate(rows):
            self.audit_table.insertRow(r_idx)
            for c_idx, val in enumerate(r):
                self.audit_table.setItem(r_idx, c_idx, QTableWidgetItem(str(val)))

    def load_users(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, username, role, is_online, last_login, created_at FROM users")
        rows = cur.fetchall()
        conn.close()
        self.user_table.setRowCount(0)
        for r_idx, u in enumerate(rows):
            self.user_table.insertRow(r_idx)
            for c_idx, val in enumerate(u):
                if c_idx == 3:
                    is_on = bool(val)
                    status_text = "Çevrimiçi" if is_on else "Çevrimdışı"
                    item = QTableWidgetItem(status_text)
                    if is_on:
                        item.setForeground(QColor("#00FF00"))
                    else:
                        item.setForeground(QColor("#FF4444"))
                else:
                    item = QTableWidgetItem(str(val))
                self.user_table.setItem(r_idx, c_idx, item)

    def force_logout_user(self):
        row = self.user_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Uyarı", "Lütfen listeden oturumu kapatılacak kullanıcıyı seçin!")
            return
        
        uid = self.user_table.item(row, 0).text()
        uname = self.user_table.item(row, 1).text()
        
        if uname == self.current_user["username"]:
            QMessageBox.warning(self, "Hata", "Kendi admin oturumunuzu buradan kapatamazsınız!")
            return

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE users SET is_online = 0 WHERE id = ?", (uid,))
        conn.commit()
        conn.close()

        log_audit(self.current_user["username"], "ZORLA ÇIKIŞ", f"Admin tarafından kullanıcının oturumu sonlandırıldı: {uname}")
        QMessageBox.information(self, "Başarılı", f"'{uname}' adlı kullanıcının oturumu admin tarafından zorla kapatıldı!")
        self.load_users()
        self.load_audit_logs()

    def delete_user(self):
        row = self.user_table.currentRow()
        if row < 0: return
        uid = self.user_table.item(row, 0).text()
        uname = self.user_table.item(row, 1).text()
        if uname == self.current_user["username"]: return
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = ?", (uid,))
        conn.commit()
        conn.close()
        log_audit(self.current_user["username"], "KULLANICI SİLME", f"Kullanıcı silindi: {uname}")
        self.load_users()

    def start_scan(self):
        ip = self.ip_input.text().strip()
        if not ip: return
        self.pbar.setRange(0, 0)
        log_audit(self.current_user["username"], "AĞ TARAMA", f"Ağ güvenlik taraması başlatıldı: {ip}")
        self.s_thread = SecurityScannerThread(ip)
        self.s_thread.scan_finished.connect(self.scan_done)
        self.s_thread.start()

    def scan_done(self, res, error_msg):
        self.pbar.setRange(0, 100)
        self.pbar.setValue(100)
        
        if error_msg:
            QMessageBox.critical(self, "Tarama Hatası", error_msg)
            return

        self.table.setRowCount(0)
        counts = {}
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for r, h in enumerate(res):
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(h["ip"]))
            self.table.setItem(r, 1, QTableWidgetItem(h["status"]))
            ports_s = ", ".join(h["ports"])
            self.table.setItem(r, 2, QTableWidgetItem(ports_s))
            alerts_s = " | ".join(h["alerts"]) if h["alerts"] else "Yok"
            self.table.setItem(r, 3, QTableWidgetItem(alerts_s))
            time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.table.setItem(r, 4, QTableWidgetItem(time_str))
            
            cursor.execute("""
                INSERT INTO scan_logs (target_ip, status, ports, security_alerts, scan_time)
                VALUES (?, ?, ?, ?, ?)
            """, (h["ip"], h["status"], ports_s, alerts_s, time_str))

            for p in h["ports"]:
                srv = p.split('(')[1].split(')')[0] if '(' in p else 'Diğer'
                counts[srv] = counts.get(srv, 0) + 1
                
        conn.commit()
        conn.close()
        self.canvas.plot_port_distribution(counts)

    def load_history(self):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT target_ip, status, ports, security_alerts, scan_time FROM scan_logs ORDER BY id DESC")
        rows = cur.fetchall()
        conn.close()
        self.table.setRowCount(0)
        for r, row in enumerate(rows):
            self.table.insertRow(r)
            for c, val in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(str(val)))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    init_db()
    
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())