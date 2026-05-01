import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
import os
import sys
import time
from core.dependency_manager import DependencyManager
from core.tor_manager import TorManager
from core.xray_manager import XrayManager
from core.proxy_manager import ProxyManager
import pyperclip

class SecureProxyApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("SecureProxy")
        self.geometry("900x700")
        
        # Инициализация менеджеров
        self.dep_manager = DependencyManager()
        self.tor_manager = TorManager()
        self.xray_manager = XrayManager()
        self.proxy_manager = ProxyManager()
        
        self.config_file = "config.json"
        self.servers = []
        self.current_connection = None
        
        # Загрузка конфигурации
        self.load_config()
        
        # Создание интерфейса
        self._create_ui()
        
        # Проверка зависимостей в фоне
        self.after(100, self._check_dependencies_async)

    def _create_ui(self):
        # Главный фрейм
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Верхняя панель
        self.top_frame = ctk.CTkFrame(self.main_frame)
        self.top_frame.pack(fill="x", pady=(0, 10))
        
        self.status_label = ctk.CTkLabel(self.top_frame, text="Статус: Отключено", font=("Arial", 14, "bold"))
        self.status_label.pack(side="left", padx=10)
        
        self.connect_btn = ctk.CTkButton(self.top_frame, text="Подключить", command=self.toggle_connection, width=120)
        self.connect_btn.pack(side="right", padx=10)
        
        # Фрейм списка серверов (ИСПРАВЛЕНИЕ: явное создание атрибута до использования)
        self.server_list_frame = ctk.CTkFrame(self.main_frame)
        self.server_list_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Заголовок списка
        header_frame = ctk.CTkFrame(self.server_list_frame)
        header_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(header_frame, text="Название", width=200).pack(side="left", padx=10)
        ctk.CTkLabel(header_frame, text="Протокол", width=100).pack(side="left", padx=10)
        ctk.CTkLabel(header_frame, text="Статус", width=100).pack(side="left", padx=10)
        ctk.CTkLabel(header_frame, text="Действия", width=150).pack(side="left", padx=10)
        
        # Скроллируемая область для списка
        self.canvas = ctk.CTkCanvas(self.server_list_frame, highlightthickness=0)
        self.scrollbar = ctk.CTkScrollbar(self.server_list_frame, orientation="vertical", command=self.canvas.yview)
        self.scrollable_frame = ctk.CTkFrame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Привязка колеса мыши
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Нижняя панель
        self.bottom_frame = ctk.CTkFrame(self.main_frame)
        self.bottom_frame.pack(fill="x", pady=(10, 0))
        
        self.add_btn = ctk.CTkButton(self.bottom_frame, text="Добавить из буфера", command=self.add_from_clipboard)
        self.add_btn.pack(side="left", padx=10)
        
        self.settings_btn = ctk.CTkButton(self.bottom_frame, text="Настройки", command=self.open_settings)
        self.settings_btn.pack(side="right", padx=10)
        
        # Обновление списка
        self._refresh_server_list()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _check_dependencies_async(self):
        def check():
            try:
                status = self.dep_manager.check_all()
                if not status['tor'] or not status['xray']:
                    self.after(0, lambda: self._show_dependency_warning(status))
            except Exception:
                pass
        
        threading.Thread(target=check, daemon=True).start()

    def _show_dependency_warning(self, status):
        missing = []
        if not status.get('tor'): missing.append("Tor")
        if not status.get('xray'): missing.append("X-Ray")
        
        if not missing: return

        msg = f"Отсутствуют компоненты: {', '.join(missing)}.\nСкачать автоматически?"
        # Используем try-except для messagebox, так как в потоке может быть нюанс
        try:
            if messagebox.askyesno("Внимание", msg):
                self._download_dependencies()
        except:
            pass

    def _download_dependencies(self):
        def download():
            try:
                self.dep_manager.install_tor()
                self.dep_manager.install_xray()
                self.after(0, lambda: messagebox.showinfo("Успех", "Все компоненты установлены!"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось скачать: {str(e)}\nПожалуйста, скачайте вручную."))
        
        threading.Thread(target=download, daemon=True).start()

    def _refresh_server_list(self):
        # Безопасная очистка
        if not hasattr(self, 'scrollable_frame'):
            return
            
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
            
        if not self.servers:
            ctk.CTkLabel(self.scrollable_frame, text="Список пуст. Добавьте конфигурацию.").pack(pady=20)
            return
            
        for i, server in enumerate(self.servers):
            row_frame = ctk.CTkFrame(self.scrollable_frame)
            row_frame.pack(fill="x", padx=5, pady=2)
            
            ctk.CTkLabel(row_frame, text=server.get('name', 'Unknown'), width=200, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(row_frame, text=server.get('protocol', 'Unknown'), width=100, anchor="w").pack(side="left", padx=10)
            
            status_text = "OK" if server.get('active', False) else "Off"
            status_color = "#00ff00" if server.get('active', False) else "gray"
            ctk.CTkLabel(row_frame, text=status_text, width=100, text_color=status_color, anchor="w").pack(side="left", padx=10)
            
            btn_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            btn_frame.pack(side="left", fill="x", expand=True)
            
            ctk.CTkButton(btn_frame, text="Выбрать", width=60, 
                         command=lambda s=server: self.select_server(s)).pack(side="left", padx=5)
            ctk.CTkButton(btn_frame, text="Удалить", width=60, fg_color="#cc0000",
                         command=lambda idx=i: self.delete_server(idx)).pack(side="left", padx=5)

    def toggle_connection(self):
        if self.current_connection:
            self.disconnect()
        else:
            self.connect()

    def connect(self):
        self.status_label.configure(text="Статус: Подключение...", text_color="orange")
        self.connect_btn.configure(text="Отключить", fg_color="red")
        
        def run_connect():
            time.sleep(2)
            self.current_connection = "active"
            self.after(0, lambda: self.status_label.configure(text="Статус: Подключено", text_color="green"))
            
        threading.Thread(target=run_connect, daemon=True).start()

    def disconnect(self):
        self.current_connection = None
        self.status_label.configure(text="Статус: Отключено", text_color="black")
        self.connect_btn.configure(text="Подключить", fg_color="green")

    def add_from_clipboard(self):
        try:
            data = pyperclip.paste()
            if not data:
                messagebox.showwarning("Внимание", "Буфер обмена пуст")
                return
                
            new_server = {
                "name": f"Server_{len(self.servers)+1}",
                "protocol": "VLESS",
                "config": data,
                "active": False
            }
            self.servers.append(new_server)
            self.save_config()
            self._refresh_server_list()
            messagebox.showinfo("Успех", "Конфигурация добавлена!")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def select_server(self, server):
        for s in self.servers:
            s['active'] = (s == server)
        self.save_config()
        self._refresh_server_list()
        messagebox.showinfo("Инфо", f"Выбран сервер: {server['name']}")

    def delete_server(self, index):
        if 0 <= index < len(self.servers):
            del self.servers[index]
            self.save_config()
            self._refresh_server_list()

    def open_settings(self):
        messagebox.showinfo("Настройки", "Функция в разработке")

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.servers = json.load(f)
            except:
                self.servers = []
        else:
            self.servers = []

    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.servers, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

def main():
    app = SecureProxyApp()
    app.mainloop()

if __name__ == "__main__":
    main()
