import sqlite3
import os

class DatabaseManager:
    def __init__(self, db_path="cybersec_platform.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Kullanıcılar Tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tarama ve Test Sonuçları Tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scan_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_type TEXT NOT NULL,
                    target TEXT NOT NULL,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Zafiyet / Risk Tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vulnerabilities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id INTEGER,
                    severity TEXT CHECK(severity IN ('Düşük', 'Orta', 'Yüksek', 'Kritik')),
                    title TEXT NOT NULL,
                    description TEXT,
                    recommendation TEXT,
                    FOREIGN KEY(scan_id) REFERENCES scan_results(id)
                )
            ''')
            
            # Varsayılan admin kullanıcısı oluştur (İlk giriş için)
            cursor.execute('''
                INSERT OR IGNORE INTO users (id, username, password) 
                VALUES (1, 'admin', 'admin123')
            ''')
            
            conn.commit()

if __name__ == "__main__":
    db = DatabaseManager()
    print("Veritabanı ve tablolar başarıyla oluşturuldu!")