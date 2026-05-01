"""
Configuration Manager - Handles saving and loading server configurations
"""
import json
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional


class ConfigManager:
    def __init__(self, config_dir: str):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.servers_file = self.config_dir / "servers.json"
        self.settings_file = self.config_dir / "settings.yaml"
        
    def load_servers(self) -> List[Dict[str, Any]]:
        """Load saved server configurations"""
        if not self.servers_file.exists():
            return []
        
        try:
            with open(self.servers_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    
    def save_servers(self, servers: List[Dict[str, Any]]) -> bool:
        """Save server configurations"""
        try:
            with open(self.servers_file, 'w', encoding='utf-8') as f:
                json.dump(servers, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False
    
    def add_server(self, server: Dict[str, Any]) -> bool:
        """Add a new server configuration"""
        servers = self.load_servers()
        servers.append(server)
        return self.save_servers(servers)
    
    def remove_server(self, index: int) -> bool:
        """Remove a server by index"""
        servers = self.load_servers()
        if 0 <= index < len(servers):
            servers.pop(index)
            return self.save_servers(servers)
        return False
    
    def update_server(self, index: int, server: Dict[str, Any]) -> bool:
        """Update a server configuration by index"""
        servers = self.load_servers()
        if 0 <= index < len(servers):
            servers[index] = server
            return self.save_servers(servers)
        return False
    
    def load_settings(self) -> Dict[str, Any]:
        """Load application settings"""
        if not self.settings_file.exists():
            return self._default_settings()
        
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings = yaml.safe_load(f)
                return settings if settings else self._default_settings()
        except Exception:
            return self._default_settings()
    
    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """Save application settings"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                yaml.dump(settings, f, default_flow_style=False, allow_unicode=True)
            return True
        except Exception:
            return False
    
    def _default_settings(self) -> Dict[str, Any]:
        """Return default application settings"""
        return {
            "tor_path": "",
            "xray_path": "",
            "auto_start": False,
            "start_on_boot": False,
            "minimize_to_tray": True,
            "check_updates": True,
            "language": "ru",
            "theme": "dark",
            "default_proxy_mode": "socks5",
            "system_proxy": False,
            "log_level": "info"
        }
    
    def import_from_clipboard(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse server configuration from clipboard text (supports various formats)"""
        text = text.strip()
        
        # Try VMess/VLESS link format
        if text.startswith('vmess://'):
            return self._parse_vmess_link(text)
        elif text.startswith('vless://'):
            return self._parse_vless_link(text)
        elif text.startswith('trojan://'):
            return self._parse_trojan_link(text)
        elif text.startswith('ss://'):
            return self._parse_shadowsocks_link(text)
        
        # Try JSON format
        if text.startswith('{'):
            try:
                return json.loads(text)
            except Exception:
                pass
        
        return None
    
    def _parse_vmess_link(self, link: str) -> Optional[Dict[str, Any]]:
        """Parse VMess link"""
        try:
            import base64
            # Remove prefix
            encoded = link[8:]
            # Add padding if needed
            padding = '=' * (4 - len(encoded) % 4) if len(encoded) % 4 else ''
            decoded = base64.b64decode(encoded + padding).decode('utf-8')
            data = json.loads(decoded)
            
            return {
                "protocol": "vmess",
                "name": data.get("ps", "VMess Server"),
                "address": data.get("add", ""),
                "port": int(data.get("port", 443)),
                "uuid": data.get("id", ""),
                "alter_id": int(data.get("aid", 0)),
                "security": data.get("scy", "auto"),
                "network": data.get("net", "tcp"),
                "tls": "tls" if data.get("tls") == "tls" else "none",
                "sni": data.get("host", "") or data.get("sni", ""),
                "path": data.get("path", "/"),
                "host": data.get("host", "")
            }
        except Exception:
            return None
    
    def _parse_vless_link(self, link: str) -> Optional[Dict[str, Any]]:
        """Parse VLESS link"""
        try:
            from urllib.parse import urlparse, parse_qs
            
            parsed = urlparse(link)
            query = parse_qs(parsed.query)
            
            return {
                "protocol": "vless",
                "name": parsed.fragment or "VLESS Server",
                "address": parsed.hostname or "",
                "port": parsed.port or 443,
                "uuid": parsed.username or "",
                "encryption": "none",
                "flow": query.get("flow", [""])[0],
                "security": query.get("security", ["none"])[0],
                "network": query.get("type", ["tcp"])[0],
                "sni": query.get("sni", [parsed.hostname])[0],
                "fp": query.get("fp", ["chrome"])[0],
                "pbk": query.get("pbk", [""])[0],
                "sid": query.get("sid", [""])[0],
                "path": query.get("path", ["/"])[0],
                "host": query.get("host", [""])[0]
            }
        except Exception:
            return None
    
    def _parse_trojan_link(self, link: str) -> Optional[Dict[str, Any]]:
        """Parse Trojan link"""
        try:
            from urllib.parse import urlparse, parse_qs
            
            parsed = urlparse(link)
            query = parse_qs(parsed.query)
            
            return {
                "protocol": "trojan",
                "name": parsed.fragment or "Trojan Server",
                "address": parsed.hostname or "",
                "port": parsed.port or 443,
                "password": parsed.username or "",
                "security": query.get("security", ["tls"])[0],
                "sni": query.get("sni", [parsed.hostname])[0],
                "network": query.get("type", ["tcp"])[0],
                "path": query.get("path", ["/"])[0],
                "host": query.get("host", [""])[0]
            }
        except Exception:
            return None
    
    def _parse_shadowsocks_link(self, link: str) -> Optional[Dict[str, Any]]:
        """Parse Shadowsocks link"""
        try:
            import base64
            from urllib.parse import urlparse
            
            parsed = urlparse(link)
            
            # Decode user info
            user_info = parsed.username
            if '@' in user_info:
                # New format: method:password@hostname:port
                method_password = base64.b64decode(user_info.split('@')[0] + '==').decode('utf-8')
                method, password = method_password.split(':', 1)
            else:
                # Old format: base64(method:password)@hostname:port
                method_password = base64.b64decode(user_info + '==').decode('utf-8')
                method, password = method_password.split(':', 1)
            
            return {
                "protocol": "shadowsocks",
                "name": parsed.fragment or "Shadowsocks Server",
                "address": parsed.hostname or "",
                "port": parsed.port or 8388,
                "method": method,
                "password": password
            }
        except Exception:
            return None
