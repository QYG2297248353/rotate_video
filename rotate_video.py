import os
import re
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime, timedelta
import json
import sys
from pathlib import Path
import shutil

# 尝试导入拖拽支持库
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DRAG_DROP_AVAILABLE = True
except ImportError:
    DRAG_DROP_AVAILABLE = False
    print("警告: 未安装tkinterdnd2库，拖拽功能将不可用。可通过 pip install tkinterdnd2 安装。")

class VideoRotator:
    def __init__(self, root):
        self.root = root
        self.root.title("视频旋转工具")
        self.root.geometry("900x650")
        self.root.minsize(800, 550)
        
        # 初始化变量
        self.video_files = []
        self.processing = False
        self.stop_requested = False
        self.current_process = None
        
        # 处理命令行参数（拖拽到exe的文件）
        self.process_command_line_args()
        
        # 检查FFmpeg是否可用
        self.ffmpeg_path = self.find_ffmpeg()
        if not self.ffmpeg_path:
            messagebox.showerror("错误", "未找到FFmpeg，请确保已安装FFmpeg并添加到系统PATH中")
            sys.exit(1)
            
        # 创建界面
        self.create_widgets()
        
        # 设置拖拽支持
        self.setup_drag_drop()
        
        # 加载配置
        self.load_config()
    
    def find_ffmpeg(self):
        """查找FFmpeg可执行文件路径"""
        # 首先检查系统PATH中的ffmpeg
        if shutil.which("ffmpeg"):
            return "ffmpeg"
        
        # 检查当前目录下的ffmpeg
        if getattr(sys, 'frozen', False):
            # 如果是打包后的exe，检查exe所在目录
            base_path = os.path.dirname(sys.executable)
            ffmpeg_path = os.path.join(base_path, "ffmpeg.exe")
            if os.path.isfile(ffmpeg_path):
                return ffmpeg_path
        
        # 检查常见安装路径
        common_paths = [
            os.path.join(os.environ.get('ProgramFiles', ''), "ffmpeg", "bin", "ffmpeg.exe"),
            os.path.join(os.environ.get('ProgramFiles(x86)', ''), "ffmpeg", "bin", "ffmpeg.exe"),
            os.path.join(os.environ.get('SystemDrive', 'C:'), "ffmpeg", "bin", "ffmpeg.exe"),
        ]
        
        for path in common_paths:
            if os.path.isfile(path):
                return path
                
        return None
    
    def process_command_line_args(self):
        """处理命令行参数（拖拽到exe的文件）"""
        if len(sys.argv) > 1:
            for arg in sys.argv[1:]:
                # 规范化路径
                path = os.path.normpath(os.path.abspath(arg))
                if os.path.isfile(path):
                    # 检查是否为视频文件
                    if self.is_video_file(path):
                        self.video_files.append(path)
                elif os.path.isdir(path):
                    # 添加目录中的所有视频文件
                    self.add_videos_from_directory(path)
    
    def is_video_file(self, filepath):
        """检查文件是否为视频文件"""
        extensions = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v')
        return filepath.lower().endswith(extensions)
    
    def add_videos_from_directory(self, directory):
        """从目录中添加所有视频文件"""
        for root_dir, _, files in os.walk(directory):
            for file in files:
                if self.is_video_file(file):
                    full_path = os.path.normpath(os.path.join(root_dir, file))
                    if full_path not in self.video_files:
                        self.video_files.append(full_path)
    
    def setup_drag_drop(self):
        """设置拖拽支持"""
        if DRAG_DROP_AVAILABLE:
            # 为文件列表框设置拖拽支持
            self.file_listbox.drop_target_register(DND_FILES)
            self.file_listbox.dnd_bind('<<Drop>>', self.on_drop)
            
            # 为主窗口设置拖拽支持
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self.on_drop)
    
    def on_drop(self, event):
        """处理拖拽事件"""
        files = self.root.tk.splitlist(event.data)
        for file_path in files:
            # 规范化路径
            path = os.path.normpath(os.path.abspath(file_path))
            if os.path.isfile(path):
                if self.is_video_file(path) and path not in self.video_files:
                    self.video_files.append(path)
            elif os.path.isdir(path):
                self.add_videos_from_directory(path)
        
        self.update_file_list()
        return 'break'
    
    def run_ffmpeg(self, cmd):
        """运行FFmpeg命令并处理Windows路径问题"""
        # 规范化命令中的所有路径
        formatted_cmd = []
        for part in cmd:
            if os.path.exists(part):
                # 规范化现有文件路径
                formatted_cmd.append(os.path.normpath(os.path.abspath(part)))
            elif part == "ffmpeg":
                # 使用找到的ffmpeg路径
                formatted_cmd.append(self.ffmpeg_path)
            else:
                formatted_cmd.append(part)
                
        # 在Windows上使用shell=False避免编码问题
        try:
            return subprocess.Popen(
                formatted_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
        except Exception as e:
            # 如果utf-8编码失败，尝试使用系统默认编码
            try:
                return subprocess.Popen(
                    formatted_cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
            except Exception as e2:
                self.log_message(f"FFmpeg启动失败: {str(e2)}")
                raise e2
    
    def run_ffmpeg_simple(self, input_file, output_file, rotation):
        """运行FFmpeg命令（简化版本，支持硬件加速）"""
        try:
            # 规范化路径
            input_file = os.path.normpath(input_file)
            output_file = os.path.normpath(output_file)
            
            # 构建FFmpeg命令
            ffmpeg_path = self.ffmpeg_path
            
            # 基础命令
            cmd = [ffmpeg_path, "-i", input_file]
            
            # 添加硬件加速参数
            hw_params = self.get_hw_accel_params()
            if hw_params:
                cmd.extend(hw_params)
            
            # 添加旋转参数
            cmd.extend(["-vf", f"transpose={rotation}", "-y", output_file])
            
            # 运行命令
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg错误: {result.stderr}")
            
            return True
        except Exception as e:
            self.log_message(f"处理失败: {str(e)}")
            return False
    
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置行列权重以实现自适应
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="视频文件", padding="5")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N), pady=5)
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Button(file_frame, text="添加文件", command=self.add_files).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(file_frame, text="添加文件夹", command=self.add_folder).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="清空列表", command=self.clear_list).grid(row=0, column=2, padx=5, pady=5)
        
        # 文件列表
        list_frame = ttk.Frame(file_frame)
        list_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        self.file_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=6)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.file_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 旋转设置区域
        settings_frame = ttk.LabelFrame(main_frame, text="旋转设置", padding="8")
        settings_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N), pady=5)
        settings_frame.columnconfigure(1, weight=1)
        
        # 旋转方向选择
        ttk.Label(settings_frame, text="旋转方向:", font=('', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.rotation_var = tk.StringVar(value="顺时针90度")
        rotation_frame = ttk.Frame(settings_frame)
        rotation_frame.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Radiobutton(rotation_frame, text="顺时针90°", variable=self.rotation_var, value="顺时针90度").pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(rotation_frame, text="逆时针90°", variable=self.rotation_var, value="逆时针90度").pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(rotation_frame, text="180°", variable=self.rotation_var, value="180度").pack(side=tk.LEFT)
        
        # 输出设置
        ttk.Label(settings_frame, text="输出后缀:", font=('', 9, 'bold')).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.suffix_var = tk.StringVar(value="_rotated")
        suffix_entry = ttk.Entry(settings_frame, textvariable=self.suffix_var, width=20, font=('', 9))
        suffix_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 输出选项
        ttk.Label(settings_frame, text="输出位置:", font=('', 9, 'bold')).grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.output_option_var = tk.StringVar(value="源文件目录")
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
        self.output_dir_var = tk.StringVar(value=os.path.expanduser("~/Desktop"))
        self.output_dir_entry = ttk.Entry(self.custom_dir_frame, textvariable=self.output_dir_var, width=40)
        self.output_dir_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        self.output_dir_btn = ttk.Button(self.custom_dir_frame, text="浏览", command=self.select_output_dir)
        self.output_dir_btn.grid(row=0, column=2, padx=5)
        
        # 输出目录创建选项
        self.create_subdir_var = tk.BooleanVar(value=False)
        self.create_subdir_check = ttk.Checkbutton(self.custom_dir_frame, text="创建子目录（按日期）", 
                                                  variable=self.create_subdir_var)
        self.create_subdir_check.grid(row=1, column=0, columnspan=3, sticky=tk.W, padx=5, pady=2)
        
        # 初始状态下隐藏自定义目录选项
        self.on_output_option_changed()
        
        # 进度区域
        progress_frame = ttk.LabelFrame(main_frame, text="处理进度", padding="5")
        progress_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N), pady=5)
        progress_frame.columnconfigure(0, weight=1)
        
        # 高级设置区域
        advanced_frame = ttk.LabelFrame(main_frame, text="高级设置", padding="5")
        advanced_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N), pady=5)
        advanced_frame.columnconfigure(1, weight=1)
        
        # 硬件加速设置
        ttk.Label(advanced_frame, text="硬件加速:", font=('', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.hw_accel_var = tk.StringVar(value="无")
        hw_accel_frame = ttk.Frame(advanced_frame)
        hw_accel_frame.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Radiobutton(hw_accel_frame, text="无", variable=self.hw_accel_var, value="无").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(hw_accel_frame, text="NVIDIA", variable=self.hw_accel_var, value="nvenc").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(hw_accel_frame, text="Intel", variable=self.hw_accel_var, value="qsv").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Radiobutton(hw_accel_frame, text="AMD", variable=self.hw_accel_var, value="amf").pack(side=tk.LEFT)
        
        # 并发任务数设置
        ttk.Label(advanced_frame, text="并发任务数:", font=('', 9, 'bold')).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.concurrent_tasks_var = tk.IntVar(value=1)
        concurrent_frame = ttk.Frame(advanced_frame)
        concurrent_frame.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Scale(concurrent_frame, from_=1, to=8, variable=self.concurrent_tasks_var, 
                 orient=tk.HORIZONTAL, length=180).pack(side=tk.LEFT)
        self.concurrent_label = ttk.Label(concurrent_frame, text="1", width=3)
        self.concurrent_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # 绑定滑块变化事件
        self.concurrent_tasks_var.trace('w', self.on_concurrent_changed)
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
        
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_info_frame, textvariable=self.status_var).grid(row=0, column=0, sticky=tk.W)
        
        self.time_var = tk.StringVar(value="剩余时间: --:--:--")
        ttk.Label(status_info_frame, textvariable=self.time_var).grid(row=0, column=1, sticky=tk.E)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        self.start_btn = ttk.Button(button_frame, text="🚀 开始处理", command=self.start_processing, width=14)
        self.start_btn.pack(side=tk.LEFT, padx=8)
        
        self.stop_btn = ttk.Button(button_frame, text="⏹ 停止", command=self.stop_processing, state=tk.DISABLED, width=14)
        self.stop_btn.pack(side=tk.LEFT, padx=8)
        
        # 添加文件按钮
        ttk.Button(button_frame, text="📁 添加文件", command=self.add_files, width=14).pack(side=tk.LEFT, padx=8)
        ttk.Button(button_frame, text="📂 添加文件夹", command=self.add_folder, width=14).pack(side=tk.LEFT, padx=8)
        ttk.Button(button_frame, text="🗑 清空列表", command=self.clear_list, width=14).pack(side=tk.LEFT, padx=8)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="5")
        log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = tk.Text(log_frame, height=10, state=tk.DISABLED)
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
    
    def add_files(self):
        """添加文件到列表"""
        files = filedialog.askopenfilenames(
            title="选择视频文件",
            filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.webm *.m4v"), ("所有文件", "*.*")]
        )
        if files:
            self.video_files.extend(files)
            self.update_file_list()
    
    def add_folder(self):
        """添加文件夹中的所有视频文件到列表"""
        folder = filedialog.askdirectory(title="选择包含视频文件的文件夹")
        if folder:
            self.add_videos_from_directory(folder)
            self.update_file_list()
    
    def clear_list(self):
        """清空文件列表"""
        self.video_files = []
        self.update_file_list()
    
    def update_file_list(self):
        """更新文件列表显示"""
        self.file_listbox.delete(0, tk.END)
        for file in self.video_files:
            filename = os.path.basename(file)
            display_text = f"{filename} ({file})"
            self.file_listbox.insert(tk.END, display_text)
    
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
            self.output_dir_var.set(os.path.expanduser("~/Desktop"))
        else:
            # 显示自定义目录选项
            for widget in self.custom_dir_frame.winfo_children():
                widget.grid()
    
    def on_concurrent_changed(self, *args):
        """并发任务数变化时的处理"""
        value = self.concurrent_tasks_var.get()
        self.concurrent_label.config(text=str(value))
    
    def get_hw_accel_params(self):
        """获取硬件加速参数"""
        hw_accel = self.hw_accel_var.get()
        if hw_accel == "无":
            return []
        elif hw_accel == "nvenc":
            return ["-c:v", "h264_nvenc"]
        elif hw_accel == "qsv":
            return ["-c:v", "h264_qsv"]
        elif hw_accel == "amf":
            return ["-c:v", "h264_amf"]
        return []
    
    def select_output_dir(self):
        """选择输出目录"""
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            self.output_dir_var.set(os.path.normpath(directory))
    
    def log_message(self, message):
        """添加消息到日志"""
        self.log_text.configure(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)
    
    def start_processing(self):
        """开始处理视频"""
        if not self.video_files:
            messagebox.showwarning("警告", "请先添加视频文件")
            return
        
        # 检查输出目录（除了源文件目录选项）
        option = self.output_option_var.get()
        if option == "桌面":
            output_dir = os.path.expanduser("~/Desktop")
            if hasattr(self, 'create_subdir_var') and self.create_subdir_var.get():
                date_str = datetime.now().strftime("%Y%m%d")
                output_dir = os.path.join(output_dir, f"视频旋转_{date_str}")
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir)
                except OSError as e:
                    messagebox.showerror("错误", f"无法创建输出目录: {e}")
                    return
        elif option == "指定目录":
            output_dir = self.output_dir_var.get()
            if hasattr(self, 'create_subdir_var') and self.create_subdir_var.get():
                date_str = datetime.now().strftime("%Y%m%d")
                output_dir = os.path.join(output_dir, f"视频旋转_{date_str}")
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir)
                except OSError as e:
                    messagebox.showerror("错误", f"无法创建输出目录: {e}")
                    return
        
        # 更新界面状态
        self.processing = True
        self.stop_requested = False
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.overall_progress_bar.config(value=0)
        self.current_progress_bar.config(value=0)
        
        # 开始处理线程
        thread = threading.Thread(target=self.process_videos_concurrent)
        thread.daemon = True
        thread.start()
    
    def stop_processing(self):
        """停止处理"""
        self.stop_requested = True
        if self.current_process:
            try:
                self.current_process.terminate()
            except:
                pass
        self.log_message("用户请求停止处理...")
    
    def process_videos_concurrent(self):
        """并发处理所有视频"""
        import concurrent.futures
        
        total_files = len(self.video_files)
        max_workers = self.concurrent_tasks_var.get()
        processed_files = 0
        failed_files = 0
        start_time = time.time()
        
        def process_with_progress(file_info):
            """处理单个文件并返回结果"""
            index, input_file = file_info
            try:
                # 更新当前处理状态
                self.root.after(0, lambda: self.status_var.set(f"处理中: {os.path.basename(input_file)} ({index+1}/{total_files})"))
                
                success = self.process_single_video(input_file)
                return (index, input_file, success)
            except Exception as e:
                self.log_message(f"处理文件 {input_file} 时出错: {str(e)}")
                return (index, input_file, False)
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                file_tasks = [(i, file) for i, file in enumerate(self.video_files)]
                future_to_file = {executor.submit(process_with_progress, task): task for task in file_tasks}
                
                # 处理完成的任务
                for future in concurrent.futures.as_completed(future_to_file):
                    if self.stop_requested:
                        # 取消所有未完成的任务
                        for f in future_to_file:
                            f.cancel()
                        break
                    
                    try:
                        index, input_file, success = future.result()
                        if success:
                            processed_files += 1
                            self.log_message(f"完成: {os.path.basename(input_file)}")
                        else:
                            failed_files += 1
                            self.log_message(f"失败: {os.path.basename(input_file)}")
                        
                        # 更新总体进度
                        completed_tasks = processed_files + failed_files
                        overall_progress = (completed_tasks / total_files) * 100
                        self.root.after(0, lambda p=overall_progress: self.overall_progress_bar.config(value=p))
                        
                        # 计算剩余时间
                        elapsed = time.time() - start_time
                        if completed_tasks > 0:
                            time_per_file = elapsed / completed_tasks
                            remaining = time_per_file * (total_files - completed_tasks)
                            self.root.after(0, lambda r=remaining: self.time_var.set(f"剩余时间: {str(timedelta(seconds=int(r)))}"))
                        
                    except Exception as e:
                        failed_files += 1
                        self.log_message(f"任务执行出错: {str(e)}")
        
        except Exception as e:
            self.log_message(f"并发处理出错: {str(e)}")
        
        # 处理完成
        self.processing = False
        self.root.after(0, self.processing_finished, processed_files, total_files)
    
    def process_videos(self):
        """处理所有视频（单线程版本）"""
        total_files = len(self.video_files)
        processed_files = 0
        start_time = time.time()
        
        for i, input_file in enumerate(self.video_files):
            if self.stop_requested:
                break
            
            # 更新状态
            self.status_var.set(f"处理中: {os.path.basename(input_file)} ({i+1}/{total_files})")
            self.overall_progress_bar.config(value=(i / total_files) * 100)
            
            # 计算剩余时间
            elapsed = time.time() - start_time
            if i > 0:
                time_per_file = elapsed / i
                remaining = time_per_file * (total_files - i)
                self.time_var.set(f"剩余时间: {str(timedelta(seconds=int(remaining)))}")
            else:
                self.time_var.set("剩余时间: 计算中...")
            
            # 处理单个视频
            success = self.process_single_video(input_file)
            
            if success:
                processed_files += 1
                self.log_message(f"完成: {os.path.basename(input_file)}")
            else:
                self.log_message(f"失败: {os.path.basename(input_file)}")
        
        # 处理完成
        self.processing = False
        self.root.after(0, self.processing_finished, processed_files, total_files)
    
    def processing_finished(self, processed, total):
        """处理完成后的清理工作"""
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.overall_progress_bar.config(value=100)
        self.current_progress_bar.config(value=0)
        self.status_var.set(f"处理完成: {processed}/{total} 个文件")
        self.time_var.set("剩余时间: --:--:--")
        
        # 保存配置
        self.save_config()
        
        if processed == total:
            messagebox.showinfo("完成", f"所有 {total} 个视频处理完成!")
        else:
            messagebox.showwarning("部分完成", f"处理了 {processed}/{total} 个视频")
    
    def process_single_video(self, input_file):
        """处理单个视频文件"""
        try:
            # 规范化输入文件路径
            input_file = os.path.normpath(os.path.abspath(input_file))
            
            # 生成输出文件名
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            ext = os.path.splitext(input_file)[1]
            suffix = self.suffix_var.get()
            
            # 根据输出选项确定输出目录
            option = self.output_option_var.get()
            if option == "源文件目录":
                output_dir = os.path.dirname(input_file)
            elif option == "桌面":
                output_dir = os.path.expanduser("~/Desktop")
                # 如果选择创建子目录，添加日期子目录
                if hasattr(self, 'create_subdir_var') and self.create_subdir_var.get():
                    date_str = datetime.now().strftime("%Y%m%d")
                    output_dir = os.path.join(output_dir, f"视频旋转_{date_str}")
            else:
                output_dir = os.path.normpath(self.output_dir_var.get())
                # 如果选择创建子目录，添加日期子目录
                if hasattr(self, 'create_subdir_var') and self.create_subdir_var.get():
                    date_str = datetime.now().strftime("%Y%m%d")
                    output_dir = os.path.join(output_dir, f"视频旋转_{date_str}")
            
            # 确保输出目录存在
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir)
                    self.log_message(f"创建输出目录: {output_dir}")
                except OSError as e:
                    self.log_message(f"无法创建输出目录 {output_dir}: {e}")
                    return False
            
            output_file = os.path.normpath(os.path.join(output_dir, f"{base_name}{suffix}{ext}"))
            
            # 检查文件是否已存在
            if os.path.exists(output_file):
                if not self.confirm_overwrite(output_file):
                    return False  # 用户选择不覆盖
            
            # 使用重新编码方式旋转视频
            return self.reencode_video(input_file, output_file)
            
        except Exception as e:
            self.log_message(f"处理出错: {str(e)}")
            return False
    
    def confirm_overwrite(self, filename):
        """确认是否覆盖已存在的文件"""
        # 使用after确保在主线程中执行
        result = []
        def ask():
            result.append(messagebox.askyesno("文件已存在", 
                                            f"文件 {os.path.basename(filename)} 已存在，是否覆盖?"))
        self.root.after(0, ask)
        # 等待用户响应
        while not result:
            time.sleep(0.1)
        return result[0]
    
    def get_rotation_code(self):
        """获取旋转参数代码"""
        rotation = self.rotation_var.get()
        if rotation == "顺时针90度":
            return "1"  # 顺时针90度
        elif rotation == "逆时针90度":
            return "2"  # 逆时针90度
        elif rotation == "180度":
            return "3"  # 180度
        return "0"      # 不旋转
    
    def reencode_video(self, input_file, output_file):
        """使用重新编码方式旋转视频"""
        try:
            # 构建FFmpeg命令
            rotation_code = self.get_rotation_code()
            cmd = [
                self.ffmpeg_path, 
                '-i', input_file,
                '-vf', f'transpose={rotation_code}',
                '-c:a', 'copy',
                '-y', output_file
            ]
            
            self.log_message(f"开始处理: {os.path.basename(input_file)}")
            
            # 执行命令
            self.current_process = self.run_ffmpeg(cmd)
            
            # 读取输出并解析进度
            duration = None
            for line in self.current_process.stdout:
                if self.stop_requested:
                    self.current_process.terminate()
                    return False
                
                # 解析视频时长
                if duration is None:
                    duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", line)
                    if duration_match:
                        hours, minutes, seconds = map(float, duration_match.groups())
                        duration = hours * 3600 + minutes * 60 + seconds
                        self.log_message(f"视频时长: {duration}秒")
                
                # 解析当前处理进度
                if duration is not None:
                    time_match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
                    if time_match:
                        hours, minutes, seconds = map(float, time_match.groups())
                        current_time = hours * 3600 + minutes * 60 + seconds
                        progress = (current_time / duration) * 100
                        self.current_progress_bar.config(value=progress)
            
            # 等待进程完成
            self.current_process.wait()
            return_code = self.current_process.returncode
            self.current_process = None
            
            if return_code == 0:
                self.log_message(f"成功旋转视频: {os.path.basename(input_file)}")
                return True
            else:
                self.log_message(f"旋转视频失败: {os.path.basename(input_file)}")
                return False
            
        except Exception as e:
            self.log_message(f"重新编码出错: {str(e)}")
            if self.current_process:
                self.current_process.terminate()
                self.current_process = None
            return False
    
    def load_config(self):
        """加载配置"""
        config_path = os.path.join(os.path.expanduser("~"), ".video_rotator_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.rotation_var.set(config.get('rotation', '顺时针90度'))
                    self.suffix_var.set(config.get('suffix', '_rotated'))
                    self.output_option_var.set(config.get('output_option', '源文件目录'))
                    self.output_dir_var.set(config.get('output_dir', os.path.expanduser("~/Desktop")))
                    self.hw_accel_var.set(config.get('hw_accel', '无'))
                    self.concurrent_tasks_var.set(config.get('concurrent_tasks', 1))
                    if hasattr(self, 'create_subdir_var'):
                        self.create_subdir_var.set(config.get('create_subdir', False))
                    # 更新界面状态
                    self.on_output_option_changed()
                    self.on_concurrent_changed()
            except:
                pass
    
    def save_config(self):
        """保存配置"""
        config = {
            'rotation': self.rotation_var.get(),
            'suffix': self.suffix_var.get(),
            'output_option': self.output_option_var.get(),
            'output_dir': self.output_dir_var.get(),
            'hw_accel': self.hw_accel_var.get(),
            'concurrent_tasks': self.concurrent_tasks_var.get(),
            'create_subdir': self.create_subdir_var.get() if hasattr(self, 'create_subdir_var') else False
        }
        
        config_path = os.path.join(os.path.expanduser("~"), ".video_rotator_config.json")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_message(f"保存配置失败: {str(e)}")

def main():
    """主函数"""
    if DRAG_DROP_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    
    app = VideoRotator(root)
    
    # 如果有命令行参数传入的文件，更新文件列表显示
    if app.video_files:
        app.update_file_list()
    
    root.mainloop()

if __name__ == "__main__":
    main()