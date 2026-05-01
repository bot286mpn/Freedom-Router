"""
Dependency Manager - Handles automatic download and updates of Tor and X-Ray cores
Includes version checking, automatic downloads, and manual installation fallback
"""
import os
import json
import hashlib
import shutil
import zipfile
import tarfile
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Callable, Tuple
import threading
import requests
from packaging import version


class DependencyManager:
    """Manages downloading and updating Tor and X-Ray dependencies"""
    
    # Download URLs (official sources)
    TOR_DOWNLOAD_URL = "https://www.torproject.org/dist/torbrowser/"
    TOR_VERSION_URL = "https://aus1.torproject.org/tpb/packages/TorBrowser/"
    
    XRAY_GITHUB_API = "https://api.github.com/repos/XTLS/Xray-core/releases/latest"
    XRAY_DOWNLOAD_BASE = "https://github.com/XTLS/Xray-core/releases/download/"
    
    # Known checksums for verification (will be updated dynamically)
    TOR_CHECKSUMS_URL = "https://www.torproject.org/dist/torbrowser/latest-sha256sums.asc"
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.bin_dir = self.base_dir / "bin"
        self.cache_dir = self.base_dir / ".cache"
        
        # Create directories
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Local state file
        self.state_file = self.bin_dir / "dependencies.json"
        self.dependencies_state = self._load_state()
        
        # Status callback
        self.status_callback: Optional[Callable[[str], None]] = None
        
    def _load_state(self) -> Dict[str, Any]:
        """Load dependencies state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "tor": {"installed": False, "version": None, "path": None},
            "xray": {"installed": False, "version": None, "path": None}
        }
    
    def _save_state(self):
        """Save dependencies state to file"""
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.dependencies_state, f, indent=2)
    
    def _log(self, message: str):
        """Log message via callback"""
        if self.status_callback:
            self.status_callback(message)
    
    def set_status_callback(self, callback: Callable[[str], None]):
        """Set status callback function"""
        self.status_callback = callback
    
    def check_tor_installed(self) -> Tuple[bool, Optional[str]]:
        """Check if Tor is installed and return version"""
        tor_exe = self.bin_dir / "Tor" / "tor.exe"
        alt_tor_exe = self.bin_dir / "tor.exe"
        
        if tor_exe.exists():
            self.dependencies_state["tor"]["installed"] = True
            self.dependencies_state["tor"]["path"] = str(tor_exe)
            self._save_state()
            return True, self.dependencies_state["tor"].get("version")
        
        if alt_tor_exe.exists():
            self.dependencies_state["tor"]["installed"] = True
            self.dependencies_state["tor"]["path"] = str(alt_tor_exe)
            self._save_state()
            return True, self.dependencies_state["tor"].get("version")
        
        # Check if path is manually configured
        if self.dependencies_state["tor"].get("installed"):
            path = self.dependencies_state["tor"].get("path")
            if path and Path(path).exists():
                return True, self.dependencies_state["tor"].get("version")
        
        return False, None
    
    def check_xray_installed(self) -> Tuple[bool, Optional[str]]:
        """Check if X-Ray is installed and return version"""
        xray_exe = self.bin_dir / "Xray" / "xray.exe"
        alt_xray_exe = self.bin_dir / "xray.exe"
        
        if xray_exe.exists():
            self.dependencies_state["xray"]["installed"] = True
            self.dependencies_state["xray"]["path"] = str(xray_exe)
            self._save_state()
            return True, self.dependencies_state["xray"].get("version")
        
        if alt_xray_exe.exists():
            self.dependencies_state["xray"]["installed"] = True
            self.dependencies_state["xray"]["path"] = str(alt_xray_exe)
            self._save_state()
            return True, self.dependencies_state["xray"].get("version")
        
        # Check if path is manually configured
        if self.dependencies_state["xray"].get("installed"):
            path = self.dependencies_state["xray"].get("path")
            if path and Path(path).exists():
                return True, self.dependencies_state["xray"].get("version")
        
        return False, None
    
    def get_latest_tor_version(self) -> Optional[str]:
        """Get latest Tor version from official source"""
        try:
            self._log("Проверка последней версии Tor...")
            response = requests.get(self.TOR_VERSION_URL, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Extract version from JSON structure
                versions = list(data.keys())
                if versions:
                    latest = sorted(versions, key=lambda v: version.parse(v))[-1]
                    return latest
        except Exception as e:
            self._log(f"Не удалось получить версию Tor: {e}")
        return None
    
    def get_latest_xray_version(self) -> Optional[str]:
        """Get latest X-Ray version from GitHub"""
        try:
            self._log("Проверка последней версии X-Ray...")
            response = requests.get(self.XRAY_GITHUB_API, timeout=10)
            if response.status_code == 200:
                data = response.json()
                tag_name = data.get("tag_name", "")
                if tag_name.startswith("v"):
                    return tag_name[1:]  # Remove 'v' prefix
                return tag_name
        except Exception as e:
            self._log(f"Не удалось получить версию X-Ray: {e}")
        return None
    
    def needs_update(self, component: str) -> bool:
        """Check if component needs update"""
        if component == "tor":
            installed, current_version = self.check_tor_installed()
            if not installed:
                return True
            latest = self.get_latest_tor_version()
            if latest and current_version:
                return version.parse(latest) > version.parse(current_version)
            return not current_version
        elif component == "xray":
            installed, current_version = self.check_xray_installed()
            if not installed:
                return True
            latest = self.get_latest_xray_version()
            if latest and current_version:
                return version.parse(latest) > version.parse(current_version)
            return not current_version
        return False
    
    def download_tor(self, version_str: Optional[str] = None) -> bool:
        """Download and install Tor Expert Bundle"""
        try:
            if not version_str:
                version_str = self.get_latest_tor_version()
                if not version_str:
                    self._log("Не удалось определить последнюю версию Tor")
                    return False
            
            self._log(f"Загрузка Tor версии {version_str}...")
            
            # Windows 64-bit Expert Bundle URL
            filename = f"tor expert bundle {version_str}.zip"
            url = f"{self.TOR_DOWNLOAD_URL}{version_str}/{filename}"
            
            # Alternative URL format
            alt_url = f"https://www.torproject.org/dist/torbrowser/{version_str}/tor-expert-bundle-windows-x86_64-{version_str}.zip"
            
            download_success = self._download_file(url, filename) or self._download_file(alt_url, filename)
            
            if not download_success:
                self._log("Автоматическая загрузка Tor не удалась из-за блокировки или недоступности")
                return False
            
            # Extract
            self._log("Распаковка Tor...")
            extract_dir = self.bin_dir / "Tor"
            extract_dir.mkdir(exist_ok=True)
            
            zip_path = self.cache_dir / filename
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # Extract to temp directory first
                    temp_extract = self.cache_dir / "tor_extract"
                    temp_extract.mkdir(exist_ok=True)
                    zip_ref.extractall(temp_extract)
                    
                    # Find tor.exe and move to bin/Tor
                    for root, dirs, files in os.walk(temp_extract):
                        for file in files:
                            if file.lower() == "tor.exe":
                                src = Path(root) / file
                                dst = extract_dir / "tor.exe"
                                shutil.copy2(src, dst)
                                break
                    
                    # Cleanup
                    shutil.rmtree(temp_extract, ignore_errors=True)
                
                # Remove zip
                zip_path.unlink(missing_ok=True)
                
                # Update state
                tor_exe = extract_dir / "tor.exe"
                if tor_exe.exists():
                    self.dependencies_state["tor"]["installed"] = True
                    self.dependencies_state["tor"]["version"] = version_str
                    self.dependencies_state["tor"]["path"] = str(tor_exe)
                    self._save_state()
                    self._log(f"Tor {version_str} успешно установлен")
                    return True
                else:
                    self._log("Файл tor.exe не найден после распаковки")
                    return False
                    
            except Exception as e:
                self._log(f"Ошибка распаковки Tor: {e}")
                return False
                
        except Exception as e:
            self._log(f"Ошибка установки Tor: {e}")
            return False
    
    def download_xray(self, version_str: Optional[str] = None) -> bool:
        """Download and install X-Ray core"""
        try:
            if not version_str:
                version_str = self.get_latest_xray_version()
                if not version_str:
                    self._log("Не удалось определить последнюю версию X-Ray")
                    return False
            
            self._log(f"Загрузка X-Ray версии {version_str}...")
            
            # Windows 64-bit
            filename = f"Xray-windows-64.zip"
            url = f"{self.XRAY_DOWNLOAD_BASE}v{version_str}/{filename}"
            
            if not self._download_file(url, filename):
                self._log("Автоматическая загрузка X-Ray не удалась из-за блокировки или недоступности")
                return False
            
            # Extract
            self._log("Распаковка X-Ray...")
            extract_dir = self.bin_dir / "Xray"
            extract_dir.mkdir(exist_ok=True)
            
            zip_path = self.cache_dir / filename
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                # Remove zip
                zip_path.unlink(missing_ok=True)
                
                # Update state
                xray_exe = extract_dir / "xray.exe"
                if xray_exe.exists():
                    self.dependencies_state["xray"]["installed"] = True
                    self.dependencies_state["xray"]["version"] = version_str
                    self.dependencies_state["xray"]["path"] = str(xray_exe)
                    self._save_state()
                    self._log(f"X-Ray {version_str} успешно установлен")
                    return True
                else:
                    self._log("Файл xray.exe не найден после распаковки")
                    return False
                    
            except Exception as e:
                self._log(f"Ошибка распаковки X-Ray: {e}")
                return False
                
        except Exception as e:
            self._log(f"Ошибка установки X-Ray: {e}")
            return False
    
    def _download_file(self, url: str, filename: str) -> bool:
        """Download file with progress tracking"""
        try:
            self._log(f"Скачивание из: {url[:80]}...")
            
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            file_path = self.cache_dir / filename
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            self._log(f"Прогресс загрузки: {progress:.1f}%")
            
            # Verify file was downloaded
            if file_path.exists() and file_path.stat().st_size > 0:
                self._log(f"Загрузка завершена: {filename}")
                return True
            else:
                return False
                
        except requests.exceptions.RequestException as e:
            self._log(f"Ошибка сети при загрузке: {e}")
            return False
        except Exception as e:
            self._log(f"Ошибка загрузки: {e}")
            return False
    
    def get_installation_instructions(self, component: str) -> str:
        """Get manual installation instructions for a component"""
        if component == "tor":
            return """
