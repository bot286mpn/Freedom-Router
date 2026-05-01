"""
SecureProxy - Универсальный прокси клиент для Windows

Приложение поддерживает:
- Tor Expert Bundle
- X-Ray/V2Ray с протоколами: VMess, VLESS, Trojan, Shadowsocks, Reality
- Локальный SOCKS5 прокси
- Системный прокси
- Проксирование отдельных приложений

Установка:
1. Установите Python 3.8+
2. Установите зависимости: pip install -r requirements.txt
3. Скачайте Tor Expert Bundle и X-Ray core
4. Укажите пути к ним в настройках приложения
5. Запустите: python main.py

Запуск:
    python main.py

Сборка в EXE (опционально):
    pyinstaller --onefile --windowed --name SecureProxy main.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import main

if __name__ == "__main__":
    main()
