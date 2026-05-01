"""
X-Ray/V2Ray Manager - Handles X-Ray core with various protocols
Supports: VMess, VLESS, Trojan, Shadowsocks, Reality, etc.
"""
import os
import subprocess
import time
import socket
import json
from pathlib import Path
from typing import Optional, Callable, Dict, Any


class XRayManager:
    def __init__(self, xray_path: str, config_dir: str):
        self.xray_path = Path(xray_path)
        self.config_dir = Path(config_dir)
        self.process: Optional[subprocess.Popen] = None
        self.socks_port = 10808
        self.http_port = 10809
        
    def is_xray_running(self) -> bool:
        """Check if X-Ray is already running"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', self.socks_port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def create_config(self, server_config: Dict[str, Any]) -> Path:
        """Create X-Ray configuration from server settings"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Build inbound (local SOCKS proxy)
        inbound = {
            "port": self.socks_port,
            "listen": "127.0.0.1",
            "protocol": "socks",
            "settings": {
                "auth": "noauth",
                "udp": True,
                "ip": "127.0.0.1"
            }
        }
        
        # Build outbound based on protocol type
        protocol = server_config.get("protocol", "vmess").lower()
        
        if protocol == "vmess":
            outbound = {
                "protocol": "vmess",
                "settings": {
                    "vnext": [{
                        "address": server_config["address"],
                        "port": server_config["port"],
                        "users": [{
                            "id": server_config["uuid"],
                            "alterId": server_config.get("alter_id", 0),
                            "security": server_config.get("security", "auto"),
                            "encryption": server_config.get("encryption", "none")
                        }]
                    }]
                },
                "streamSettings": self._build_stream_settings(server_config)
            }
        elif protocol == "vless":
            outbound = {
                "protocol": "vless",
                "settings": {
                    "vnext": [{
                        "address": server_config["address"],
                        "port": server_config["port"],
                        "users": [{
                            "id": server_config["uuid"],
                            "encryption": "none",
                            "flow": server_config.get("flow", "")
                        }]
                    }]
                },
                "streamSettings": self._build_stream_settings(server_config)
            }
        elif protocol == "trojan":
            outbound = {
                "protocol": "trojan",
                "settings": {
                    "servers": [{
                        "address": server_config["address"],
                        "port": server_config["port"],
                        "password": server_config["password"],
                        "flow": server_config.get("flow", "")
                    }]
                },
                "streamSettings": self._build_stream_settings(server_config)
            }
        elif protocol == "shadowsocks":
            outbound = {
                "protocol": "shadowsocks",
                "settings": {
                    "servers": [{
                        "address": server_config["address"],
                        "port": server_config["port"],
                        "method": server_config["method"],
                        "password": server_config["password"]
                    }]
                }
            }
        else:
            raise ValueError(f"Неподдерживаемый протокол: {protocol}")
        
        # Build complete config
        config = {
            "log": {
                "loglevel": "warning"
            },
            "inbounds": [inbound],
            "outbounds": [outbound],
            "routing": {
                "domainStrategy": "AsIs",
                "rules": []
            }
        }
        
        config_path = self.config_dir / "config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        return config_path
    
    def _build_stream_settings(self, server_config: Dict[str, Any]) -> Dict[str, Any]:
        """Build stream settings for various transports"""
        stream = {
            "network": server_config.get("network", "tcp"),
            "security": server_config.get("tls", "none")
        }
        
        # TLS settings
        if stream["security"] == "tls":
            stream["tlsSettings"] = {
                "serverName": server_config.get("sni", server_config["address"]),
                "allowInsecure": server_config.get("allow_insecure", False)
            }
        elif stream["security"] == "reality":
            stream["realitySettings"] = {
                "serverName": server_config.get("sni", ""),
                "fingerprint": server_config.get("fp", "chrome"),
                "publicKey": server_config.get("public_key", ""),
                "shortId": server_config.get("short_id", "")
            }
        
        # Network-specific settings
        network = stream["network"]
        if network == "ws":
            stream["wsSettings"] = {
                "path": server_config.get("path", "/"),
                "headers": {
                    "Host": server_config.get("host", "")
                }
            }
        elif network == "grpc":
            stream["grpcSettings"] = {
                "serviceName": server_config.get("service_name", "")
            }
        elif network == "h2":
            stream["h2Settings"] = {
                "path": server_config.get("path", "/"),
                "host": server_config.get("host", [])
            }
        elif network == "kcp":
            stream["kcpSettings"] = {
                "header": {
                    "type": server_config.get("header_type", "none")
                }
            }
        
        return stream
    
    def start(self, server_config: Dict[str, Any], status_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Start X-Ray with given server configuration"""
        if self.is_xray_running():
            if status_callback:
                status_callback("X-Ray уже запущен")
            return True
        
        if not self.xray_path.exists():
            if status_callback:
                status_callback(f"X-Ray исполняемый файл не найден: {self.xray_path}")
            return False
        
        try:
            # Create configuration
            config_path = self.create_config(server_config)
            
            if status_callback:
                status_callback(f"Запуск X-Ray ({server_config.get('protocol', 'unknown')})...")
            
            cmd = [
                str(self.xray_path),
                "-c", str(config_path)
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(self.xray_path.parent)
            )
            
            # Wait for X-Ray to start
            time.sleep(2)
            
            if self.is_xray_running():
                if status_callback:
                    status_callback(f"X-Ray запущен на порту {self.socks_port}")
                return True
            else:
                if status_callback:
                    status_callback("Не удалось запустить X-Ray")
                return False
                
        except Exception as e:
            if status_callback:
                status_callback(f"Ошибка запуска X-Ray: {str(e)}")
            return False
    
    def stop(self, status_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Stop X-Ray service"""
        if self.process:
            try:
                if status_callback:
                    status_callback("Остановка X-Ray...")
                self.process.terminate()
                self.process.wait(timeout=5)
                self.process = None
                if status_callback:
                    status_callback("X-Ray остановлен")
                return True
            except Exception as e:
                if status_callback:
                    status_callback(f"Ошибка остановки X-Ray: {str(e)}")
                return False
        return False
    
    def get_socks_proxy(self) -> str:
        """Get SOCKS proxy string"""
        return f"socks5://127.0.0.1:{self.socks_port}"
    
    def get_http_proxy(self) -> str:
        """Get HTTP proxy string"""
        return f"http://127.0.0.1:{self.http_port}"
