"""
Proxy Manager - Manages system proxy settings and application-specific proxying
"""
import os
import sys
import subprocess
from typing import Optional, List, Dict, Any
from pathlib import Path


class ProxyManager:
    def __init__(self):
        self.is_windows = sys.platform == 'win32'
        
    def set_system_proxy(self, proxy_url: str, enable: bool = True) -> bool:
        """Set system-wide proxy settings (Windows)"""
        if not self.is_windows:
            print("Системный прокси поддерживается только на Windows")
            return False
        
        try:
            import winreg
            
            if enable:
                # Parse proxy URL
                if '://' in proxy_url:
                    proxy_url = proxy_url.split('://')[1]
                
                # Set proxy in Windows registry
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                    0,
                    winreg.KEY_SET_VALUE
                ) as key:
                    winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
                    winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy_url)
            else:
                # Disable proxy
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                    0,
                    winreg.KEY_SET_VALUE
                ) as key:
                    winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            
            # Notify Windows of change
            self._notify_internet_settings_changed()
            return True
            
        except ImportError:
            print("Модуль winreg доступен только на Windows")
            return False
        except Exception as e:
            print(f"Ошибка настройки системного прокси: {e}")
            return False
    
    def _notify_internet_settings_changed(self):
        """Notify Windows of internet settings change"""
        if not self.is_windows:
            return
        try:
            ctypes = __import__('ctypes')
            ctypes.windll.wininet.InternetSetOptionW(
                None, 
                39,  # INTERNET_OPTION_SETTINGS_CHANGED
                None, 
                0
            )
            ctypes.windll.wininet.InternetSetOptionW(
                None,
                37,  # INTERNET_OPTION_REFRESH
                None,
                0
            )
        except Exception:
            pass
    
    def set_environment_proxy(self, proxy_url: str):
        """Set proxy environment variables"""
        os.environ['HTTP_PROXY'] = proxy_url
        os.environ['HTTPS_PROXY'] = proxy_url
        os.environ['SOCKS_PROXY'] = proxy_url
        # Also set lowercase versions
        os.environ['http_proxy'] = proxy_url
        os.environ['https_proxy'] = proxy_url
        os.environ['socks_proxy'] = proxy_url
    
    def clear_environment_proxy(self):
        """Clear proxy environment variables"""
        for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'SOCKS_PROXY', 'http_proxy', 'https_proxy', 'socks_proxy']:
            if var in os.environ:
                del os.environ[var]
    
    def get_app_launch_command(self, app_path: str, proxy_url: str) -> List[str]:
        """Get command to launch application with proxy"""
        # Parse proxy
        proxy_host_port = proxy_url
        if '://' in proxy_host_port:
            proxy_host_port = proxy_host_port.split('://')[1]
        
        # Some applications support --proxy flag
        common_apps = {
            'firefox.exe': ['--proxy'],
            'chrome.exe': ['--proxy-server='],
            'curl.exe': ['--proxy'],
            'wget.exe': ['--proxy='],
        }
        
        app_name = Path(app_path).name.lower()
        if app_name in common_apps:
            flags = common_apps[app_name]
            if '=' in flags[0]:
                return [app_path, f"{flags[0]}{proxy_host_port}"]
            else:
                return [app_path, flags[0], proxy_host_port]
        
        # Default: just return the app path (user should configure proxy in app settings)
        return [app_path]
    
    def launch_app_with_proxy(self, app_path: str, proxy_url: str) -> Optional[subprocess.Popen]:
        """Launch application with proxy settings"""
        try:
            env = os.environ.copy()
            env['HTTP_PROXY'] = proxy_url
            env['HTTPS_PROXY'] = proxy_url
            env['SOCKS_PROXY'] = proxy_url
            env['http_proxy'] = proxy_url
            env['https_proxy'] = proxy_url
            env['socks_proxy'] = proxy_url
            
            cmd = self.get_app_launch_command(app_path, proxy_url)
            return subprocess.Popen(cmd, env=env)
        except Exception as e:
            print(f"Ошибка запуска приложения с прокси: {e}")
            return None
    
    def test_proxy_connection(self, proxy_url: str, test_url: str = "https://www.google.com", timeout: int = 10) -> bool:
        """Test if proxy connection works"""
        try:
            import requests
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            response = requests.get(test_url, proxies=proxies, timeout=timeout)
            return response.status_code == 200
        except Exception:
            return False
