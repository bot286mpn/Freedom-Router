"""
Tor Manager - Handles Tor Expert Bundle integration
"""
import os
import subprocess
import time
import socket
from pathlib import Path
from typing import Optional, Callable


class TorManager:
    def __init__(self, tor_path: str, data_dir: str):
        self.tor_path = Path(tor_path)
        self.data_dir = Path(data_dir)
        self.process: Optional[subprocess.Popen] = None
        self.socks_port = 9150
        self.control_port = 9151
        
    def is_tor_running(self) -> bool:
        """Check if Tor is already running on the expected port"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', self.socks_port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def start(self, status_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Start Tor service"""
        if self.is_tor_running():
            if status_callback:
                status_callback("Tor уже запущен")
            return True
        
        if not self.tor_path.exists():
            if status_callback:
                status_callback(f"Tor исполняемый файл не найден: {self.tor_path}")
            return False
        
        # Create data directory if it doesn't exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create torrc configuration
        torrc_content = f"""
SocksPort {self.socks_port}
ControlPort {self.control_port}
DataDirectory {self.data_dir}
Log notice stdout
"""
        torrc_path = self.data_dir / "torrc"
        torrc_path.write_text(torrc_content)
        
        try:
            cmd = [
                str(self.tor_path),
                "-f", str(torrc_path)
            ]
            
            if status_callback:
                status_callback("Запуск Tor...")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.tor_path.parent)
            )
            
            # Wait for Tor to start
            time.sleep(3)
            
            if self.is_tor_running():
                if status_callback:
                    status_callback(f"Tor запущен на порту {self.socks_port}")
                return True
            else:
                if status_callback:
                    status_callback("Не удалось запустить Tor")
                return False
                
        except Exception as e:
            if status_callback:
                status_callback(f"Ошибка запуска Tor: {str(e)}")
            return False
    
    def stop(self, status_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Stop Tor service"""
        if self.process:
            try:
                if status_callback:
                    status_callback("Остановка Tor...")
                self.process.terminate()
                self.process.wait(timeout=5)
                self.process = None
                if status_callback:
                    status_callback("Tor остановлен")
                return True
            except Exception as e:
                if status_callback:
                    status_callback(f"Ошибка остановки Tor: {str(e)}")
                return False
        elif self.is_tor_running():
            # Try to find and kill the process
            try:
                import psutil
                for proc in psutil.process_iter(['pid', 'name']):
                    if 'tor' in proc.info['name'].lower():
                        proc.terminate()
                if status_callback:
                    status_callback("Tor остановлен")
                return True
            except Exception:
                pass
        return False
    
    def get_socks_proxy(self) -> str:
        """Get SOCKS proxy string"""
        return f"socks5://127.0.0.1:{self.socks_port}"
