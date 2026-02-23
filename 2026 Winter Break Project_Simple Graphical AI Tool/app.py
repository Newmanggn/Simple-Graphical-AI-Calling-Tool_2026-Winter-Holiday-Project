
import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import sys
import os
import glob
import threading
import queue
import webbrowser
import platform
import re
from datetime import datetime

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
    
    def get_gpu_info(self):
        """
        获取系统中所有GPU信息，区分NVIDIA/AMD显卡
        返回格式：[{"brand": "NVIDIA/AMD/UNKNOWN", "index": 0, "name": "显卡名称", "vram": "显存大小(GB)"}]
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
        
        # 4. 兜底逻辑：未检测到任何GPU时，提供模拟AMD数据
        if not gpu_list:
            gpu_list = [
                {"brand": "AMD", "index": 0, "name": "AMD Radeon(TM) Graphics", "vram": "2"},
                {"brand": "AMD", "index": 1, "name": "AMD Radeon(TM) Graphics", "vram": "2"},
                {"brand": "AMD", "index": 2, "name": "AMD Radeon(TM) Graphics", "vram": "2"},
                {"brand": "AMD", "index": 3, "name": "AMD Radeon(TM) Graphics", "vram": "2"},
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
    
    def start_server(self):
        """启动Flask服务器"""
        try:
            if self.server_process is not None and self.server_process.poll() is None:
                self.root.after(0, lambda: print("服务器已经在运行中..."))
                return
            
            print("正在启动服务器...")
            
            # 获取当前脚本路径
            script_path = os.path.abspath(__file__)
            project_dir = os.path.dirname(script_path)
            
            # 使用pythonw.exe来完全分离进程，避免与GUI进程冲突
            python_exe = sys.executable
            if python_exe.endswith('python.exe'):
                pythonw_exe = python_exe.replace('python.exe', 'pythonw.exe')
                if os.path.exists(pythonw_exe):
                    python_exe = pythonw_exe
            
            # 使用独立的方式启动Flask进程
            self.server_process = subprocess.Popen(
                [python_exe, script_path, "run"],
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
            print(f"启动服务器失败: {e}")
            self.root.after(0, self.update_status)
    
    def stop_server(self):
        """停止Flask服务器"""
        try:
            if self.server_process is None or self.server_process.poll() is not None:
                self.append_to_terminal("服务器未在运行...\n")
                return
            
            self.append_to_terminal("正在停止服务器...\n")
            
            # Windows系统使用taskkill强制终止进程
            if os.name == 'nt':
                try:
                    # 查找并终止所有占用5000端口的进程
                    netstat_result = subprocess.run(
                        ['netstat', '-ano', '-p', 'tcp'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    for line in netstat_result.stdout.splitlines():
                        if ':5000' in line and ('LISTENING' in line or 'LISTEN' in line):
                            parts = line.split()
                            pid = parts[-1]
                            try:
                                subprocess.run(
                                    ['taskkill', '/F', '/PID', pid],
                                    capture_output=True,
                                    timeout=5
                                )
                                self.append_to_terminal(f"已终止进程 PID: {pid}\n")
                            except Exception as e:
                                pass
                    
                    # 同时终止已知的server_process
                    if self.server_process.poll() is None:
                        try:
                            self.server_process.kill()
                        except:
                            pass
                    
                    self.append_to_terminal("服务器已停止\n")
                except Exception as e:
                    self.append_to_terminal(f"停止服务器失败: {e}\n")
            else:
                # 非Windows系统使用标准方式
                self.server_process.terminate()
                try:
                    self.server_process.wait(timeout=5)
                    self.append_to_terminal("服务器已停止\n")
                except subprocess.TimeoutExpired:
                    self.server_process.kill()
                    self.append_to_terminal("服务器已强制停止\n")
            
            # 更新状态栏状态
            self.root.after(0, self.update_status)
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

import os
import threading
import concurrent.futures
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"

# Flask应用代码
from flask import Flask, render_template, jsonify, request, send_from_directory
import importlib.util
import json
import zipfile
import io
import uuid
import torch

# 创建线程池执行器，用于异步执行模块
# 最大工作线程数设置为2，避免过多线程占用资源
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

# 全局停止标志，用于停止正在执行的模块
stop_execution_flag = False
# 存储正在执行的future对象，用于取消
ongoing_futures = set()

app = Flask(__name__)

# 模块文件夹路径
DEFAULT_MODULES_DIR = 'default_modules'
CUSTOM_MODULES_DIR = 'custom_modules'

# 存储加载的模块
loaded_modules = {}

# 全局张量缓存
tensor_cache = {}

# 全局模型缓存
model_cache = {}

# 解析模块文件的注释参数
def parse_module_params(file_path):
    params = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # 读取所有注释行，直到遇到非注释行
            for line in f:
                line = line.strip()
                if not line.startswith('#'):
                    break
                
                # 处理普通参数
                if '=' in line and not line.startswith('#variables_name=') and not line.startswith('#output_name='):
                    key_value = line[1:].split('=', 1)
                    if len(key_value) == 2:
                        key = key_value[0]
                        value = key_value[1]
                        # 转换布尔值
                        if value.lower() in ['t', 'true']:
                            value = True
                        elif value.lower() in ['f', 'false']:
                            value = False
                        # 转换数字
                        elif value.isdigit():
                            value = int(value)
                        params[key] = value
                # 处理变量名
                elif line.startswith('#variables_name='):
                    params['variables_name'] = line[16:]
                # 处理输出端口名称
                elif line.startswith('#output_name='):
                    params['output_name'] = line[13:]
    except Exception as e:
        print(f"解析模块文件失败: {e}")
    return params

# 加载模块
def load_modules():
    loaded_modules.clear()
    
    # 加载默认模块
    if os.path.exists(DEFAULT_MODULES_DIR):
        for filename in os.listdir(DEFAULT_MODULES_DIR):
            if filename.endswith('.py'):
                file_path = os.path.join(DEFAULT_MODULES_DIR, filename)
                module_name = os.path.splitext(filename)[0]
                params = parse_module_params(file_path)
                params['source'] = 'default'  # 添加来源信息
                loaded_modules[module_name] = params
    
    # 加载自定义模块
    if os.path.exists(CUSTOM_MODULES_DIR):
        for filename in os.listdir(CUSTOM_MODULES_DIR):
            if filename.endswith('.py'):
                file_path = os.path.join(CUSTOM_MODULES_DIR, filename)
                module_name = os.path.splitext(filename)[0]
                params = parse_module_params(file_path)
                params['source'] = 'custom'  # 添加来源信息
                loaded_modules[module_name] = params

# 初始化时加载模块
load_modules()

@app.route('/')
def index():
    return render_template('main.html')

@app.route('/api/modules')
def get_modules():
    # 重新加载模块，确保包含最新的自定义模块
    load_modules()
    return jsonify(loaded_modules)

@app.route('/api/refresh_modules')
def refresh_modules():
    load_modules()
    return jsonify(loaded_modules)

def _execute_module_async(module_name, input_values, settings):
    """异步执行模块的内部函数"""
    try:
        # 确定模块文件路径
        module_path = None
        if os.path.exists(os.path.join(DEFAULT_MODULES_DIR, f'{module_name}.py')):
            module_path = os.path.join(DEFAULT_MODULES_DIR, f'{module_name}.py')
        elif os.path.exists(os.path.join(CUSTOM_MODULES_DIR, f'{module_name}.py')):
            module_path = os.path.join(CUSTOM_MODULES_DIR, f'{module_name}.py')
        
        if not module_path:
            return {'error': f'模块 {module_name} 不存在'}
        
        # 解析模块参数
        module_params = parse_module_params(module_path)
        input_quantity = module_params.get('input_quantity', 0)
        variable_quantity = module_params.get('variable_quantity', 0)
        output_quantity = module_params.get('output_quantity', 0)
        time_late = module_params.get('time_late', 0)
        
        # 准备输入变量
        # 前input_quantity个变量来自输入端口
        # 剩余变量和默认值来自设置界面
        prepared_inputs = []
        
        # 获取变量名列表
        variable_names = []
        if 'variables_name' in module_params:
            variable_names = [name.strip() for name in module_params['variables_name'].split(',')]
        
        # 处理输入端口变量
        for i in range(input_quantity):
            if i < len(input_values):
                val = input_values[i]
                # 如果是张量引用，从缓存中取出
                if isinstance(val, str) and val.startswith('TENSOR_REF:'):
                    tensor_id = val[len('TENSOR_REF:'):]
                    if tensor_id in tensor_cache:
                        val = tensor_cache[tensor_id]
                # 如果是图像引用，从缓存中取出
                elif isinstance(val, str) and val.startswith('IMAGE_REF:'):
                    image_id = val[len('IMAGE_REF:'):]
                    if image_id in tensor_cache:
                        val = tensor_cache[image_id]
                # 如果是图像列表引用，从缓存中取出
                elif isinstance(val, str) and val.startswith('IMAGE_LIST_REF:'):
                    image_list_id = val[len('IMAGE_LIST_REF:'):]
                    if image_list_id in tensor_cache:
                        val = tensor_cache[image_list_id]
                prepared_inputs.append(val)
            else:
                # 从设置中获取默认值
                var_name = variable_names[i] if i < len(variable_names) else f'var{i}'
                # 对于判断模块，设置默认值为1
                if module_name == '判断' and var_name == '判断':
                    prepared_inputs.append(settings.get(var_name, 1))
                else:
                    prepared_inputs.append(settings.get(var_name))
        
        # 处理剩余变量（如果有）
        for i in range(input_quantity, variable_quantity):
            var_name = variable_names[i] if i < len(variable_names) else f'var{i}'
            # 对于判断模块，设置默认值为1
            if module_name == '判断' and var_name == '判断':
                prepared_inputs.append(settings.get(var_name, 1))
            else:
                prepared_inputs.append(settings.get(var_name))
        
        print(f'准备好的输入变量: {prepared_inputs}')
        print(f'接收到的settings: {settings}')
        
        # 加载模块
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 自动发现模块中的执行函数
        # 查找模块中定义的所有函数
        module_functions = []
        for name in dir(module):
            # 排除内置函数和私有函数
            if not name.startswith('_') and callable(getattr(module, name)):
                module_functions.append(name)
        
        # 尝试调用模块中的函数
        result = None
        executed_function = None
        
        # 创建取消令牌函数，检查全局停止标志
        def cancel_token():
            global stop_execution_flag
            return stop_execution_flag
        
        # 优先调用主执行函数
        main_functions = ['execute', 'run', 'process']
        for func_name in main_functions:
            if func_name in module_functions:
                try:
                    # 对于调用模块和加载图像模块，额外传递settings参数
                    if module_name == '调用模块' or module_name == '加载图像模块':
                        # 检查函数是否接受settings参数
                        import inspect
                        func = getattr(module, func_name)
                        sig = inspect.signature(func)
                        
                        if module_name == '调用模块' and 'cancel_token' in sig.parameters:
                            result = getattr(module, func_name)(*prepared_inputs, settings, cancel_token=cancel_token)
                        elif 'settings' in sig.parameters:
                            result = getattr(module, func_name)(*prepared_inputs, settings)
                        else:
                            result = getattr(module, func_name)(*prepared_inputs)
                    else:
                        result = getattr(module, func_name)(*prepared_inputs)
                    executed_function = func_name
                    break
                except Exception as e:
                    print(f'调用主函数 {func_name} 失败: {e}')
                    continue
        
        # 如果没有主执行函数，尝试调用模块中的第一个函数
        if result is None and module_functions:
            for func_name in module_functions:
                try:
                    # 对于调用模块和加载图像模块，额外传递settings参数
                    if module_name == '调用模块' or module_name == '加载图像模块':
                        # 检查函数是否接受settings参数
                        import inspect
                        func = getattr(module, func_name)
                        sig = inspect.signature(func)
                        
                        if module_name == '调用模块' and 'cancel_token' in sig.parameters:
                            result = getattr(module, func_name)(*prepared_inputs, settings, cancel_token=cancel_token)
                        elif 'settings' in sig.parameters:
                            result = getattr(module, func_name)(*prepared_inputs, settings)
                        else:
                            result = getattr(module, func_name)(*prepared_inputs)
                    else:
                        result = getattr(module, func_name)(*prepared_inputs)
                    executed_function = func_name
                    break
                except Exception as e:
                    print(f'调用函数 {func_name} 失败: {e}')
                    continue
        
        if result is None:
            return {'error': f'模块 {module_name} 没有可执行的函数'}
        
        # 处理返回值
        # 确保返回值是可迭代的
        if not isinstance(result, (list, tuple)):
            result = [result]
        
        # 处理张量和图像：将PyTorch张量和PIL图像存入缓存，返回引用
        processed_result = []
        for val in result:
            # 处理包含samples字段的字典（新Latent格式）
            if isinstance(val, dict) and "samples" in val and isinstance(val["samples"], torch.Tensor):
                tensor_id = str(uuid.uuid4())
                tensor_cache[tensor_id] = val
                processed_result.append(f'TENSOR_REF:{tensor_id}')
            # 处理原始张量格式（向后兼容）
            elif isinstance(val, torch.Tensor):
                tensor_id = str(uuid.uuid4())
                tensor_cache[tensor_id] = val
                processed_result.append(f'TENSOR_REF:{tensor_id}')
            elif val is not None:
                try:
                    from PIL import Image
                    if isinstance(val, Image.Image):
                        # 是PIL图像，存入缓存
                        image_id = str(uuid.uuid4())
                        tensor_cache[image_id] = val
                        processed_result.append(f'IMAGE_REF:{image_id}')
                    elif isinstance(val, list) and len(val) > 0 and isinstance(val[0], Image.Image):
                        # 是PIL图像列表，保存为列表引用
                        image_list_id = str(uuid.uuid4())
                        tensor_cache[image_list_id] = val
                        processed_result.append(f'IMAGE_LIST_REF:{image_list_id}')
                    else:
                        processed_result.append(val)
                except ImportError:
                    processed_result.append(val)
            else:
                processed_result.append(val)
        
        # 检查返回值数量
        expected_outputs = output_quantity
        if time_late == variable_quantity:
            expected_outputs = output_quantity + 1
        
        print(f'执行模块 {module_name} 成功，调用函数: {executed_function}')
        print(f'返回值: {result}, 处理后: {processed_result}, 预期输出数量: {expected_outputs}')
        
        # 返回执行结果
        return {
            'result': processed_result,
            'output_quantity': output_quantity,
            'time_late': time_late,
            'variable_quantity': variable_quantity
        }
                
    except Exception as e:
        print(f'执行模块时出错: {e}')
        return {'error': str(e)}

@app.route('/api/execute_module', methods=['POST'])
def execute_module():
    global stop_execution_flag
    try:
        data = request.json
        module_name = data.get('module_name')
        input_values = data.get('input_values', [])
        settings = data.get('settings', {})  # 获取设置界面的默认值
        
        # 重置停止标志（每次新请求开始时）
        stop_execution_flag = False
        
        # 使用线程池执行器异步执行模块
        future = executor.submit(_execute_module_async, module_name, input_values, settings)
        
        # 添加到正在执行的集合中
        ongoing_futures.add(future)
        
        try:
            # 等待执行完成并获取结果，支持检查停止标志
            while not future.done():
                if stop_execution_flag:
                    future.cancel()
                    print(f'模块执行被取消: {module_name}')
                    return jsonify({'error': '执行已被用户取消'}), 499
                import time
                time.sleep(0.1)
            
            result = future.result()
        finally:
            # 从正在执行的集合中移除
            try:
                ongoing_futures.remove(future)
            except:
                pass
        
        # 检查是否有错误
        if 'error' in result:
            return jsonify(result), 400 if '不存在' in result['error'] else 500
        
        # 返回执行结果
        return jsonify(result)
                
    except Exception as e:
        print(f'执行模块时出错: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/save_project', methods=['POST'])
def save_project():
    try:
        # 获取项目数据
        data = request.json
        project_data = data.get('project_data')
        
        if not project_data:
            return jsonify({'error': '项目数据为空'}), 400
        
        # 确保auto_save文件夹存在
        auto_save_dir = 'auto_save'
        if not os.path.exists(auto_save_dir):
            os.makedirs(auto_save_dir)
        
        # 生成文件名
        timestamp = datetime.now().isoformat()[:19].replace(':', '-').replace('T', '-')
        filename = f'ai_tool_project_{timestamp}.aiud'
        file_path = os.path.join(auto_save_dir, filename)
        
        # 创建zip文件
        with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加project.json文件
            zipf.writestr('project.json', json.dumps(project_data, indent=2, ensure_ascii=False))
            
            # 添加自定义模块文件夹
            used_custom_modules = project_data.get('usedCustomModules', [])
            for module_name in used_custom_modules:
                # 查找自定义模块文件
                module_file = os.path.join('custom_modules', f'{module_name}.py')
                if os.path.exists(module_file):
                    # 添加自定义模块文件到zip中
                    zipf.write(module_file, f'custom_modules/{module_name}.py')
        
        print(f'项目保存成功: {file_path}')
        return jsonify({'success': True, 'message': '项目保存成功', 'file_path': file_path})
                
    except Exception as e:
        print(f'保存项目时出错: {e}')
        return jsonify({'error': str(e)}), 500

# 提供静态文件服务，用于显示和下载生成的图像
@app.route('/output/&lt;path:filename&gt;')
def serve_output_file(filename):
    output_dir = 'output'
    # 确保output文件夹存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return send_from_directory(output_dir, filename)

@app.route('/api/get_image_base64', methods=['GET'])
def get_image_base64():
    """
    获取缓存中图像的base64数据
    """
    try:
        image_ref = request.args.get('image_ref', '')
        if not image_ref:
            return jsonify({'error': '缺少image_ref参数'}), 400
        
        print(f'获取图像base64: {image_ref}')
        
        if image_ref not in tensor_cache:
            return jsonify({'error': '图像引用不存在'}), 404
        
        image_data = tensor_cache[image_ref]
        
        from PIL import Image
        import io
        import base64
        
        images_to_convert = []
        if isinstance(image_data, list):
            images_to_convert = image_data
        elif isinstance(image_data, Image.Image):
            images_to_convert = [image_data]
        
        if not images_to_convert:
            return jsonify({'error': '没有有效的图像数据'}), 400
        
        # 只转换第一张图片（显示用）
        img = images_to_convert[0]
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        return jsonify({
            'success': True,
            'image_base64': f'data:image/png;base64,{img_str}',
            'image_count': len(images_to_convert)
        }), 200
        
    except Exception as e:
        print(f'获取图像base64失败: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_lmstudio_models', methods=['GET'])
def get_lmstudio_models():
    """
    获取LM Studio的模型列表
    通过后端代理来避免CORS错误
    """
    try:
        import requests
        
        # 从请求参数中获取LM Studio的主机地址
        host = request.args.get('host', 'http://localhost:1234')
        endpoint = '/v1/models'
        
        # 调用LM Studio API获取模型列表
        response = requests.get(f'{host}{endpoint}', timeout=10)
        
        if not response.ok:
            return jsonify({'error': f'调用LM Studio API失败: {response.status_code} - {response.text}'}), 400
        
        data = response.json()
        models = data.get('data', [])
        
        # 提取模型ID列表
        model_list = []
        for model in models:
            model_id = model.get('id') or model.get('name') or model.get('model')
            if model_id:
                model_list.append(model_id)
        
        return jsonify({'models': model_list}), 200
        
    except Exception as e:
        print(f'获取LM Studio模型列表失败: {e}')
        return jsonify({'error': f'获取模型列表失败: {str(e)}'}), 500

@app.route('/api/save_cache', methods=['POST'])
def save_cache():
    """
    保存界面缓存
    """
    try:
        # 获取缓存数据
        data = request.json
        cache_data = data.get('cache_data')
        
        if not cache_data:
            return jsonify({'error': '缓存数据为空'}), 400
        
        # 确保缓存文件夹存在
        cache_dir = os.path.join('auto_save', 'cache')
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        
        # 使用固定文件名
        cache_file = os.path.join(cache_dir, 'cache.json')
        
        # 保存缓存数据
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        
        print(f'缓存保存成功: {cache_file}')
        return jsonify({'success': True, 'message': '缓存保存成功', 'file_path': cache_file})
                
    except Exception as e:
        print(f'保存缓存失败: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/load_cache', methods=['GET'])
def load_cache():
    """
    加载最新的界面缓存
    """
    try:
        # 确保缓存文件夹存在
        cache_dir = os.path.join('auto_save', 'cache')
        if not os.path.exists(cache_dir):
            return jsonify({'error': '缓存文件夹不存在'}), 404
        
        # 使用固定文件名
        cache_file = os.path.join(cache_dir, 'cache.json')
        if not os.path.exists(cache_file):
            return jsonify({'error': '缓存文件不存在'}), 404
        
        # 读取缓存数据
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        print(f'缓存加载成功: {cache_file}')
        return jsonify({'success': True, 'cache_data': cache_data, 'file_path': cache_file})
                
    except Exception as e:
        print(f'加载缓存失败: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear_cache', methods=['POST'])
def clear_cache():
    """
    清除界面缓存
    """
    try:
        cache_dir = os.path.join('auto_save', 'cache')
        cache_file = os.path.join(cache_dir, 'cache.json')
        
        if os.path.exists(cache_file):
            os.remove(cache_file)
            print(f'缓存已清除: {cache_file}')
            return jsonify({'success': True, 'message': '缓存已清除'})
        else:
            print('缓存文件不存在，无需清除')
            return jsonify({'success': True, 'message': '缓存文件不存在'})
                
    except Exception as e:
        print(f'清除缓存失败: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/restart', methods=['POST'])
def restart_server():
    """
    重启服务器
    """
    try:
        import subprocess
        import sys
        import os
        
        print('收到重启请求，正在准备重启服务器...')
        
        # 获取当前脚本的路径
        script_path = os.path.abspath(__file__)
        
        # 构建重启命令
        # 使用pythonw.exe来在后台运行，避免控制台窗口
        python_exe = sys.executable
        
        # 启动一个新的进程来重启服务器
        # 使用subprocess.Popen来在后台运行
        subprocess.Popen([python_exe, script_path])
        
        # 返回重启成功的消息
        return jsonify({'message': '服务器正在重启...'}), 200
        
    except Exception as e:
        print(f'重启服务器失败: {e}')
        return jsonify({'error': f'重启服务器失败: {str(e)}'}), 500

@app.route('/api/get_default_paths', methods=['GET'])
def get_default_paths():
    """
    获取默认路径配置
    """
    try:
        settings_file = os.path.join(os.getcwd(), "gui_settings.json")
        default_model_path = os.path.join(os.getcwd(), "models")
        default_image_path = os.path.join(os.getcwd(), "auto_save")
        
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    saved_model_path = settings.get("模型文件夹路径", default_model_path)
                    saved_image_path = settings.get("默认图片保存路径", default_image_path)
                    return jsonify({
                        'success': True,
                        'default_model_path': saved_model_path,
                        'default_image_path': saved_image_path
                    }), 200
            except Exception as e:
                print(f'读取设置文件失败: {e}')
        
        return jsonify({
            'success': True,
            'default_model_path': default_model_path,
            'default_image_path': default_image_path
        }), 200
        
    except Exception as e:
        print(f'获取默认路径失败: {e}')
        return jsonify({'error': f'获取默认路径失败: {str(e)}'}), 500

@app.route('/api/get_default_model_path', methods=['GET'])
def get_default_model_path():
    """
    获取默认模型文件夹路径（兼容旧接口）
    """
    try:
        settings_file = os.path.join(os.getcwd(), "gui_settings.json")
        default_path = os.path.join(os.getcwd(), "models")
        
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    saved_path = settings.get("模型文件夹路径", default_path)
                    return jsonify({
                        'success': True,
                        'default_path': saved_path
                    }), 200
            except Exception as e:
                print(f'读取设置文件失败: {e}')
        
        return jsonify({
            'success': True,
            'default_path': default_path
        }), 200
        
    except Exception as e:
        print(f'获取默认路径失败: {e}')
        return jsonify({'error': f'获取默认路径失败: {str(e)}'}), 500

@app.route('/api/stop_execution', methods=['POST'])
def stop_execution():
    """
    停止当前正在执行的所有模块，并清空显存
    """
    global stop_execution_flag
    stop_execution_flag = True
    
    # 取消所有正在执行的future
    for future in ongoing_futures:
        try:
            future.cancel()
        except:
            pass
    
    # 清空张量缓存
    tensor_cache.clear()
    print('已清空张量缓存')
    
    # 清空模型缓存
    model_cache.clear()
    print('已清空模型缓存')
    
    # 释放PyTorch显存
    try:
        if torch and torch.cuda.is_available():
            torch.cuda.empty_cache()
            print('已释放CUDA显存')
    except Exception as e:
        print(f'释放CUDA显存失败: {e}')
    
    print('收到停止执行请求并已清空显存')
    return jsonify({'success': True, 'message': '已发送停止信号并清空显存'}), 200

@app.route('/api/get_engine_setting', methods=['GET'])
def get_engine_setting():
    """
    获取当前设置的生成引擎
    """
    try:
        settings_file = os.path.join(os.getcwd(), "gui_settings.json")
        default_engine = "CPU"
        
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    saved_engine = settings.get("生成引擎", default_engine)
                    return jsonify({
                        'success': True,
                        'engine': saved_engine
                    }), 200
            except Exception as e:
                print(f'读取生成引擎设置失败: {e}')
        
        return jsonify({
            'success': True,
            'engine': default_engine
        }), 200
        
    except Exception as e:
        print(f'获取生成引擎设置失败: {e}')
        return jsonify({'error': f'获取生成引擎设置失败: {str(e)}'}), 500


@app.route('/api/get_vae_setting', methods=['GET'])
def get_vae_setting():
    """
    获取当前设置的使用 CPU 运行 VAE
    """
    try:
        settings_file = os.path.join(os.getcwd(), "gui_settings.json")
        default_vae = False
        
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    saved_vae = settings.get("使用 CPU 运行 VAE", default_vae)
                    return jsonify({
                        'success': True,
                        'use_cpu_for_vae': saved_vae
                    }), 200
            except Exception as e:
                print(f'读取使用 CPU 运行 VAE 设置失败: {e}')
        
        return jsonify({
            'success': True,
            'use_cpu_for_vae': default_vae
        }), 200
        
    except Exception as e:
        print(f'获取使用 CPU 运行 VAE 设置失败: {e}')
        return jsonify({'error': f'获取使用 CPU 运行 VAE 设置失败: {str(e)}'}), 500


@app.route('/api/scan_models', methods=['POST'])
def scan_models():
    """
    扫描指定文件夹中的模型文件
    """
    try:
        data = request.json
        folder_path = data.get('folder_path', '')
        
        if not folder_path:
            return jsonify({'error': '文件夹路径不能为空'}), 400
        
        print(f'扫描模型文件夹: {folder_path}')
        
        # 检查文件夹是否存在
        if not os.path.exists(folder_path):
            return jsonify({'error': '文件夹不存在'}), 404
        
        # 扫描模型文件
        model_files = []
        patterns = [
            os.path.join(folder_path, "**", "*.safetensors"),
            os.path.join(folder_path, "**", "*.ckpt"),
            os.path.join(folder_path, "**", "*.bin")
        ]
        
        for pattern in patterns:
            files = glob.glob(pattern, recursive=True)
            model_files.extend(files)
        
        print(f'找到的模型文件: {model_files}')
        
        return jsonify({
            'success': True,
            'model_files': model_files
        }), 200
        
    except Exception as e:
        print(f'扫描模型文件失败: {e}')
        return jsonify({'error': f'扫描模型文件失败: {str(e)}'}), 500

@app.route('/api/get_module_source', methods=['POST'])
def get_module_source():
    """
    获取模块的完整源代码
    """
    try:
        data = request.json
        module_name = data.get('module_name')
        
        if not module_name:
            return jsonify({'error': '缺少module_name参数'}), 400
        
        # 确定模块文件路径
        module_path = None
        if os.path.exists(os.path.join(DEFAULT_MODULES_DIR, f'{module_name}.py')):
            module_path = os.path.join(DEFAULT_MODULES_DIR, f'{module_name}.py')
        elif os.path.exists(os.path.join(CUSTOM_MODULES_DIR, f'{module_name}.py')):
            module_path = os.path.join(CUSTOM_MODULES_DIR, f'{module_name}.py')
        
        if not module_path:
            return jsonify({'error': f'模块 {module_name} 不存在'}), 404
        
        # 读取模块源代码
        with open(module_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        # 解析模块参数
        module_params = parse_module_params(module_path)
        
        return jsonify({
            'success': True,
            'source_code': source_code,
            'module_params': module_params
        }), 200
        
    except Exception as e:
        print(f'获取模块源代码失败: {e}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate_code_ast', methods=['POST'])
def generate_code_ast():
    """
    基于AST的工作流Python代码生成
    """
    try:
        data = request.json
        workflow_data = data.get('workflow', {})
        
        # 导入插件
        import sys
        import os
        
        # 添加 plugin 目录到路径
        plugin_dir = os.path.join(os.path.dirname(__file__), 'plugin')
        if plugin_dir not in sys.path:
            sys.path.insert(0, plugin_dir)
        
        from json2py import generate_python_code_from_workflow
        
        # 调用插件函数
        source_code = generate_python_code_from_workflow(
            workflow_data,
            DEFAULT_MODULES_DIR,
            CUSTOM_MODULES_DIR
        )
        
        return jsonify({
            'success': True,
            'source_code': source_code
        }), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f'AST代码生成失败: {e}')
        return jsonify({'error': str(e)}), 500


def get_engine_from_settings():
    """从 gui_settings.json 读取生成引擎设置"""
    import os
    import json
    
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
    
    # 备份方案：从 simple_gui.py 读取
    backup_file = os.path.join(os.getcwd(), "simple_gui.py")
    if os.path.exists(backup_file):
        try:
            import ast
            with open(backup_file, "r", encoding="utf-8") as f:
                # 尝试在文件中搜索引擎设置
                content = f.read()
                if "生成引擎" in content:
                    # 简单字符串解析
                    for line in content.split('\n'):
                        if "生成引擎" in line and ":" in line:
                            engine = line.split(":", 1)[1].strip().strip('"').strip("'").strip(",")
                            if engine:
                                return engine
        except Exception:
            pass
    
    return default_engine


def check_and_restart_in_venv():
    """根据生成引擎设置选择对应的虚拟环境并重启"""
    import sys
    import os
    import subprocess
    
    # 如果已经在虚拟环境中运行，直接返回
    if hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix:
        return False
    
    # 获取生成引擎设置
    engine = get_engine_from_settings()
    print(f"读取到的生成引擎: {engine}")
    
    # 检查虚拟环境是否存在
    project_dir = os.getcwd()
    venv_cuda = os.path.join(project_dir, "venv_cuda")
    venv_dml = os.path.join(project_dir, "venv_dml")
    
    # 根据引擎选择虚拟环境
    target_venv = None
    
    if "CUDA" in engine or "TensorRT" in engine or "ZLUDA" in engine:
        # CUDA/TensorRT/ZLUDA 使用 venv_cuda
        if os.path.exists(venv_cuda):
            target_venv = venv_cuda
    elif "DML" in engine:
        # DML 必须使用 venv_dml，不存在则弹窗提醒
        if os.path.exists(venv_dml):
            target_venv = venv_dml
        else:
            # DML 引擎但 venv_dml 不存在，弹窗提醒
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror(
                    "错误",
                    "已选择 DML 引擎，但 venv_dml 虚拟环境不存在！\n\n"
                    "请先在高级设置中点击「一键安装」，选择「仅安装 DML」或「全部安装」。"
                )
                root.destroy()
            except:
                print("错误：已选择 DML 引擎，但 venv_dml 虚拟环境不存在！")
            sys.exit(1)
    else:
        # CPU 或其他情况，按优先级选择
        if os.path.exists(venv_cuda):
            target_venv = venv_cuda
        elif os.path.exists(venv_dml):
            target_venv = venv_dml
    
    if target_venv:
        python_exe = os.path.join(target_venv, "Scripts", "python.exe")
        if os.path.exists(python_exe):
            print(f"选择虚拟环境: {target_venv}")
            print(f"正在使用虚拟环境重新启动...")
            # 使用 subprocess 启动，在 Windows 上更可靠
            subprocess.Popen([python_exe] + sys.argv, cwd=project_dir)
            return True
    
    return False

if __name__ == '__main__':
    # 检查并在虚拟环境中重启
    if check_and_restart_in_venv():
        sys.exit(0)
    
    # 检查是否以模块方式运行
    if len(sys.argv) > 1 and sys.argv[1] == 'run':
        # 以模块方式运行，启动Flask服务器
        app.run(debug=False, host='0.0.0.0', port=5000)
    else:
        # 直接运行，启动GUI
        root = ctk.CTk()
        app = FlaskServerGUI(root)
        root.mainloop()
