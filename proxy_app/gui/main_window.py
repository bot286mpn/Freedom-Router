"""
Main Application GUI - Modern interface using CustomTkinter
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import pyperclip
from typing import Optional, Dict, Any

from core.tor_manager import TorManager
from core.xray_manager import XRayManager
from core.proxy_manager import ProxyManager
from core.config_manager import ConfigManager
from core.dependency_manager import DependencyManager


class ProxyApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configuration
        self.title("SecureProxy - Универсальный прокси клиент")
        self.geometry("900x700")
        self.minsize(800, 600)
        
        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Initialize managers
        self.config_manager = ConfigManager("configs")
        settings = self.config_manager.load_settings()
        
        # Initialize dependency manager for auto-downloads
        self.dep_manager = DependencyManager(".")
        
        self.tor_manager = TorManager(
            settings.get("tor_path", ""),
            "logs/tor_data"
        )
        self.xray_manager = XRayManager(
            settings.get("xray_path", ""),
            "configs/xray"
        )
        self.proxy_manager = ProxyManager()
        
        # Check dependencies on startup
        self._check_dependencies_startup()
        
        # State
        self.tor_active = False
        self.xray_active = False
        self.current_server_index: Optional[int] = None
        self.servers = self.config_manager.load_servers()
        
        # Build UI
        self._build_ui()
        
        # Load saved data
        self._refresh_server_list()
    
    def _build_ui(self):
        """Build the main user interface"""
        # Main container
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)
        
        # Logo/Title
        self.logo_label = ctk.CTkLabel(
            self.sidebar, 
            text="🔒 SecureProxy", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Navigation buttons
        self.btn_dashboard = ctk.CTkButton(
            self.sidebar, 
            text="📊 Панель управления",
            command=self._show_dashboard,
            height=40
        )
        self.btn_dashboard.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        self.btn_servers = ctk.CTkButton(
            self.sidebar, 
            text="🌐 Серверы",
            command=self._show_servers,
            height=40
        )
        self.btn_servers.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        
        self.btn_apps = ctk.CTkButton(
            self.sidebar, 
            text="📱 Приложения",
            command=self._show_apps,
            height=40
        )
        self.btn_apps.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        
        self.btn_settings = ctk.CTkButton(
            self.sidebar, 
            text="⚙️ Настройки",
            command=self._show_settings,
            height=40
        )
        self.btn_settings.grid(row=4, column=0, padx=10, pady=5, sticky="ew")
        
        # Status indicator
        self.status_frame = ctk.CTkFrame(self.sidebar)
        self.status_frame.grid(row=5, column=0, padx=10, pady=20, sticky="ew")
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="● Статус: Остановлено",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(pady=10)
        
        # Main content area
        self.content_frame = ctk.CTkScrollableFrame(self, corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        
        # Show dashboard by default
        self._show_dashboard()
    
    def _clear_content(self):
        """Clear content area"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def _show_dashboard(self):
        """Show main dashboard"""
        self._clear_content()
        
        # Title
        title = ctk.CTkLabel(
            self.content_frame,
            text="Панель управления",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(pady=(20, 10), padx=20, anchor="w")
        
        # Quick actions frame
        actions_frame = ctk.CTkFrame(self.content_frame)
        actions_frame.pack(fill="x", padx=20, pady=10)
        
        # Tor control
        tor_frame = ctk.CTkFrame(actions_frame)
        tor_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(
            tor_frame,
            text="🧅 Tor Network",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        self.tor_status = ctk.CTkLabel(
            tor_frame,
            text="Остановлен",
            text_color="gray"
        )
        self.tor_status.pack(pady=5)
        
        self.btn_tor_toggle = ctk.CTkButton(
            tor_frame,
            text="Запустить Tor",
            command=self._toggle_tor,
            width=200
        )
        self.btn_tor_toggle.pack(pady=10)
        
        # X-Ray control
        xray_frame = ctk.CTkFrame(actions_frame)
        xray_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(
            xray_frame,
            text="⚡ X-Ray / V2Ray",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        self.xray_status = ctk.CTkLabel(
            xray_frame,
            text="Остановлен",
            text_color="gray"
        )
        self.xray_status.pack(pady=5)
        
        self.btn_xray_toggle = ctk.CTkButton(
            xray_frame,
            text="Запустить X-Ray",
            command=self._toggle_xray,
            width=200
        )
        self.btn_xray_toggle.pack(pady=10)
        
        # Proxy mode selection
        mode_frame = ctk.CTkFrame(self.content_frame)
        mode_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            mode_frame,
            text="Режим прокси:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left", padx=10)
        
        self.proxy_mode_var = tk.StringVar(value="socks5")
        self.mode_socks = ctk.CTkRadioButton(
            mode_frame,
            text="SOCKS5 (порт 10808)",
            variable=self.proxy_mode_var,
            value="socks5"
        )
        self.mode_socks.pack(side="left", padx=10)
        
        self.mode_system = ctk.CTkRadioButton(
            mode_frame,
            text="Системный прокси",
            variable=self.proxy_mode_var,
            value="system"
        )
        self.mode_system.pack(side="left", padx=10)
        
        # Connection test
        test_frame = ctk.CTkFrame(self.content_frame)
        test_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            test_frame,
            text="Проверка соединения:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left", padx=10)
        
        self.btn_test = ctk.CTkButton(
            test_frame,
            text="Тестировать",
            command=self._test_connection,
            width=150
        )
        self.btn_test.pack(side="left", padx=10)
        
        self.test_result = ctk.CTkLabel(
            test_frame,
            text="",
            text_color="gray"
        )
        self.test_result.pack(side="left", padx=10)
        
        # Log output
        ctk.CTkLabel(
            self.content_frame,
            text="Журнал событий:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(padx=20, pady=(10, 5), anchor="w")
        
        self.log_text = ctk.CTkTextbox(
            self.content_frame,
            height=200,
            state="disabled"
        )
        self.log_text.pack(fill="both", expand=True, padx=20, pady=10)
    
    def _show_servers(self):
        """Show servers management page"""
        self._clear_content()
        
        # Title
        title = ctk.CTkLabel(
            self.content_frame,
            text="Управление серверами",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(pady=(20, 10), padx=20, anchor="w")
        
        # Import from clipboard button
        btn_import = ctk.CTkButton(
            self.content_frame,
            text="📋 Импорт из буфера обмена",
            command=self._import_from_clipboard,
            width=200
        )
        btn_import.pack(pady=10, padx=20, anchor="w")
        
        # Server list
        self.server_list_frame = ctk.CTkFrame(self.content_frame)
        self.server_list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self._refresh_server_list()
        
        # Add server button
        btn_add = ctk.CTkButton(
            self.content_frame,
            text="+ Добавить сервер вручную",
            command=self._add_server_dialog,
            width=200
        )
        btn_add.pack(pady=10, padx=20, anchor="w")
    
    def _refresh_server_list(self):
        """Refresh server list display"""
        for widget in self.server_list_frame.winfo_children():
            widget.destroy()
        
        if not self.servers:
            ctk.CTkLabel(
                self.server_list_frame,
                text="Нет сохраненных серверов",
                text_color="gray"
            ).pack(pady=20)
            return
        
        for i, server in enumerate(self.servers):
            server_frame = ctk.CTkFrame(self.server_list_frame)
            server_frame.pack(fill="x", padx=5, pady=5)
            
            # Server info
            info = f"{server.get('name', 'Без имени')} - {server.get('protocol', 'unknown').upper()}"
            ctk.CTkLabel(
                server_frame,
                text=info,
                font=ctk.CTkFont(size=14)
            ).pack(side="left", padx=10, pady=10)
            
            # Select button
            btn_select = ctk.CTkButton(
                server_frame,
                text="Выбрать",
                width=100,
                command=lambda idx=i: self._select_server(idx)
            )
            btn_select.pack(side="right", padx=5, pady=5)
            
            # Delete button
            btn_delete = ctk.CTkButton(
                server_frame,
                text="Удалить",
                width=100,
                fg_color="red",
                hover_color="darkred",
                command=lambda idx=i: self._delete_server(idx)
            )
            btn_delete.pack(side="right", padx=5, pady=5)
    
    def _show_apps(self):
        """Show applications proxy configuration"""
        self._clear_content()
        
        title = ctk.CTkLabel(
            self.content_frame,
            text="Проксирование приложений",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(pady=(20, 10), padx=20, anchor="w")
        
        info = ctk.CTkLabel(
            self.content_frame,
            text="Запустите приложение через прокси или настройте его вручную",
            text_color="gray"
        )
        info.pack(padx=20, pady=5, anchor="w")
        
        # App launcher
        app_frame = ctk.CTkFrame(self.content_frame)
        app_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            app_frame,
            text="Путь к приложению:",
            font=ctk.CTkFont(size=14)
        ).pack(side="left", padx=10)
        
        self.app_path_entry = ctk.CTkEntry(
            app_frame,
            width=400
        )
        self.app_path_entry.pack(side="left", padx=10, pady=10)
        
        btn_browse = ctk.CTkButton(
            app_frame,
            text="Обзор...",
            command=self._browse_app,
            width=100
        )
        btn_browse.pack(side="left", padx=5)
        
        btn_launch = ctk.CTkButton(
            app_frame,
            text="Запустить с прокси",
            command=self._launch_app,
            width=150
        )
        btn_launch.pack(side="left", padx=10)
        
        # Manual configuration guide
        guide_frame = ctk.CTkFrame(self.content_frame)
        guide_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        ctk.CTkLabel(
            guide_frame,
            text="Ручная настройка прокси в приложениях:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(padx=10, pady=10, anchor="w")
        
        guide_text = ctk.CTkTextbox(
            guide_frame,
            height=200
        )
        guide_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        guide_content = """
SOCKS5 Прокси:
  Адрес: 127.0.0.1
  Порт: 10808

HTTP Прокси:
  Адрес: 127.0.0.1
  Порт: 10809

Поддерживаемые протоколы:
  • VMess (V2Ray)
  • VLESS (X-Ray)
  • Trojan
  • Shadowsocks
  • Tor (SOCKS5 порт 9150)

Для браузеров:
  Firefox: Настройки -> Параметры сети -> Настроить прокси
  Chrome: Используйте расширения типа Proxy SwitchyOmega
        """
        guide_text.insert("0.0", guide_content)
        guide_text.configure(state="disabled")
    
    def _show_settings(self):
        """Show settings page"""
        self._clear_content()
        
        title = ctk.CTkLabel(
            self.content_frame,
            text="Настройки приложения",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(pady=(20, 10), padx=20, anchor="w")
        
        settings = self.config_manager.load_settings()
        
        # Tor path
        tor_frame = ctk.CTkFrame(self.content_frame)
        tor_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            tor_frame,
            text="Путь к Tor (tor.exe):",
            font=ctk.CTkFont(size=14)
        ).pack(side="left", padx=10, pady=10)
        
        self.tor_path_entry = ctk.CTkEntry(
            tor_frame,
            width=400,
            placeholder_text=settings.get("tor_path", "")
        )
        self.tor_path_entry.pack(side="left", padx=10)
        
        btn_tor_browse = ctk.CTkButton(
            tor_frame,
            text="Обзор...",
            command=lambda: self._browse_exe(self.tor_path_entry),
            width=100
        )
        btn_tor_browse.pack(side="left", padx=5)
        
        # X-Ray path
        xray_frame = ctk.CTkFrame(self.content_frame)
        xray_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            xray_frame,
            text="Путь к X-Ray (xray.exe):",
            font=ctk.CTkFont(size=14)
        ).pack(side="left", padx=10, pady=10)
        
        self.xray_path_entry = ctk.CTkEntry(
            xray_frame,
            width=400,
            placeholder_text=settings.get("xray_path", "")
        )
        self.xray_path_entry.pack(side="left", padx=10)
        
        btn_xray_browse = ctk.CTkButton(
            xray_frame,
            text="Обзор...",
            command=lambda: self._browse_exe(self.xray_path_entry),
            width=100
        )
        btn_xray_browse.pack(side="left", padx=5)
        
        # Save button
        btn_save = ctk.CTkButton(
            self.content_frame,
            text="Сохранить настройки",
            command=self._save_settings,
            width=200
        )
        btn_save.pack(pady=20)
    
    def _toggle_tor(self):
        """Toggle Tor on/off"""
        if self.tor_active:
            success = self.tor_manager.stop(self._log)
            if success:
                self.tor_active = False
                self.tor_status.configure(text="Остановлен", text_color="gray")
                self.btn_tor_toggle.configure(text="Запустить Tor")
                self._log("Tor остановлен")
        else:
            success = self.tor_manager.start(self._log)
            if success:
                self.tor_active = True
                self.tor_status.configure(text="Работает", text_color="green")
                self.btn_tor_toggle.configure(text="Остановить Tor")
                self._log("Tor запущен на порту 9150")
    
    def _toggle_xray(self):
        """Toggle X-Ray on/off"""
        if self.xray_active:
            success = self.xray_manager.stop(self._log)
            if success:
                self.xray_active = False
                self.xray_status.configure(text="Остановлен", text_color="gray")
                self.btn_xray_toggle.configure(text="Запустить X-Ray")
                self._log("X-Ray остановлен")
        else:
            if self.current_server_index is None:
                messagebox.showwarning("Предупреждение", "Выберите сервер для подключения")
                return
            
            server = self.servers[self.current_server_index]
            success = self.xray_manager.start(server, self._log)
            if success:
                self.xray_active = True
                self.xray_status.configure(text="Работает", text_color="green")
                self.btn_xray_toggle.configure(text="Остановить X-Ray")
                self._log(f"X-Ray запущен ({server.get('protocol', 'unknown')})")
    
    def _select_server(self, index: int):
        """Select a server for connection"""
        self.current_server_index = index
        server = self.servers[index]
        self._log(f"Выбран сервер: {server.get('name', 'Без имени')}")
        messagebox.showinfo("Сервер выбран", f"Сервер: {server.get('name', 'Без имени')}\nПротокол: {server.get('protocol', 'unknown').upper()}")
    
    def _delete_server(self, index: int):
        """Delete a server"""
        if messagebox.askyesno("Подтверждение", "Удалить этот сервер?"):
            self.config_manager.remove_server(index)
            self.servers = self.config_manager.load_servers()
            self._refresh_server_list()
            self._log("Сервер удален")
    
    def _import_from_clipboard(self):
        """Import server from clipboard"""
        try:
            text = pyperclip.paste()
            server = self.config_manager.import_from_clipboard(text)
            if server:
                self.config_manager.add_server(server)
                self.servers = self.config_manager.load_servers()
                self._refresh_server_list()
                self._log(f"Импортирован сервер: {server.get('name', 'Без имени')}")
                messagebox.showinfo("Успех", "Сервер успешно импортирован!")
            else:
                messagebox.showerror("Ошибка", "Не удалось распознать формат ссылки")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка импорта: {str(e)}")
    
    def _add_server_dialog(self):
        """Open dialog to add server manually"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Добавить сервер")
        dialog.geometry("500x600")
        
        ctk.CTkLabel(
            dialog,
            text="Добавление сервера",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=10)
        
        form_frame = ctk.CTkScrollableFrame(dialog)
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Protocol selection
        ctk.CTkLabel(form_frame, text="Протокол:").pack(anchor="w", padx=10, pady=5)
        protocol_var = tk.StringVar(value="vmess")
        protocol_menu = ctk.CTkOptionMenu(
            form_frame,
            variable=protocol_var,
            values=["vmess", "vless", "trojan", "shadowsocks"]
        )
        protocol_menu.pack(fill="x", padx=10, pady=5)
        
        # Name
        ctk.CTkLabel(form_frame, text="Название:").pack(anchor="w", padx=10, pady=5)
        name_entry = ctk.CTkEntry(form_frame)
        name_entry.pack(fill="x", padx=10, pady=5)
        
        # Address
        ctk.CTkLabel(form_frame, text="Адрес сервера:").pack(anchor="w", padx=10, pady=5)
        address_entry = ctk.CTkEntry(form_frame)
        address_entry.pack(fill="x", padx=10, pady=5)
        
        # Port
        ctk.CTkLabel(form_frame, text="Порт:").pack(anchor="w", padx=10, pady=5)
        port_entry = ctk.CTkEntry(form_frame)
        port_entry.pack(fill="x", padx=10, pady=5)
        
        # UUID/Password
        ctk.CTkLabel(form_frame, text="UUID/Пароль:").pack(anchor="w", padx=10, pady=5)
        uuid_entry = ctk.CTkEntry(form_frame)
        uuid_entry.pack(fill="x", padx=10, pady=5)
        
        def save_server():
            server = {
                "protocol": protocol_var.get(),
                "name": name_entry.get() or "Новый сервер",
                "address": address_entry.get(),
                "port": int(port_entry.get()) if port_entry.get().isdigit() else 443,
            }
            
            if protocol_var.get() in ["vmess", "vless"]:
                server["uuid"] = uuid_entry.get()
            elif protocol_var.get() == "trojan":
                server["password"] = uuid_entry.get()
            elif protocol_var.get() == "shadowsocks":
                server["password"] = uuid_entry.get()
                server["method"] = "aes-256-gcm"
            
            if not server["address"]:
                messagebox.showerror("Ошибка", "Введите адрес сервера")
                return
            
            self.config_manager.add_server(server)
            self.servers = self.config_manager.load_servers()
            self._refresh_server_list()
            self._log(f"Добавлен сервер: {server['name']}")
            dialog.destroy()
            messagebox.showinfo("Успех", "Сервер добавлен!")
        
        btn_save = ctk.CTkButton(
            dialog,
            text="Сохранить",
            command=save_server,
            width=200
        )
        btn_save.pack(pady=20)
    
    def _browse_app(self):
        """Browse for application executable"""
        filename = filedialog.askopenfilename(
            title="Выберите приложение",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if filename:
            self.app_path_entry.delete(0, tk.END)
            self.app_path_entry.insert(0, filename)
    
    def _browse_exe(self, entry_widget):
        """Browse for executable file"""
        filename = filedialog.askopenfilename(
            title="Выберите исполняемый файл",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if filename:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, filename)
    
    def _launch_app(self):
        """Launch application with proxy"""
        app_path = self.app_path_entry.get()
        if not app_path:
            messagebox.showerror("Ошибка", "Выберите приложение")
            return
        
        proxy_url = "socks5://127.0.0.1:10808"
        self.proxy_manager.launch_app_with_proxy(app_path, proxy_url)
        self._log(f"Запущено приложение: {app_path}")
    
    def _test_connection(self):
        """Test proxy connection"""
        self.test_result.configure(text="Тестирование...", text_color="yellow")
        self.update_idletasks()
        
        def test():
            proxy_url = "socks5://127.0.0.1:10808"
            if self.tor_active:
                proxy_url = "socks5://127.0.0.1:9150"
            
            success = self.proxy_manager.test_proxy_connection(proxy_url)
            
            self.after(0, lambda: self.test_result.configure(
                text="✓ Работает" if success else "✗ Не работает",
                text_color="green" if success else "red"
            ))
        
        thread = threading.Thread(target=test)
        thread.daemon = True
        thread.start()
    
    def _save_settings(self):
        """Save application settings"""
        settings = self.config_manager.load_settings()
        settings["tor_path"] = self.tor_path_entry.get()
        settings["xray_path"] = self.xray_path_entry.get()
        
        if self.config_manager.save_settings(settings):
            messagebox.showinfo("Успех", "Настройки сохранены!")
            self._log("Настройки сохранены")
        else:
            messagebox.showerror("Ошибка", "Не удалось сохранить настройки")
    
    def _check_dependencies_startup(self):
        """Check dependencies on startup and prompt for installation if needed"""
        status = self.dep_manager.check_all_dependencies()
        missing = []
        
        if not status["tor"]["installed"]:
            missing.append("Tor")
        if not status["xray"]["installed"]:
            missing.append("X-Ray")
        
        if missing:
            threading.Thread(target=self._show_dependency_dialog, args=(missing,), daemon=True).start()

    def _show_dependency_dialog(self, missing: list):
        """Show dialog for missing dependencies"""
        def show_dialog():
            components = " и ".join(missing)
            result = messagebox.askyesno(
                "Отсутствуют зависимости",
                f"Обнаружено отсутствие компонентов: {components}.\n\n"
                f"Хотите скачать и установить их автоматически?\n\n"
                f"Если загрузка не удастся (из-за блокировок), "
                f"вам будет предложено скачать их вручную.",
                icon="warning"
            )
            
            if result:
                threading.Thread(target=self._install_dependencies, daemon=True).start()
            else:
                self._log("Пользователь отказался от автоматической установки зависимостей")
        
        self.after(0, show_dialog)

    def _install_dependencies(self):
        """Install missing dependencies with progress updates"""
        def update_log(msg):
            self.after(0, lambda: self._log(msg))
        
        self.dep_manager.set_status_callback(update_log)
        results = self.dep_manager.install_or_update_all(update_log)
        
        def show_results():
            success = []
            failed = []
            
            if results["tor"]:
                success.append("Tor")
            else:
                failed.append("Tor")
            
            if results["xray"]:
                success.append("X-Ray")
            else:
                failed.append("X-Ray")
            
            message = ""
            if success:
                message += f"✅ Успешно установлены: {', '.join(success)}\n\n"
            
            if failed:
                message += f"❌ Не удалось установить: {', '.join(failed)}\n\n"
                message += "Причина: Возможно, доступ к источникам заблокирован.\n\n"
                message += "Инструкция по ручной установке:\n\n"
                
                for comp in failed:
                    if comp == "Tor":
                        message += self.dep_manager.get_installation_instructions("tor")
                    elif comp == "X-Ray":
                        message += self.dep_manager.get_installation_instructions("xray")
                
                messagebox.showwarning(
                    "Ручная установка требуется",
                    message
                )
            else:
                messagebox.showinfo(
                    "Установка завершена",
                    f"Все компоненты успешно установлены!\n\n"
                    f"Теперь вы можете использовать приложение."
                )
        
        self.after(0, show_results)
        """Add message to log"""
        self.log_text.configure(state="normal")
        timestamp = threading.current_thread().name
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        
        # Update status
        if self.tor_active or self.xray_active:
            self.status_label.configure(
                text="● Статус: Активно",
                text_color="green"
            )
        else:
            self.status_label.configure(
                text="● Статус: Остановлено",
                text_color="gray"
            )


def main():
    app = ProxyApp()
    app.mainloop()


if __name__ == "__main__":
    main()

    def _check_dependencies_startup(self):
        """Check dependencies on startup and prompt for installation if needed"""
        status = self.dep_manager.check_all_dependencies()
        missing = []
        
        if not status["tor"]["installed"]:
            missing.append("Tor")
        if not status["xray"]["installed"]:
            missing.append("X-Ray")
        
        if missing:
            threading.Thread(target=self._show_dependency_dialog, args=(missing,), daemon=True).start()
    
    def _show_dependency_dialog(self, missing: list):
        """Show dialog for missing dependencies"""
        def show_dialog():
            components = " и ".join(missing)
            result = messagebox.askyesno(
                "Отсутствуют зависимости",
                f"Обнаружено отсутствие компонентов: {components}.\n\n"
                f"Хотите скачать и установить их автоматически?\n\n"
                f"Если загрузка не удастся (из-за блокировок), "
                f"вам будет предложено скачать их вручную.",
                icon="warning"
            )
            
            if result:
                threading.Thread(target=self._install_dependencies, daemon=True).start()
            else:
                self._log("Пользователь отказался от автоматической установки зависимостей")
        
        self.after(0, show_dialog)
    
    def _install_dependencies(self):
        """Install missing dependencies with progress updates"""
        def update_log(msg):
            self.after(0, lambda: self._log(msg))
        
        self.dep_manager.set_status_callback(update_log)
        results = self.dep_manager.install_or_update_all(update_log)
        
        def show_results():
            success = []
            failed = []
            
            if results["tor"]:
                success.append("Tor")
            else:
                failed.append("Tor")
            
            if results["xray"]:
                success.append("X-Ray")
            else:
                failed.append("X-Ray")
            
            message = ""
            if success:
                message += f"✅ Успешно установлены: {', '.join(success)}\n\n"
            
            if failed:
                message += f"❌ Не удалось установить: {', '.join(failed)}\n\n"
                message += "Причина: Возможно, доступ к источникам заблокирован.\n\n"
                message += "Инструкция по ручной установке:\n\n"
                
                for comp in failed:
                    if comp == "Tor":
                        message += self.dep_manager.get_installation_instructions("tor")
                    elif comp == "X-Ray":
                        message += self.dep_manager.get_installation_instructions("xray")
                
                messagebox.showwarning(
                    "Ручная установка требуется",
                    message
                )
            else:
                messagebox.showinfo(
                    "Установка завершена",
                    f"Все компоненты успешно установлены!\n\n"
                    f"Теперь вы можете использовать приложение."
                )
        
        self.after(0, show_results)

    def _log(self, message: str):
        """Add message to log"""
        self.log_text.configure(state="normal")
        timestamp = threading.current_thread().name
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        
        # Update status
        if self.tor_active or self.xray_active:
            self.status_label.configure(
                text="● Статус: Активно",
                text_color="green"
            )
        else:
            self.status_label.configure(
                text="● Статус: Остановлено",
                text_color="gray"
            )


def main():
    app = ProxyApp()
    app.mainloop()


if __name__ == "__main__":
    main()
