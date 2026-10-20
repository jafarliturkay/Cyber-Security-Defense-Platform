# 🛡️ Ağ Güvenliği & Savunma Platformu

<p align="center">
  <b>Python, PyQt6, Nmap ve SQLite ile Geliştirilmiş Kapsamlı Siber Güvenlik ve Savunma Ekosistemi</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/PyQt6-GUI-green?style=for-the-badge&logo=qt&logoColor=white" />
  <img src="https://img.shields.io/badge/Nmap-Network%20Scanner-orange?style=for-the-badge&logo=security&logoColor=white" />
  <img src="https://img.shields.io/badge/SQLite-Database-lightgrey?style=for-the-badge&logo=sqlite&logoColor=white" />
</p>

---

## 📋 Proje Hakkında
**Ağ Güvenliği & Savunma Platformu**, yerel ağları taramak, web sunucu zafiyetlerini analiz etmek, dosya ve disklerde zararlı yazılım imzalarını aramak, e-posta veri sızıntılarını (OSINT) sorgulamak ve Wi-Fi MITM tehditlerini engellemek için geliştirilmiş hepsi bir arada masaüstü güvenlik aracıdır. Modern koyu tema arayüzü, animasyonlu giriş ekranı ve güçlü arka plan iş parçacıkları (QThread) ile donatılmıştır.

---

## 🚀 Modüller ve Özellikler

| Modül Adı | Açıklama ve Teknik Detaylar |
| :--- | :--- |
| **🌐 Ağ Taraması & Güvenlik** | Nmap entegrasyonu ile hedef IP üzerinde hızlı port taraması yapar, açık portları ve riskli servisleri tespit eder. Sonuçları anlık olarak pasta grafikle (Matplotlib) görselleştirir ve `scan_logs` veritabanına kaydeder. Raporlar HTML formatında dışa aktarılabilir. |
| **🌍 Web / Sunucu Tarayıcı** | Hedef web sitelerinin DNS çözümlemesini yapar, açık web portlarını (80, 443, 8080 vb.) tarar ve kritik HTTP güvenlik başlıklarını (`HSTS`, `CSP`, `X-Frame-Options`) denetler. |
| **🤖 AI Dosya & Disk Taraması** | Yerel disk veya klasörlerde statik kod analizi gerçekleştirir. `import socket`, `subprocess`, `powershell -enc` veya `base64` gibi şüpheli zararlı yazılım / backdoor kalıplarını satır satır yakalar. |
| **🔍 E-Posta Veri Sızıntısı** | `XposedOrNot` API entegrasyonuyla e-posta adreslerinin geçmiş sızıntılarını sorgular. API'den tarih gelmeyen kayıtlar için **akıllı tarih fallback sözlüğü (`KNOWN_BREACH_YEARS`)** kullanarak tahmini/bilinen sızıntı yıllarını gösterir ve yapay zeka analiz kutusuyla risk açıklaması sunar. |
| **🛡️ Wi-Fi & MITM Kalkanı** | ARP tablosunu analiz ederek aynı MAC adresine sahip birden fazla IP çakışmasını ve ağ geçidi (Gateway) güvenliğini denetler, Man-in-the-Middle (ARP Spoofing) saldırılarını anında raporlar. |
| **👑 Admin Paneli & Denetim** | Sistemdeki kayıtlı kullanıcıları ve çevrimiçi durumlarını canlı takip eder. Adminler şüpheli gördükleri kullanıcıların oturumunu **zorla sonlandırabilir** (`is_online = 0`) veya kullanıcı silebilir. Tüm işlemler `audit_logs` tablosunda kayıt altına alınır. |

---

## 🛠️ Kullanılan Teknolojiler ve Kütüphaneler

- **Dil:** Python 3.10+
- **Arayüz (GUI):** PyQt6 (Özel animasyonlu arayüz bileşenleri, QStackedWidget, QTableWidget)
- **Ağ & Tarama:** `python-nmap`, Sockets, Subprocess (ARP analizi)
- **Veritabanı:** SQLite3 (Güvenli şifre hashleme, denetim logları, tarama geçmişi)
- **Grafik & Görselleştirme:** Matplotlib (Port dağılım grafikleri)
- **Paketleme:** PyInstaller (`.exe` dönüştürücü ve otomatik `.ico` kalkan logo üreticisi)

---

## 💻 Kurulum ve Çalıştırma

Bilgisayarınızda projenin kaynak kodlarını çalıştırmak için şu adımları izleyebilirsiniz:

1. **Depoyu klonlayın:**
   ```bash
   git clone [https://github.com/jafarliturkay/Cyber-Security-Defense-Platform.git](https://github.com/jafarliturkay/Cyber-Security-Defense-Platform.git)
   cd Cyber-Security-Defense-Platform
   Gerekli kütüphaneleri yükleyin:

Bash
pip install PyQt6 matplotlib python-nmap
Uygulamayı başlatın:

Bash
python main.py
(Not: Ağ tarama özelliklerinin tam çalışabilmesi için sisteminizde Nmap kurulu olmalıdır).

📦 Tek Tıkla Çalıştırılabilir (.EXE) Sürümü Oluşturma
Python veya ek kütüphaneler kurmadan doğrudan masaüstünde çalıştırmak isterseniz PyInstaller ile paketleyebilirsiniz:

Bash
pyinstaller --noconsole --onefile --icon=app_icon.ico main.py