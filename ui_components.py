import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import time

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DRAG_DROP_AVAILABLE = True
except ImportError:
    DRAG_DROP_AVAILABLE = False
    print("警告: 未安装tkinterdnd2库，拖拽功能将不可用。可通过 pip install tkinterdnd2 安装。")

class VideoRotatorUI:
    """视频旋转工具的用户界面类"""
    
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller
        self.setup_window()
        self.create_variables()
        self.create_widgets()
        self.setup_drag_drop()
    
    def setup_window(self):
        """设置窗口属性"""
        self.root.title("视频旋转工具")
        # 让窗口充满屏幕，移除固定尺寸限制
        self.root.state('zoomed')  # Windows下最大化窗口
        self.root.minsize(750, 500)
    
    def create_variables(self):
        """创建界面变量"""
        self.rotation_var = tk.StringVar(value="顺时针90度")
        self.suffix_var = tk.StringVar(value="_rotated")
        self.output_option_var = tk.StringVar(value="源文件目录")
        self.output_dir_var = tk.StringVar(value=os.path.normpath(os.path.expanduser("~/Desktop")))
        self.create_subdir_var = tk.BooleanVar(value=False)
        self.hw_accel_var = tk.StringVar(value="无")
        self.concurrent_tasks_var = tk.IntVar(value=1)
        self.status_var = tk.StringVar(value="就绪")
        self.time_var = tk.StringVar(value="剩余时间: --:--:--")
    
    def create_widgets(self):
        """创建界面组件"""
        # 创建主容器框架
        container = ttk.Frame(self.root)
        container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置根窗口权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)
        
        # 创建Canvas和滚动条
        self.canvas = tk.Canvas(container, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # 配置滚动
        def configure_scroll(event=None):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            # 延迟检查滚动条需求，确保布局完成
            def check_scrollbar():
                try:
                    canvas_height = self.canvas.winfo_height()
                    content_height = self.scrollable_frame.winfo_reqheight()
                    # 只有当内容真正超出画布高度时才显示滚动条
                    if content_height > canvas_height and canvas_height > 50:  # 增加最小高度阈值
                        self.scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
                    else:
                        self.scrollbar.grid_remove()
                except tk.TclError:
                    pass  # 忽略窗口销毁时的错误
            self.root.after(10, check_scrollbar)  # 延迟10ms检查
        
        self.scrollable_frame.bind("<Configure>", configure_scroll)
        self.canvas.bind("<Configure>", configure_scroll)
        
        # 创建窗口并配置Canvas宽度跟随
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        def configure_canvas_width(event=None):
            canvas_width = self.canvas.winfo_width()
            self.canvas.itemconfig(self.canvas_window, width=canvas_width)
        
        self.canvas.bind("<Configure>", lambda e: (configure_canvas_width(), configure_scroll()))
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # 布局Canvas
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            if self.scrollbar.winfo_viewable():
                self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # 主框架（现在在可滚动框架内）
        main_frame = ttk.Frame(self.scrollable_frame, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置主框架权重
        self.scrollable_frame.columnconfigure(0, weight=1)
        self.scrollable_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        # 设置各行的权重，让文件列表和日志区域可以伸缩
        main_frame.rowconfigure(0, weight=1)  # 文件选择区域可伸缩
        main_frame.rowconfigure(1, weight=0)  # 旋转设置区域
        main_frame.rowconfigure(2, weight=0)  # 进度区域
        main_frame.rowconfigure(3, weight=0)  # 高级设置区域
        main_frame.rowconfigure(4, weight=0)  # 按钮区域
        main_frame.rowconfigure(5, weight=1)  # 日志区域可伸缩
        main_frame.rowconfigure(6, weight=0)  # 版权信息区域
        
        # 创建各个区域
        self.create_file_section(main_frame)
        self.create_settings_section(main_frame)
        self.create_progress_section(main_frame)
        self.create_advanced_section(main_frame)
        self.create_button_section(main_frame)
        self.create_log_section(main_frame)
        self.create_copyright_section(main_frame)
    
    def create_file_section(self, parent):
        """创建文件选择区域"""
        # 文件选择区域 - 允许垂直扩展
        file_frame = ttk.LabelFrame(parent, text="视频文件", padding="5")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        file_frame.columnconfigure(1, weight=1)
        file_frame.rowconfigure(1, weight=1)
        
        # 文件操作按钮
        file_btn_frame = ttk.Frame(file_frame)
        file_btn_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Button(file_btn_frame, text="📁 添加文件", command=self.controller.add_files, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_btn_frame, text="📂 添加文件夹", command=self.controller.add_folder, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_btn_frame, text="🗑 清空列表", command=self.controller.clear_list, width=12).pack(side=tk.LEFT, padx=5)
        
        # 文件列表
        list_frame = ttk.Frame(file_frame)
        list_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # 移除固定高度，让文件列表自适应
        self.file_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED)
        file_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=file_scrollbar.set)
        
        self.file_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        file_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
    
    def create_settings_section(self, parent):
        """创建旋转设置区域"""
        # 旋转设置区域
        settings_frame = ttk.LabelFrame(parent, text="旋转设置", padding="8")
        settings_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N), pady=5)
        settings_frame.columnconfigure(1, weight=1)
        
        # 旋转方向选择
        ttk.Label(settings_frame, text="旋转方向:", font=('', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        rotation_frame = ttk.Frame(settings_frame)
        rotation_frame.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Radiobutton(rotation_frame, text="顺时针90°", variable=self.rotation_var, value="顺时针90度").pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(rotation_frame, text="逆时针90°", variable=self.rotation_var, value="逆时针90度").pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(rotation_frame, text="180°", variable=self.rotation_var, value="180度").pack(side=tk.LEFT)
        
        # 输出设置
        ttk.Label(settings_frame, text="输出后缀:", font=('', 9, 'bold')).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        suffix_entry = ttk.Entry(settings_frame, textvariable=self.suffix_var, width=20, font=('', 9))
        suffix_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 输出选项
        ttk.Label(settings_frame, text="输出位置:", font=('', 9, 'bold')).grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        output_option_frame = ttk.Frame(settings_frame)
        output_option_frame.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Radiobutton(output_option_frame, text="源文件目录", variable=self.output_option_var, 
                       value="源文件目录", command=self.on_output_option_changed).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(output_option_frame, text="桌面", variable=self.output_option_var, 
                       value="桌面", command=self.on_output_option_changed).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(output_option_frame, text="指定目录", variable=self.output_option_var, 
                       value="指定目录", command=self.on_output_option_changed).pack(side=tk.LEFT)
        
        # 自定义输出目录
        self.custom_dir_frame = ttk.Frame(settings_frame)
        self.custom_dir_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.custom_dir_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.custom_dir_frame, text="自定义目录:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.output_dir_entry = ttk.Entry(self.custom_dir_frame, textvariable=self.output_dir_var, width=40)
        self.output_dir_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        self.output_dir_btn = ttk.Button(self.custom_dir_frame, text="浏览", command=self.select_output_dir)
        self.output_dir_btn.grid(row=0, column=2, padx=5)
        
        # 输出目录创建选项
        self.create_subdir_check = ttk.Checkbutton(self.custom_dir_frame, text="创建子目录（按日期）", 
                                                  variable=self.create_subdir_var)
        self.create_subdir_check.grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=5, pady=2)
        
        # 初始状态下隐藏自定义目录选项
        self.on_output_option_changed()
    
    def create_progress_section(self, parent):
        """创建进度区域"""
        # 进度区域
        progress_frame = ttk.LabelFrame(parent, text="处理进度", padding="5")
        progress_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N), pady=5)
        progress_frame.columnconfigure(0, weight=1)
        
        # 总体进度条
        ttk.Label(progress_frame, text="总体进度:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.overall_progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.overall_progress_bar.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        
        # 当前任务进度条
        ttk.Label(progress_frame, text="当前任务:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.current_progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.current_progress_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        
        # 状态信息
        status_info_frame = ttk.Frame(progress_frame)
        status_info_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        status_info_frame.columnconfigure(0, weight=1)
        
        ttk.Label(status_info_frame, textvariable=self.status_var).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(status_info_frame, textvariable=self.time_var).grid(row=0, column=1, sticky=tk.E)
    
    def create_advanced_section(self, parent):
        """创建高级设置区域"""
        # 高级设置区域
        advanced_frame = ttk.LabelFrame(parent, text="高级设置", padding="5")
        advanced_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N), pady=5)
        advanced_frame.columnconfigure(1, weight=1)
        
        # 硬件加速设置
        ttk.Label(advanced_frame, text="硬件加速:", font=('', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        hw_accel_frame = ttk.Frame(advanced_frame)
        hw_accel_frame.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Radiobutton(hw_accel_frame, text="无", variable=self.hw_accel_var, value="无").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(hw_accel_frame, text="NVIDIA", variable=self.hw_accel_var, value="nvenc").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(hw_accel_frame, text="Intel", variable=self.hw_accel_var, value="qsv").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(hw_accel_frame, text="AMD", variable=self.hw_accel_var, value="amf").pack(side=tk.LEFT)
        
        # 并发任务数设置
        ttk.Label(advanced_frame, text="并发任务数:", font=('', 9, 'bold')).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        concurrent_frame = ttk.Frame(advanced_frame)
        concurrent_frame.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Scale(concurrent_frame, from_=1, to=8, variable=self.concurrent_tasks_var, 
                 orient=tk.HORIZONTAL, length=180).pack(side=tk.LEFT)
        self.concurrent_label = ttk.Label(concurrent_frame, text="1", width=3)
        self.concurrent_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # 绑定滑块变化事件
        self.concurrent_tasks_var.trace('w', self.on_concurrent_changed)
    
    def create_button_section(self, parent):
        """创建按钮区域"""
        # 按钮区域
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        self.start_btn = ttk.Button(button_frame, text="🚀 开始处理", command=self.controller.start_processing, width=14)
        self.start_btn.pack(side=tk.LEFT, padx=8)
        
        self.stop_btn = ttk.Button(button_frame, text="⏹ 停止", command=self.controller.stop_processing, state=tk.DISABLED, width=14)
        self.stop_btn.pack(side=tk.LEFT, padx=8)
    
    def create_log_section(self, parent):
        """创建日志区域"""
        # 日志区域 - 允许垂直扩展
        log_frame = ttk.LabelFrame(parent, text="日志", padding="5")
        log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 移除固定高度，让日志区域自适应
        self.log_text = tk.Text(log_frame, state=tk.DISABLED, wrap=tk.WORD)
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
    
    def setup_drag_drop(self):
        """设置拖拽支持"""
        if DRAG_DROP_AVAILABLE:
            # 为文件列表框设置拖拽支持
            self.file_listbox.drop_target_register(DND_FILES)
            self.file_listbox.dnd_bind('<<Drop>>', self.controller.on_drop)
            
            # 为主窗口设置拖拽支持
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self.controller.on_drop)
    
    def on_output_option_changed(self):
        """输出选项变化时的处理"""
        option = self.output_option_var.get()
        if option == "源文件目录":
            # 隐藏自定义目录选项
            for widget in self.custom_dir_frame.winfo_children():
                widget.grid_remove()
        elif option == "桌面":
            # 隐藏自定义目录选项，但设置桌面路径
            for widget in self.custom_dir_frame.winfo_children():
                widget.grid_remove()
            self.output_dir_var.set(os.path.normpath(os.path.expanduser("~/Desktop")))
        else:
            # 显示自定义目录选项
            for widget in self.custom_dir_frame.winfo_children():
                widget.grid()
    
    def select_output_dir(self):
        """选择输出目录"""
        directory = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if directory:
            # 统一使用反斜杠分隔符
            self.output_dir_var.set(os.path.normpath(directory))
    
    def on_concurrent_changed(self, *args):
        """并发任务数变化时的处理"""
        self.concurrent_label.config(text=str(self.concurrent_tasks_var.get()))
    
    def update_file_list(self, files):
        """更新文件列表显示"""
        self.file_listbox.delete(0, tk.END)
        for file in files:
            filename = os.path.basename(file)
            display_text = f"{filename} ({file})"
            self.file_listbox.insert(tk.END, display_text)
    
    def create_copyright_section(self, parent):
        """创建版权信息区域"""
        copyright_frame = ttk.Frame(parent)
        copyright_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 5))
        copyright_frame.columnconfigure(0, weight=1)
        
        # 添加分隔线
        separator = ttk.Separator(copyright_frame, orient='horizontal')
        separator.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 版权信息标签 - 居中显示
        copyright_text = "© 2025 视频旋转工具 - 基于FFmpeg开发 | 作者: 新疆萌森软件开发工作室 | 版本: 2.0"
        copyright_label = ttk.Label(copyright_frame, text=copyright_text, 
                                   font=('', 8), foreground='gray', anchor='center')
        copyright_label.grid(row=1, column=0, sticky=(tk.W, tk.E))
    
    def log_message(self, message):
        """添加日志消息"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()