🧅 Ручная установка Tor Expert Bundle:

1. Перейдите на официальный сайт: https://www.torproject.org/download/
2. Найдите "Tor Expert Bundle" для Windows
3. Скачайте ZIP архив
4. Распакуйте в папку: {bin_dir}\\Tor\\
5. Убедитесь, что файл tor.exe находится в: {bin_dir}\\Tor\\tor.exe
6. Перезапустите приложение

Или укажите путь к tor.exe в настройках приложения.
            """.format(bin_dir=self.bin_dir)
        elif component == "xray":
            return """
⚡ Ручная установка X-Ray Core:

1. Перейдите на GitHub: https://github.com/XTLS/Xray-core/releases
2. Скачайте последнюю версию для Windows (Xray-windows-64.zip)
3. Распакуйте в папку: {bin_dir}\\Xray\\
4. Убедитесь, что файл xray.exe находится в: {bin_dir}\\Xray\\xray.exe
5. Перезапустите приложение

Или укажите путь к xray.exe в настройках приложения.
            """.format(bin_dir=self.bin_dir)
        return ""
    
    def check_all_dependencies(self) -> Dict[str, Dict[str, Any]]:
        """Check status of all dependencies"""
        tor_installed, tor_version = self.check_tor_installed()
        xray_installed, xray_version = self.check_xray_installed()
        
        return {
            "tor": {
                "installed": tor_installed,
                "version": tor_version,
                "needs_update": self.needs_update("tor") if tor_installed else True,
                "path": self.dependencies_state["tor"].get("path")
            },
            "xray": {
                "installed": xray_installed,
                "version": xray_version,
                "needs_update": self.needs_update("xray") if xray_installed else True,
                "path": self.dependencies_state["xray"].get("path")
            }
        }
    
    def install_or_update_all(self, callback: Optional[Callable[[str], None]] = None) -> Dict[str, bool]:
        """Install or update all missing/outdated dependencies"""
        results = {"tor": False, "xray": False}
        
        if callback:
            self.set_status_callback(callback)
        
        status = self.check_all_dependencies()
        
        # Install/update Tor
        if not status["tor"]["installed"] or status["tor"]["needs_update"]:
            self._log("Установка/обновление Tor...")
            results["tor"] = self.download_tor()
        else:
            self._log("Tor уже установлен и актуален")
            results["tor"] = True
        
        # Install/update X-Ray
        if not status["xray"]["installed"] or status["xray"]["needs_update"]:
            self._log("Установка/обновление X-Ray...")
            results["xray"] = self.download_xray()
        else:
            self._log("X-Ray уже установлен и актуален")
            results["xray"] = True
        
        return results
