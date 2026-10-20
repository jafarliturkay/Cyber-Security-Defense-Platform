import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, 
    QVBoxLayout, QPushButton, QStackedWidget, QLabel,
    QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt

from modules.scanner import NetworkScanner
from database.db_manager import DatabaseManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cybersecurity Assessment & Attack Simulation Platform")
        self.setGeometry(100, 100, 1100, 700)
        self.db = DatabaseManager()
        self.scanner = NetworkScanner()
        
        # Ana Düzen (Sol Menü + Sağ İçerik)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Sol Menü Paneli
        sidebar = QWidget()
        sidebar.setStyleSheet("background-color: #1e1e2e; min-width: 200px; max-width: 220px;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        title = QLabel("CYBER PLATFORM")
        title.setStyleSheet("color: #cdd6f4; font-weight: bold; font-size: 16px; margin: 15px 0px;")
        sidebar_layout.addWidget(title)
        
        self.btn_dashboard = QPushButton("Genel Bakış")
        self.btn_network = QPushButton("Ağ & Port Taraması")
        self.btn_mitm = QPushButton("MITM Simülasyonu")
        self.btn_bruteforce = QPushButton("Brute-Force Testi")
        self.btn_reports = QPushButton("Raporlar")
        
        menu_buttons = [
            self.btn_dashboard, self.btn_network, 
            self.btn_mitm, self.btn_bruteforce, self.btn_reports
        ]
        
        for btn in menu_buttons:
            btn.setStyleSheet("""
                QPushButton {
                    color: #a6adc8; background-color: transparent; border: none;
                    text-align: left; padding: 12px; font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #313244; color: #cdd6f4; border-radius: 5px;
                }
            """)
            sidebar_layout.addWidget(btn)
            
        main_layout.addWidget(sidebar)
        
        # 2. Sağ İçerik Alanı
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)
        
        # Sayfalar
        self.init_dashboard_page()
        self.init_network_page()
        
        self.stacked_widget.addWidget(self.dashboard_page) # Index 0
        self.stacked_widget.addWidget(self.network_page)   # Index 1
        self.stacked_widget.addWidget(QLabel("MITM Saldırı Simülasyonu Ekranı", alignment=Qt.AlignmentFlag.AlignCenter))
        self.stacked_widget.addWidget(QLabel("Brute-Force Test Ekranı", alignment=Qt.AlignmentFlag.AlignCenter))
        self.stacked_widget.addWidget(QLabel("Raporlama Ekranı", alignment=Qt.AlignmentFlag.AlignCenter))
        
        # Menü Bağlantıları
        self.btn_dashboard.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        self.btn_network.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        self.btn_mitm.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        self.btn_bruteforce.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(3))
        self.btn_reports.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(4))

    def init_dashboard_page(self):
        self.dashboard_page = QWidget()
        layout = QVBoxLayout(self.dashboard_page)
        lbl = QLabel("Platforma Hoş Geldiniz! Sol menüden işlem seçebilirsiniz.")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

    def init_network_page(self):
        self.network_page = QWidget()
        layout = QVBoxLayout(self.network_page)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Giriş Alanları
        input_layout = QHBoxLayout()
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("Hedef IP / Subnet (Örn: 127.0.0.1 veya 192.168.1.1)")
        self.target_input.setStyleSheet("padding: 8px; font-size: 14px;")
        
        self.scan_btn = QPushButton("Taramayı Başlat")
        self.scan_btn.setStyleSheet("""
            QPushButton { background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 8px 15px; border-radius: 4px; }
            QPushButton:hover { background-color: #b4befe; }
        """)
        self.scan_btn.clicked.connect(self.run_network_scan)
        
        input_layout.addWidget(self.target_input)
        input_layout.addWidget(self.scan_btn)
        layout.addLayout(input_layout)
        
        # Sonuç Tablosu
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(["Hedef IP", "Port", "Servis", "Versiyon"])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.result_table)

    def run_network_scan(self):
        target = self.target_input.text().strip()
        if not target:
            QMessageBox.warning(self, "Uyarı", "Lütfen geçerli bir IP adresi girin!")
            return
            
        self.scan_btn.setText("Taranıyor...")
        self.scan_btn.setEnabled(False)
        QApplication.processEvents()
        
        success, results = self.scanner.scan_target(target)
        
        self.scan_btn.setText("Taramayı Başlat")
        self.scan_btn.setEnabled(True)
        
        if not success:
            QMessageBox.critical(self, "Hata", f"Tarama sırasında hata oluştu:\n{results}")
            return
            
        # Tabloyu Temizle ve Doldur
        self.result_table.setRowCount(0)
        row = 0
        for host in results:
            for proto in host['protocols']:
                self.result_table.insertRow(row)
                self.result_table.setItem(row, 0, QTableWidgetItem(host['host']))
                self.result_table.setItem(row, 1, QTableWidgetItem(str(proto['port'])))
                self.result_table.setItem(row, 2, QTableWidgetItem(proto['name']))
                self.result_table.setItem(row, 3, QTableWidgetItem(f"{proto['product']} {proto['version']}"))
                
                # Veritabanına kaydet
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO scan_results (test_type, target, details) VALUES (?, ?, ?)",
                        ("Network Scan", host['host'], f"Port {proto['port']}: {proto['name']} ({proto['product']})")
                    )
                    conn.commit()
                row += 1

        QMessageBox.information(self, "Başarılı", "Ağ taraması tamamlandı ve sonuçlar kaydedildi!")