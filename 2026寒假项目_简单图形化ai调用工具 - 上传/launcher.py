import tkinter as tk
from tkinter import scrolledtext
import subprocess
import sys
import os
import threading
import queue
import webbrowser
import platform
import re
from datetime import datetime
import json

# 全局尝试导入torch
try:
    import torch
    print("PyTorch版本:", torch.__version__)
except ImportError:
    torch = None
    print("警告：未安装PyTorch，无法检测NVIDIA显卡")

# 导入CustomTkinter库
import customtkinter as ctk

class FlaskServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI图形化工具")
        self.root.geometry("1000x600")
        
        # 设置CustomTkinter主题
        ctk.set_appearance_mode("dark")  # Modes: "System" (default), "Dark", "Light"
        ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"
        
        # 创建队列用于进程间通信
        self.queue = queue.Queue()
        
        # 终端输出缓冲区
        self.output_buffer = []
        self.buffer_lock = threading.Lock()
        self.flush_pending = False
        self.enable_terminal_output = True  # 是否启用终端输出
        
        # 服务器进程
        self.server_process = None
        
        # 生成引擎下拉菜单变量
        self.engine_var = None
        
        # 创建顶部状态栏
        self.create_status_bar()
        
        # 创建左侧导航栏
        self.create_sidebar()
        
        # 创建右侧内容区域
        self.create_content_area()
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # 延迟更新生成引擎选项
        self.root.after(100, self.update_engine_options)
    
    def create_status_bar(self):
        """创建顶部状态栏"""
        status_frame = ctk.CTkFrame(self.root, fg_color="#1e1e1e", height=40)
        status_frame.pack(fill=tk.X, side=tk.TOP)
        
        # 状态栏左侧
        self.status_label = ctk.CTkLabel(status_frame, text="未运行", text_color="#ff4757", 
                                   fg_color="#1e1e1e", font= ("Arial", 10))
        self.status_label.pack(side=tk.LEFT, padx=10, pady=10)
        
        # 状态栏右侧
        button_frame = ctk.CTkFrame(status_frame, fg_color="#1e1e1e")
        button_frame.pack(side=tk.RIGHT, padx=10)
        
        # 生成诊断包按钮
        diag_button = ctk.CTkButton(button_frame, text="生成诊断包", 
                                   fg_color="#3c3c3c", hover_color="#4a4a4a",
                                   text_color="white", font=("Arial", 10), 
                                   width=100, command=self.generate_diagnostic)
        diag_button.pack(side=tk.RIGHT, padx=5)
        
        # 终止进程按钮
        stop_button = ctk.CTkButton(button_frame, text="终止进程", 
                                   fg_color="#3c3c3c", hover_color="#4a4a4a",
                                   text_color="white", font=("Arial", 10), 
                                   width=100, command=self.stop_server)
        stop_button.pack(side=tk.RIGHT, padx=5)
        
        # 一键启动按钮
        start_button = ctk.CTkButton(button_frame, text="一键启动", 
                                    fg_color="#3c3c3c", hover_color="#4a4a4a",
                                    text_color="white", font=("Arial", 10), 
                                    width=100, command=self.start_server)
        start_button.pack(side=tk.RIGHT, padx=5)
    
    def create_sidebar(self):
        """创建左侧导航栏"""
        sidebar_frame = ctk.CTkFrame(self.root, fg_color="#1e1e1e", width=180)
        sidebar_frame.pack(fill=tk.Y, side=tk.LEFT)
        
        # 导航项列表
        nav_items = [
            ("设置", self.show_settings),
            ("高级设置", self.show_advanced_settings),
            ("终端面板", self.show_terminal)
        ]
        
        for i, (text, command) in enumerate(nav_items):
            button = ctk.CTkButton(sidebar_frame, text=text, 
                                  fg_color="#1e1e1e", hover_color="#3c3c3c",
                                  text_color="white", font=("Arial", 10), 
                                  width=160, height=40, 
                                  command=command, corner_radius=4)
            button.pack(pady=2, padx=10)
            
            # 添加分隔线
            if i < len(nav_items) - 1:
                separator = ctk.CTkFrame(sidebar_frame, fg_color="#3c3c3c", height=1)
                separator.pack(fill=tk.X, pady=5, padx=10)
    
    def create_content_area(self):
        """创建右侧内容区域"""
        content_frame = ctk.CTkFrame(self.root, fg_color="#2c2c2c")
        content_frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)
        
        # 创建三个页面的容器
        self.settings_frame = ctk.CTkFrame(content_frame, fg_color="#2c2c2c")
        self.advanced_frame = ctk.CTkFrame(content_frame, fg_color="#2c2c2c")
        self.terminal_frame = ctk.CTkFrame(content_frame, fg_color="#2c2c2c")
        
        # 初始化各个页面
        self.init_settings()
        self.init_advanced_settings()
        self.init_terminal()
        
        # 默认显示设置页面
        self.show_settings()
    
    def init_terminal(self):
        """初始化终端面板"""
        # 创建滚动文本框
        self.terminal_text = scrolledtext.ScrolledText(self.terminal_frame, 
                                                      bg="#1e1e1e", fg="#d4d4d4",
                                                      font=("Consolas", 10),
                                                      wrap=tk.WORD)
        self.terminal_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.terminal_text.config(state=tk.DISABLED)
        
        # 开始监听队列
        self.root.after(100, self.check_queue)
    
    def init_settings(self):
        """初始化设置页面"""
        settings_label = ctk.CTkLabel(self.settings_frame, text="基本设置", 
                                    text_color="white", font=("Arial", 12, "bold"))
        settings_label.pack(padx=20, pady=20)
        
        # 添加模型文件夹路径设置
        self.create_path_setting(self.settings_frame, "模型文件夹路径", 
                                "默认的模型文件夹路径，Checkpoint加载器等模块会使用此路径",
                                os.path.join(os.getcwd(), "models"))
        
        # 添加默认图片保存路径设置
        self.create_path_setting(self.settings_frame, "默认图片保存路径", 
                                "默认的图片保存路径，图片保存/显示模块会使用此路径",
                                os.path.join(os.getcwd(), "auto_save"))
        
        # 添加保存按钮
        save_button = ctk.CTkButton(self.settings_frame, text="保存设置", 
                                   fg_color="#4ec9b0", hover_color="#3db89f",
                                   text_color="white", font=("Arial", 10), 
                                   width=120, command=self.save_path_settings)
        save_button.pack(pady=20)
        
        # 添加一些设置项
        setting_items = [
            "服务器端口: 5000",
            "主机地址: 0.0.0.0",
            "调试模式: 关闭",
            "自动保存: 开启"
        ]
        
        for item in setting_items:
            item_label = ctk.CTkLabel(self.settings_frame, text=item, 
                                     text_color="#d4d4d4", font=("Arial", 10))
            item_label.pack(padx=30, pady=5, anchor=tk.W)
    
    def create_path_setting(self, parent, title, description, default_value):
        """创建路径设置项"""
        frame = ctk.CTkFrame(parent, fg_color="#2c2c2c")
        frame.pack(fill=tk.X, pady=10)
        
        # 标题
        title_label = ctk.CTkLabel(frame, text=title, 
                                  text_color="white", font=("Arial", 10, "bold"))
        title_label.pack(side=tk.LEFT, padx=20, pady=5)
        
        # 描述
        desc_label = ctk.CTkLabel(frame, text=description, 
                                 text_color="#d4d4d4", font=("Arial", 9))
        desc_label.pack(side=tk.LEFT, padx=20, pady=5, fill=tk.X, expand=True)
        
        # 路径输入框和浏览按钮
        input_frame = ctk.CTkFrame(frame, fg_color="#2c2c2c")
        input_frame.pack(fill=tk.X, padx=30, pady=5)
        
        path_input = ctk.CTkEntry(input_frame, placeholder_text=default_value)
        path_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        browse_button = ctk.CTkButton(input_frame, text="浏览", 
                                       fg_color="#3c3c3c", hover_color="#4a4a4a",
                                       text_color="white", font=("Arial", 9), 
                                       width=80, command=lambda: self.browse_path(path_input))
        browse_button.pack(side=tk.RIGHT)
        
        # 保存到实例变量
        setattr(self, f"{title.replace(' ', '_')}_input", path_input)
        
        # 加载保存的设置
        self.load_path_setting(path_input, title, default_value)
    
    def browse_path(self, entry_widget):
        """浏览文件夹"""
        from tkinter import filedialog
        folder_path = filedialog.askdirectory()
        if folder_path:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, folder_path)
    
    def load_path_setting(self, entry_widget, title, default_value):
        """加载保存的路径设置"""
        settings_file = os.path.join(os.getcwd(), "gui_settings.json")
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    saved_path = settings.get(title, default_value)
                    if saved_path:
                        entry_widget.delete(0, tk.END)
                        entry_widget.insert(0, saved_path)
            except Exception as e:
                print(f"加载设置失败: {e}")
    
    def load_engine_setting(self):
        """加载保存的生成引擎设置"""
        settings_file = os.path.join(os.getcwd(), "gui_settings.json")
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    saved_engine = settings.get("生成引擎")
                    if saved_engine and hasattr(self, "engine_var"):
                        self.engine_var.set(saved_engine)
            except Exception as e:
                print(f"加载生成引擎设置失败: {e}")
    
    def load_vae_setting(self):
        """加载保存的使用 CPU 运行 VAE 设置"""
        settings_file = os.path.join(os.getcwd(), "gui_settings.json")
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    saved_vae = settings.get("使用 CPU 运行 VAE", False)
                    if hasattr(self, "使用_CPU_运行_VAE_var"):
                        self.使用_CPU_运行_VAE_var.set(saved_vae)
            except Exception as e:
                print(f"加载使用 CPU 运行 VAE 设置失败: {e}")
    
    def save_path_settings(self):
        """保存路径设置"""
        settings_file = os.path.join(os.getcwd(), "gui_settings.json")
        settings = {}
        
        # 获取模型文件夹路径
        if hasattr(self, "模型文件夹路径_input"):
            path_value = self.模型文件夹路径_input.get()
            if path_value:
                settings["模型文件夹路径"] = path_value
        
        # 获取默认图片保存路径
        if hasattr(self, "默认图片保存路径_input"):
            path_value = self.默认图片保存路径_input.get()
            if path_value:
                settings["默认图片保存路径"] = path_value
        
        # 获取生成引擎设置
        if hasattr(self, "engine_var"):
            engine_value = self.engine_var.get()
            if engine_value:
                settings["生成引擎"] = engine_value
        
        # 获取使用 CPU 运行 VAE 设置
        if hasattr(self, "使用_CPU_运行_VAE_var"):
            vae_value = self.使用_CPU_运行_VAE_var.get()
            settings["使用 CPU 运行 VAE"] = vae_value
        
        try:
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            self.append_to_terminal("设置已保存\n")
        except Exception as e:
            print(f"保存设置失败: {e}")
            self.append_to_terminal(f"保存设置失败: {e}\n")
    
    def init_advanced_settings(self):
        """初始化高级设置页面"""
        # 一键安装栏
        install_bar = ctk.CTkFrame(self.advanced_frame, fg_color="#2d2d2d", height=80)
        install_bar.pack(fill=tk.X, side=tk.TOP, pady=10, padx=10)
        
        # 标题
        install_title = ctk.CTkLabel(install_bar, text="环境一键安装", 
                                    text_color="white", font= ("Arial", 12, "bold"))
        install_title.pack(side=tk.LEFT, padx=20, pady=10)
        
        # 描述
        install_desc = ctk.CTkLabel(install_bar, text="快速安装 CUDA 或 DML 虚拟环境及依赖", 
                                    text_color="#d4d4d4", font= ("Arial", 9))
        install_desc.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.X, expand=True)
        
        # 一键安装按钮
        install_button = ctk.CTkButton(install_bar, text="一键安装", 
                                      fg_color="#4ec9b0", hover_color="#3db89f",
                                      text_color="white", font= ("Arial", 10), 
                                      width=120, height=40, command=self.show_install_dialog)
        install_button.pack(side=tk.RIGHT, padx=20, pady=10)
        
        # 顶部操作栏
        top_bar = ctk.CTkFrame(self.advanced_frame, fg_color="#1e1e1e", height=40)
        top_bar.pack(fill=tk.X, side=tk.TOP, pady=10, padx=10)
        
        # 标题
        title_label = ctk.CTkLabel(top_bar, text="性能设置", 
                                  text_color="white", font= ("Arial", 12, "bold"))
        title_label.pack(side=tk.LEFT, padx=10, pady=10)
        
        # 保存设置按钮
        save_button = ctk.CTkButton(top_bar, text="保存设置", 
                                    fg_color="#4ec9b0", hover_color="#3db89f",
                                    text_color="white", font= ("Arial", 10), 
                                    width=100, command=self.save_path_settings)
        save_button.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # 核心设置区域
        settings_frame = ctk.CTkFrame(self.advanced_frame, fg_color="#2c2c2c")
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 生成引擎
        self.engine_var = self.create_setting_item(settings_frame, "生成引擎", 
                                "选择参与计算的硬件引擎", 
                                ["检测中..."],  # 临时占位
                                default="检测中...")
        
        # 使用 CPU 运行 VAE
        self.create_switch_setting(settings_frame, "使用 CPU 运行 VAE", 
                                 "显著降低峰值显存消耗，但会降低整体速度")
        
        # 加载保存的使用 CPU 运行 VAE 设置
        self.load_vae_setting()
    
    def create_setting_item(self, parent, title, description, options, default=None):
        """创建设置项（带下拉菜单）"""
        frame = ctk.CTkFrame(parent, fg_color="#2c2c2c")
        frame.pack(fill=tk.X, pady=10)
        
        # 标题
        title_label = ctk.CTkLabel(frame, text=title, 
                                  text_color="white", font= ("Arial", 10, "bold"))
        title_label.pack(side=tk.LEFT, padx=20, pady=5)
        
        # 描述
        desc_label = ctk.CTkLabel(frame, text=description, 
                                 text_color="#d4d4d4", font= ("Arial", 9))
        desc_label.pack(side=tk.LEFT, padx=20, pady=5, fill=tk.X, expand=True)
        
        # 下拉菜单
        option_var = ctk.StringVar(value=default if default else options[0])
        self.option_menu = ctk.CTkOptionMenu(frame, values=options, 
                                       variable=option_var, 
                                       fg_color="#3c3c3c", button_color="#57606f", 
                                       button_hover_color="#747d8c", text_color="white", 
                                       font= ("Arial", 9), width=200)
        self.option_menu.pack(side=tk.RIGHT, padx=20, pady=5)
        
        # 保存下拉菜单对象
        setattr(self, f"{title.replace(' ', '_')}_menu", self.option_menu)
        
        return option_var
    
    def create_precision_setting(self, parent, title, options, default):
        """创建精度设置项"""
        frame = ctk.CTkFrame(parent, fg_color="#3c3c3c")
        frame.pack(fill=tk.X, pady=5)
        
        # 标题
        label = ctk.CTkLabel(frame, text=title, 
                            text_color="#d4d4d4", font= ("Arial", 9))
        label.pack(side=tk.LEFT, padx=20, pady=5, fill=tk.X, expand=True)
        
        # 下拉菜单
        option_var = ctk.StringVar(value=default)
        option_menu = ctk.CTkOptionMenu(frame, values=options, 
                                       variable=option_var, 
                                       fg_color="#4a4a4a", button_color="#57606f", 
                                       button_hover_color="#747d8c", text_color="white", 
                                       font= ("Arial", 8), width=150)
        option_menu.pack(side=tk.RIGHT, padx=20, pady=5)
        
        return option_var
    
    def create_switch_setting(self, parent, title, description, default=False):
        """创建开关型设置项"""
        frame = ctk.CTkFrame(parent, fg_color="#2c2c2c")
        frame.pack(fill=tk.X, pady=10)
        
        # 标题
        title_label = ctk.CTkLabel(frame, text=title, 
                                  text_color="white", font= ("Arial", 10, "bold"))
        title_label.pack(side=tk.LEFT, padx=20, pady=5)
        
        # 描述
        desc_label = ctk.CTkLabel(frame, text=description, 
                                 text_color="#d4d4d4", font= ("Arial", 9))
        desc_label.pack(side=tk.LEFT, padx=20, pady=5, fill=tk.X, expand=True)
        
        # 开关
        switch_var = ctk.BooleanVar(value=default)
        switch = ctk.CTkSwitch(frame, text="", fg_color="#57606f", 
                              progress_color="#4ec9b0", 
                              variable=switch_var)
        switch.pack(side=tk.RIGHT, padx=20, pady=5)
        
        # 保存开关对象和变量
        setattr(self, f"{title.replace(' ', '_')}_switch", switch)
        setattr(self, f"{title.replace(' ', '_')}_var", switch_var)
        
        return switch_var
    
    def update_engine_options(self):
        """更新生成引擎选项"""
        try:
            engine_options = self.detect_available_engines()
            if hasattr(self, "生成引擎_menu") and engine_options:
                self.生成引擎_menu.configure(values=engine_options)
                # 先尝试加载保存的设置
                self.load_engine_setting()
                # 如果保存的设置不在选项中，使用默认值
                current_engine = self.engine_var.get()
                if current_engine not in engine_options:
                    self.engine_var.set(engine_options[0])
        except Exception as e:
            print(f"更新生成引擎选项失败: {e}")
            if hasattr(self, "生成引擎_menu"):
                self.生成引擎_menu.configure(values=["CPU"])
                self.engine_var.set("CPU")
    
    def detect_amd_gpus_windows(self, existing_gpu_names=None):
        """在Windows系统中检测AMD显卡"""
        if existing_gpu_names is None:
            existing_gpu_names = []
        
        gpu_list = []
        try:
            result = subprocess.check_output(
                ["wmic", "path", "win32_VideoController", "get", "Name,AdapterRAM"],
                encoding="utf-8", errors="ignore",
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            lines = result.strip().split("\n")[1:]  # 跳过表头
            amd_index = 0
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # 解析显卡名称和显存 (wmic可能输出 AdapterRAM, Name 或 Name, AdapterRAM)
                parts = re.split(r'\s{2,}', line)
                if len(parts) >= 2:
                    # 尝试找出哪个是名称，哪个是显存
                    name = None
                    vram_str = None
                    for part in parts:
                        part = part.strip()
                        if part.isdigit():
                            vram_str = part
                        else:
                            name = part
                    
                    if name:
                        # 检查是否已存在（避免重复）
                        if name in existing_gpu_names:
                            continue
                        # 只识别 AMD 显卡，排除 NVIDIA
                        if "AMD" in name.upper() and "NVIDIA" not in name.upper():
                            # AdapterRAM单位是字节，转GB
                            vram = int(vram_str) / (1024**3) if vram_str and vram_str.isdigit() else 2
                            gpu_list.append({
                                "brand": "AMD",
                                "index": amd_index,
                                "name": name,
                                "vram": f"{vram:.0f}"
                            })
                            amd_index += 1
        except Exception as e:
            print(f"检测AMD显卡失败: {e}")
        return gpu_list
    
    def detect_nvidia_gpus_windows(self, existing_gpu_names=None):
        """在Windows系统中通过wmic检测NVIDIA显卡"""
        if existing_gpu_names is None:
            existing_gpu_names = []
        
        gpu_list = []
        try:
            result = subprocess.check_output(
                ["wmic", "path", "win32_VideoController", "get", "Name,AdapterRAM"],
                encoding="utf-8", errors="ignore",
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            lines = result.strip().split("\n")[1:]  # 跳过表头
            nvidia_index = 0
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # 解析显卡名称和显存
                parts = re.split(r'\s{2,}', line)
                if len(parts) >= 2:
                    # 尝试找出哪个是名称，哪个是显存
                    name = None
                    vram_str = None
                    for part in parts:
                        part = part.strip()
                        if part.isdigit():
                            vram_str = part
                        else:
                            name = part
                    
                    if name:
                        # 检查是否已存在（避免重复）
                        if name in existing_gpu_names:
                            continue
                        # 只识别 NVIDIA 显卡
                        if "NVIDIA" in name.upper():
                            # AdapterRAM单位是字节，转GB
                            vram = int(vram_str) / (1024**3) if vram_str and vram_str.isdigit() else 2
                            gpu_list.append({
                                "brand": "NVIDIA",
                                "index": nvidia_index,
                                "name": name,
                                "vram": f"{vram:.0f}"
                            })
                            nvidia_index += 1
        except Exception as e:
            print(f"检测NVIDIA显卡失败: {e}")
        return gpu_list
    
    def detect_intel_gpus_windows(self, existing_gpu_names=None):
        """在Windows系统中检测英特尔核显"""
        if existing_gpu_names is None:
            existing_gpu_names = []
        
        gpu_list = []
        try:
            result = subprocess.check_output(
                ["wmic", "path", "win32_VideoController", "get", "Name,AdapterRAM"],
                encoding="utf-8", errors="ignore",
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            lines = result.strip().split("\n")[1:]  # 跳过表头
            intel_index = 0
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # 解析显卡名称和显存 (wmic可能输出 AdapterRAM, Name 或 Name, AdapterRAM)
                parts = re.split(r'\s{2,}', line)
                if len(parts) >= 2:
                    # 尝试找出哪个是名称，哪个是显存
                    name = None
                    vram_str = None
                    for part in parts:
                        part = part.strip()
                        if part.isdigit():
                            vram_str = part
                        else:
                            name = part
                    
                    if name:
                        # 检查是否已存在（避免重复）
                        if name in existing_gpu_names:
                            continue
                        # 只识别英特尔核显
                        if "INTEL" in name.upper():
                            # AdapterRAM单位是字节，转GB
                            vram = int(vram_str) / (1024**3) if vram_str and vram_str.isdigit() else 2
                            gpu_list.append({
                                "brand": "Intel",
                                "index": intel_index,
                                "name": name,
                                "vram": f"{vram:.0f}"
                            })
                            intel_index += 1
        except Exception as e:
            print(f"检测英特尔核显失败: {e}")
        return gpu_list
    
    def get_gpu_info(self):
        """
        获取系统中所有GPU信息，区分NVIDIA/AMD/Intel显卡
        返回格式：[{"brand": "NVIDIA/AMD/Intel/UNKNOWN", "index": 0, "name": "显卡名称", "vram": "显存大小(GB)"}]
        """
        gpu_list = []
        existing_names = []
        
        # 1. 优先通过torch识别GPU (NVIDIA)
        try:
            if torch and torch.cuda.is_available():
                for i in range(torch.cuda.device_count()):
                    try:
                        gpu_name = torch.cuda.get_device_name(i)
                        vram = torch.cuda.get_device_properties(i).total_memory / (1024**3)
                        gpu_list.append({
                            "brand": "NVIDIA",
                            "index": i,
                            "name": gpu_name,
                            "vram": f"{vram:.0f}"
                        })
                        existing_names.append(gpu_name)
                    except Exception as e:
                        print(f"检测NVIDIA显卡{i}失败: {e}")
        except Exception as e:
            print(f"检测NVIDIA显卡时出错: {e}")
        
        # 2. 通过wmic检测NVIDIA显卡 (当torch无法识别时备用)
        if platform.system() == "Windows":
            nvidia_gpus = self.detect_nvidia_gpus_windows(existing_names)
            gpu_list.extend(nvidia_gpus)
            for gpu in nvidia_gpus:
                existing_names.append(gpu["name"])
        
        # 3. 尝试识别AMD显卡（Windows系统）
        if platform.system() == "Windows":
            amd_gpus = self.detect_amd_gpus_windows(existing_names)
            gpu_list.extend(amd_gpus)
            for gpu in amd_gpus:
                existing_names.append(gpu["name"])
        
        # 4. 尝试识别英特尔核显（Windows系统）
        if platform.system() == "Windows":
            intel_gpus = self.detect_intel_gpus_windows(existing_names)
            gpu_list.extend(intel_gpus)
            for gpu in intel_gpus:
                existing_names.append(gpu["name"])
        
        # 5. 兜底逻辑：未检测到任何GPU时，提供模拟数据
        if not gpu_list:
            gpu_list = [
                {"brand": "Intel", "index": 0, "name": "Intel(R) UHD Graphics", "vram": "2"},
                {"brand": "Intel", "index": 1, "name": "Intel(R) Iris(R) Xe Graphics", "vram": "2"},
            ]
        
        return gpu_list
    
    def detect_available_engines(self):
        """检测系统可用的生成引擎"""
        engine_options = []
        gpu_info = self.get_gpu_info()
        
        for gpu in gpu_info:
            brand = gpu["brand"]
            idx = gpu["index"]
            name = gpu["name"]
            vram = gpu["vram"]
            
            if brand == "NVIDIA":
                # NVIDIA显卡：CUDA、TensorRT、DML
                engine_options.append(f"CUDA GPU {idx}: {name} ({vram} GB)")
                engine_options.append(f"TensorRT GPU {idx}: {name} ({vram} GB)")
                engine_options.append(f"DML GPU {idx}: {name} ({vram} GB)")
            elif brand == "AMD":
                # AMD显卡：DML、ZLUDA
                engine_options.append(f"DML GPU {idx}: {name} ({vram} GB)")
                # ZLUDA通常只显示GPU 0，显存取共享显存（模拟7GB）
                if idx == 0:
                    engine_options.append(f"ZLUDA GPU {idx}: {name} (7 GB)")
            elif brand == "Intel":
                # Intel核显：DML
                engine_options.append(f"DML GPU {idx}: {name} ({vram} GB)")
        
        # 最后添加CPU选项
        engine_options.append("CPU")
        
        # 去重逻辑
        engine_options = list(dict.fromkeys(engine_options))
        
        return engine_options
    
    def show_settings(self):
        """显示设置页面"""
        # 隐藏所有页面
        self.advanced_frame.pack_forget()
        self.terminal_frame.pack_forget()
        # 显示设置页面
        self.settings_frame.pack(fill=tk.BOTH, expand=True)
    
    def show_advanced_settings(self):
        """显示高级设置页面"""
        # 隐藏所有页面
        self.settings_frame.pack_forget()
        self.terminal_frame.pack_forget()
        # 显示高级设置页面
        self.advanced_frame.pack(fill=tk.BOTH, expand=True)
    
    def show_terminal(self):
        """显示终端面板"""
        # 隐藏所有页面
        self.settings_frame.pack_forget()
        self.advanced_frame.pack_forget()
        # 显示终端面板
        self.terminal_frame.pack(fill=tk.BOTH, expand=True)
    
    def update_status(self):
        """更新状态栏状态"""
        if self.server_process is not None and self.server_process.poll() is None:
            self.status_label.configure(text="运行中", text_color="#4ec9b0")
        else:
            self.status_label.configure(text="未运行", text_color="#ff4757")
    
    def get_engine_from_settings(self):
        """从 gui_settings.json 读取生成引擎设置"""
        settings_file = os.path.join(os.getcwd(), "gui_settings.json")
        default_engine = "CPU"
        
        if os.path.exists(settings_file):
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                # 尝试从不同的键中读取
                if "生成引擎" in settings:
                    return settings["生成引擎"]
                elif "engine" in settings:
                    return settings["engine"]
            except Exception:
                pass
        
        return default_engine
    
    def start_server(self):
        """启动Flask服务器"""
        try:
            if self.server_process is not None and self.server_process.poll() is None:
                self.root.after(0, lambda: print("服务器已经在运行中..."))
                return
            
            print("正在启动服务器...")
            
            # 获取当前脚本路径
            if getattr(sys, 'frozen', False):
                # 打包成exe后的路径
                script_path = os.path.abspath(sys.executable)
                project_dir = os.path.dirname(script_path)
            else:
                # 正常Python脚本路径
                script_path = os.path.abspath(__file__)
                project_dir = os.path.dirname(script_path)
            
            print(f"项目目录: {project_dir}")
            
            # 获取生成引擎设置
            engine = self.get_engine_from_settings()
            print(f"读取到的生成引擎: {engine}")
            
            # 根据引擎选择虚拟环境
            python_exe = None
            
            if "CUDA" in engine or "TensorRT" in engine or "ZLUDA" in engine:
                # NVIDIA显卡使用venv_cuda
                venv_cuda = os.path.join(project_dir, "venv_cuda")
                if os.path.exists(venv_cuda):
                    python_exe = os.path.join(venv_cuda, "Scripts", "python.exe")
                    print(f"使用虚拟环境: {venv_cuda}")
            elif "DML" in engine:
                # AMD/Intel显卡使用venv_dml
                venv_dml = os.path.join(project_dir, "venv_dml")
                if os.path.exists(venv_dml):
                    python_exe = os.path.join(venv_dml, "Scripts", "python.exe")
                    print(f"使用虚拟环境: {venv_dml}")
            
            # 如果没有找到对应的虚拟环境，尝试查找系统Python
            if not python_exe:
                # 尝试查找系统Python
                import shutil
                python_exe = shutil.which('python.exe')
                if python_exe:
                    print(f"使用系统Python环境: {python_exe}")
                else:
                    # 如果还是找不到，使用当前Python解释器
                    python_exe = sys.executable
                    print(f"使用当前Python环境: {python_exe}")
            
            # 使用pythonw.exe来完全分离进程，避免与GUI进程冲突
            if python_exe.endswith('python.exe'):
                pythonw_exe = python_exe.replace('python.exe', 'pythonw.exe')
                if os.path.exists(pythonw_exe):
                    python_exe = pythonw_exe
                    print(f"使用pythonw.exe: {python_exe}")
            
            # 确保app.py存在
            app_py_path = os.path.join(project_dir, "app.py")
            if not os.path.exists(app_py_path):
                error_msg = f"错误：app.py文件不存在！路径: {app_py_path}"
                print(error_msg)
                self.append_to_terminal(error_msg + "\n")
                self.root.after(0, self.update_status)
                return
            
            print(f"启动命令: {python_exe} {app_py_path} run")
            
            # 使用独立的方式启动Flask进程
            self.server_process = subprocess.Popen(
                [python_exe, app_py_path, "run"],
                cwd=project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS | subprocess.BELOW_NORMAL_PRIORITY_CLASS if os.name == 'nt' else 0
            )
            print("服务器已启动")
            
            # 启动线程读取输出
            output_thread = threading.Thread(target=self.read_server_output, daemon=True)
            output_thread.start()
            
            # 更新状态栏状态
            self.root.after(0, self.update_status)
        except Exception as e:
            error_msg = f"启动服务器失败: {e}"
            print(error_msg)
            self.append_to_terminal(error_msg + "\n")
            self.root.after(0, self.update_status)
    
    def stop_server(self):
        """停止Flask服务器"""
        try:
            if self.server_process is None or self.server_process.poll() is not None:
                self.append_to_terminal("服务器未在运行...\n")
                return
            
            self.append_to_terminal("正在停止服务器...\n")
            
            # 1. 首先尝试直接终止已知的server_process
            try:
                if self.server_process.poll() is None:
                    self.server_process.kill()
                    self.append_to_terminal("已终止服务器进程\n")
            except Exception as e:
                self.append_to_terminal(f"终止服务器进程时出错: {e}\n")
            
            # 2. Windows系统使用taskkill强制终止进程（作为备用方案）
            if os.name == 'nt':
                try:
                    # 查找并终止所有占用5000端口的进程
                    netstat_result = subprocess.run(
                        ['netstat', '-ano', '-p', 'tcp'],
                        capture_output=True,
                        text=True,
                        timeout=3  # 减少超时时间
                    )
                    for line in netstat_result.stdout.splitlines():
                        if ':5000' in line and ('LISTENING' in line or 'LISTEN' in line):
                            parts = line.split()
                            if len(parts) > 0:
                                pid = parts[-1]
                                try:
                                    subprocess.run(
                                        ['taskkill', '/F', '/PID', pid],
                                        capture_output=True,
                                        timeout=3
                                    )
                                    self.append_to_terminal(f"已终止端口5000进程 PID: {pid}\n")
                                except Exception as e:
                                    pass
                except subprocess.TimeoutExpired:
                    # 捕获netstat超时异常，继续执行其他操作
                    self.append_to_terminal("端口检查超时，已尝试直接终止进程\n")
                except Exception as e:
                    self.append_to_terminal(f"端口检查出错: {e}\n")
            else:
                # 非Windows系统使用标准方式
                try:
                    self.server_process.terminate()
                    try:
                        self.server_process.wait(timeout=3)
                        self.append_to_terminal("服务器已停止\n")
                    except subprocess.TimeoutExpired:
                        self.server_process.kill()
                        self.append_to_terminal("服务器已强制停止\n")
                except Exception as e:
                    self.append_to_terminal(f"终止服务器时出错: {e}\n")
            
            # 更新状态栏状态
            self.root.after(0, self.update_status)
            self.append_to_terminal("服务器停止操作完成\n")
        except Exception as e:
            self.append_to_terminal(f"停止服务器失败: {e}\n")
            self.root.after(0, self.update_status)
    
    def read_server_output(self):
        """读取服务器输出"""
        if self.server_process:
            for line in iter(self.server_process.stdout.readline, ''):
                # 只将重要信息添加到队列（启动消息、错误消息等）
                # 过滤掉大量的调试输出，避免GUI阻塞
                if "Running on http://" in line or "ERROR" in line.upper() or "Exception" in line:
                    self.queue.put(line)
                # 其他输出直接丢弃，避免GUI卡顿
    
    def check_queue(self):
        """检查队列是否有新内容"""
        try:
            # 从队列读取所有内容到缓冲区
            lines_to_add = []
            while not self.queue.empty():
                try:
                    line = self.queue.get_nowait()
                    lines_to_add.append(line)
                    
                    # 检测服务器启动成功的消息，自动打开浏览器
                    if "Running on http://127.0.0.1:5000" in line:
                        self.root.after(0, lambda: self.append_to_terminal("服务器启动成功，正在打开浏览器...\n"))
                        self.root.after(1000, lambda: webbrowser.open("http://127.0.0.1:5000"))
                except queue.Empty:
                    break
            
            # 如果有新内容，批量添加到缓冲区
            if lines_to_add:
                with self.buffer_lock:
                    self.output_buffer.extend(lines_to_add)
                
                # 安排一次GUI更新
                self.schedule_flush()
                
        except Exception as e:
            print(f"队列检查错误: {e}")
        
        # 降低更新频率到500ms
        self.root.after(500, self.check_queue)
    
    def schedule_flush(self):
        """安排缓冲区刷新，避免频繁调用"""
        if not self.flush_pending:
            self.flush_pending = True
            self.root.after(50, self.flush_buffer)
    
    def flush_buffer(self):
        """将缓冲区内容批量刷新到终端"""
        self.flush_pending = False
        try:
            with self.buffer_lock:
                if not self.output_buffer:
                    return
                # 取出缓冲区内容
                content = ''.join(self.output_buffer)
                self.output_buffer = []
            
            # 一次性添加到终端
            self._append_to_terminal_internal(content)
        except Exception as e:
            print(f"刷新缓冲区错误: {e}")
    
    def _append_to_terminal_internal(self, text):
        """内部函数：向终端面板添加文本（实际GUI操作）"""
        try:
            if hasattr(self, 'terminal_text'):
                # 限制终端文本长度
                max_lines = 5000
                current_lines = int(self.terminal_text.index('end-1c').split('.')[0])
                
                if current_lines > max_lines:
                    delete_lines = current_lines - max_lines
                    self.terminal_text.config(state=tk.NORMAL)
                    self.terminal_text.delete(f"1.0", f"{delete_lines}.0")
                
                # 添加新文本
                self.terminal_text.config(state=tk.NORMAL)
                self.terminal_text.insert(tk.END, text)
                # 只在有换行符时才滚动
                if "\n" in text:
                    self.terminal_text.see(tk.END)
                self.terminal_text.config(state=tk.DISABLED)
        except Exception as e:
            print(f"终端更新错误: {e}")
    
    def append_to_terminal(self, text):
        """向终端面板添加文本（对外接口）"""
        try:
            with self.buffer_lock:
                self.output_buffer.append(text)
            # 安排刷新
            self.schedule_flush()
        except Exception as e:
            print(f"添加到终端错误: {e}")
    
    def generate_diagnostic(self):
        """生成诊断包"""
        self.append_to_terminal("正在生成诊断包...\n")
        
        # 创建诊断包文件夹
        diag_dir = "diagnostics"
        if not os.path.exists(diag_dir):
            os.makedirs(diag_dir)
        
        # 生成诊断文件
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        diag_file = os.path.join(diag_dir, f"diagnostic_{timestamp}.txt")
        
        with open(diag_file, "w", encoding="utf-8") as f:
            f.write(f"诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Python版本: {sys.version}\n")
            f.write(f"操作系统: {sys.platform}\n")
            f.write(f"当前目录: {os.getcwd()}\n")
            f.write("\n服务器状态: ")
            if self.server_process and self.server_process.poll() is None:
                f.write("运行中\n")
            else:
                f.write("未运行\n")
        
        self.append_to_terminal(f"诊断包已生成: {diag_file}\n")
    
    def show_install_dialog(self):
        """显示安装选择对话框"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("选择安装类型")
        dialog.geometry("450x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 标题
        title_label = ctk.CTkLabel(dialog, text="选择要安装的环境", 
                                  text_color="white", font= ("Arial", 14, "bold"))
        title_label.pack(pady=20)
        
        # 选项变量
        install_var = ctk.StringVar(value="cuda")
        
        # 安装选项
        options_frame = ctk.CTkFrame(dialog, fg_color="#2c2c2c")
        options_frame.pack(fill=tk.X, padx=30, pady=10)
        
        cuda_radio = ctk.CTkRadioButton(options_frame, text="仅安装 CUDA (NVIDIA 显卡)", 
                                         variable=install_var, value="cuda")
        cuda_radio.pack(pady=10, padx=20, anchor=tk.W)
        
        dml_radio = ctk.CTkRadioButton(options_frame, text="仅安装 DML (AMD/Intel 显卡)", 
                                        variable=install_var, value="dml")
        dml_radio.pack(pady=10, padx=20, anchor=tk.W)
        
        all_radio = ctk.CTkRadioButton(options_frame, text="全部安装 (CUDA + DML)", 
                                       variable=install_var, value="all")
        all_radio.pack(pady=10, padx=20, anchor=tk.W)
        
        # 按钮区域
        button_frame = ctk.CTkFrame(dialog, fg_color="#2c2c2c")
        button_frame.pack(fill=tk.X, padx=30, pady=20)
        
        cancel_button = ctk.CTkButton(button_frame, text="取消", 
                                     fg_color="#3c3c3c", hover_color="#4a4a4a",
                                     text_color="white", font= ("Arial", 10), 
                                     width=100, command=dialog.destroy)
        cancel_button.pack(side=tk.RIGHT, padx=10)
        
        def on_install():
            dialog.destroy()
            self.start_installation(install_var.get())
        
        install_button = ctk.CTkButton(button_frame, text="开始安装", 
                                      fg_color="#4ec9b0", hover_color="#3db89f",
                                      text_color="white", font= ("Arial", 10), 
                                      width=100, command=on_install)
        install_button.pack(side=tk.RIGHT, padx=10)
    
    def start_installation(self, install_type):
        """开始安装进程"""
        self.show_terminal()
        self.append_to_terminal("="*50 + "\n")
        self.append_to_terminal(f"开始安装 {install_type.upper()} 环境...\n")
        self.append_to_terminal("="*50 + "\n")
        
        # 在新线程中执行安装
        threading.Thread(target=self.install_environment, args=(install_type,), daemon=True).start()
    
    def run_command_streaming(self, cmd, cwd=None):
        """运行命令并实时输出到终端"""
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=cwd,
            bufsize=1,
            universal_newlines=True,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        for line in iter(process.stdout.readline, ''):
            self.append_to_terminal(line)
        
        process.stdout.close()
        return process.wait()
    
    def install_environment(self, install_type):
        """执行环境安装"""
        try:
            project_dir = os.getcwd()
            
            # 创建虚拟环境和安装依赖
            if install_type in ["cuda", "all"]:
                self.install_venv_cuda(project_dir)
            
            if install_type in ["dml", "all"]:
                self.install_venv_dml(project_dir)
            
            self.append_to_terminal("\n" + "="*50 + "\n")
            self.append_to_terminal("安装完成！\n")
            self.append_to_terminal("="*50 + "\n")
            
        except Exception as e:
            self.append_to_terminal(f"\n安装失败: {e}\n")
    
    def install_venv_cuda(self, project_dir):
        """安装 CUDA 虚拟环境"""
        venv_path = os.path.join(project_dir, "venv_cuda")
        self.append_to_terminal(f"\n[CUDA] 创建虚拟环境: {venv_path}\n")
        
        # 创建虚拟环境
        self.run_command_streaming([sys.executable, "-m", "venv", venv_path], cwd=project_dir)
        
        # 确定 pip 路径
        python_path = os.path.join(venv_path, "Scripts", "python.exe")
        
        # 升级 pip (使用 python -m pip 的方式)
        self.append_to_terminal("\n[CUDA] 升级 pip...\n")
        self.run_command_streaming([python_path, "-m", "pip", "install", "--upgrade", "pip", "--progress-bar=on"], cwd=project_dir)
        
        # 安装 PyTorch with CUDA
        self.append_to_terminal("\n[CUDA] 安装 PyTorch (CUDA)...\n")
        self.run_command_streaming([python_path, "-m", "pip", "install", "torch", "torchvision", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cu121", "--progress-bar=on"], cwd=project_dir)
        
        # 安装其他依赖
        self.append_to_terminal("\n[CUDA] 安装其他依赖...\n")
        requirements = [
            "flask", "customtkinter", "pillow", "numpy", "requests",
            "safetensors", "transformers", "accelerate", "diffusers"
        ]
        self.run_command_streaming([python_path, "-m", "pip", "install"] + requirements + ["--progress-bar=on"], cwd=project_dir)
        
        self.append_to_terminal("\n[CUDA] 安装完成！\n")
    
    def install_venv_dml(self, project_dir):
        """安装 DML 虚拟环境"""
        venv_path = os.path.join(project_dir, "venv_dml")
        self.append_to_terminal(f"\n[DML] 创建虚拟环境: {venv_path}\n")
        
        # 创建虚拟环境
        self.run_command_streaming([sys.executable, "-m", "venv", venv_path], cwd=project_dir)
        
        # 确定 python 路径
        python_path = os.path.join(venv_path, "Scripts", "python.exe")
        
        # 升级 pip (使用 python -m pip 的方式)
        self.append_to_terminal("\n[DML] 升级 pip...\n")
        self.run_command_streaming([python_path, "-m", "pip", "install", "--upgrade", "pip", "--progress-bar=on"], cwd=project_dir)
        
        # 安装 PyTorch (CPU 版本) - 使用与 torch-directml 兼容的版本
        self.append_to_terminal("\n[DML] 安装 PyTorch (CPU)...\n")
        self.run_command_streaming([python_path, "-m", "pip", "install", "torch==2.0.1", "torchvision==0.15.2", "torchaudio==2.0.2", "--index-url", "https://download.pytorch.org/whl/cpu", "--progress-bar=on"], cwd=project_dir)
        
        # 安装 torch-directml
        self.append_to_terminal("\n[DML] 安装 torch-directml...\n")
        self.run_command_streaming([python_path, "-m", "pip", "install", "torch-directml", "--progress-bar=on"], cwd=project_dir)
        
        # 安装其他依赖
        self.append_to_terminal("\n[DML] 安装其他依赖...\n")
        requirements = [
            "flask", "customtkinter", "pillow", "numpy", "requests",
            "safetensors", "transformers", "accelerate", "diffusers"
        ]
        self.run_command_streaming([python_path, "-m", "pip", "install"] + requirements + ["--progress-bar=on"], cwd=project_dir)
        
        self.append_to_terminal("\n[DML] 安装完成！\n")
    
    def on_close(self):
        """窗口关闭事件"""
        # 停止服务器
        self.stop_server()
        # 关闭窗口
        self.root.destroy()

if __name__ == '__main__':
    # 直接运行，启动GUI
    root = ctk.CTk()
    app = FlaskServerGUI(root)
    root.mainloop()