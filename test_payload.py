# --- TEST ZARARLI SCRIPT SIMULASYONU ---
import socket
import subprocess
import os

def fake_reverse_shell():
    # 1. Ağ Soketi Açma (Potential Reverse Shell)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # 2. Sistem Komutu Çalıştırma
    subprocess.Popen(["cmd.exe", "/c", "echo Test Attack"])
    
    # 3. Dinamik Kod Çalıştırma Riskli Fonksiyon
    code_input = "print('Hacked!')"
    eval(code_input)

if __name__ == "__main__":
    fake_reverse_shell()