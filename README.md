# 🛡️ Ağ Güvenliği & Savunma Platformu

Python, PyQt6, Nmap ve SQLite kullanılarak geliştirilmiş kapsamlı masaüstü siber güvenlik, ağ tarama ve zafiyet analiz platformudur.

## 🚀 Özellikler
* **🌐 Ağ Güvenliği & Port Taraması:** Hedef IP adresleri üzerinde Nmap entegrasyonu ile hızlı port taraması ve şüpheli servis tespiti.
* **🌍 Web Sunucu & Header Analizi:** Web sitelerinin açık portlarını ve kritik HTTP güvenlik başlıklarını (HSTS, CSP vb.) denetleme.
* **🤖 AI Statik Dosya & Disk Taraması:** Bilgisayar veya klasörler üzerinde zararlı yazılım kalıplarını ve backdoor imzalarını tarama.
* **🔍 E-Posta OSINT & Veri Sızıntısı:** XposedOrNot API entegrasyonu ve akıllı tarih fallback mekanizması ile e-posta ihlal sorgulaması.
* **🛡️ Wi-Fi & MITM Kalkanı:** ARP tablosu analizi ile Man-in-the-Middle (MITM) saldırı tespiti.
* **👑 Admin Paneli & Oturum Yönetimi:** Canlı kullanıcı takibi, denetim günlükleri (Audit Logs) ve şüpheli kullanıcıların oturumunu zorla sonlandırma.

## 💻 Kurulum ve Çalıştırma

1. Projeyi klonlayın:
   ```bash
   git clone [https://github.com/KULLANICI_ADIN/Cyber-Security-Defense-Platform.git](https://github.com/KULLANICI_ADIN/Cyber-Security-Defense-Platform.git)
2. Gerekli kütüphaneleri yükleyin:
   pip install PyQt6 matplotlib python-nmap
3. Uygulamayı başlatın:
   python main.py