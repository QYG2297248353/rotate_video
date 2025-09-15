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

# 导入新的模块
from ui_components import VideoRotatorUI
from video_processor import VideoProcessor
from config_manager import ConfigManager

class VideoRotator:
    def __init__(self, root):
        self.root = root
        
        # 初始化变量
        self.video_files = []
        self.processing = False
        self.stop_requested = False
        self.active_processes = []  # 存储活跃的进程列表
        
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        
        # 初始化视频处理器
        self.video_processor = VideoProcessor(ui_callback=self.ui_callback)
        
        # 处理命令行参数（拖拽到exe的文件）
        self.process_command_line_args()
        
        # 检查FFmpeg是否可用
        self.ffmpeg_path = self.find_ffmpeg()
        if not self.ffmpeg_path:
            messagebox.showerror("错误", "未找到FFmpeg，请确保已安装FFmpeg并添加到系统PATH中")
            sys.exit(1)
            
        # 创建界面
        self.ui = VideoRotatorUI(self.root, self)
        
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
    
    def ui_callback(self, callback_type, data):
        """UI回调函数，用于视频处理器更新界面"""
        if callback_type == 'log':
            self.ui.log_message(data)
        elif callback_type == 'status':
            self.ui.status_var.set(data)
        elif callback_type == 'time':
            self.ui.time_var.set(data)
        elif callback_type == 'progress':
            if 'overall' in data:
                self.ui.overall_progress_bar['value'] = data['overall']
            if 'current' in data:
                self.ui.current_progress_bar['value'] = data['current']
            self.root.update_idletasks()
    
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
        
        self.ui.update_file_list(self.video_files)
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
                self.ui.log_message(f"FFmpeg启动失败: {str(e2)}")
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
            self.ui.log_message(f"处理失败: {str(e)}")
            return False
    

    
    def add_files(self):
        """添加文件到列表"""
        files = filedialog.askopenfilenames(
            title="选择视频文件",
            filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.webm *.m4v"), ("所有文件", "*.*")]
        )
        if files:
            self.video_files.extend(files)
            self.ui.update_file_list(self.video_files)
    
    def add_folder(self):
        """添加文件夹中的所有视频文件到列表"""
        folder = filedialog.askdirectory(title="选择包含视频文件的文件夹")
        if folder:
            self.add_videos_from_directory(folder)
            self.ui.update_file_list(self.video_files)
    
    def clear_list(self):
        """清空文件列表"""
        self.video_files = []
        self.ui.update_file_list(self.video_files)
    

    
    def get_hw_accel_params(self):
        """获取硬件加速参数"""
        hw_accel = self.ui.hw_accel_var.get()
        if hw_accel == "无":
            return []
        elif hw_accel == "nvenc":
            return ["-c:v", "h264_nvenc"]
        elif hw_accel == "qsv":
            return ["-c:v", "h264_qsv"]
        elif hw_accel == "amf":
            return ["-c:v", "h264_amf"]
        return []
    

    
    def start_processing(self):
        """开始处理视频"""
        if not self.video_files:
            messagebox.showwarning("警告", "请先添加视频文件")
            return
        
        # 保存当前设置
        self.save_current_settings()
        
        # 准备处理参数
        processing_params = {
            'rotation': self.ui.rotation_var.get(),
            'suffix': self.ui.suffix_var.get(),
            'output_option': self.ui.output_option_var.get(),
            'output_dir': self.ui.output_dir_var.get(),
            'create_subdir': self.ui.create_subdir_var.get(),
            'hw_accel': self.ui.hw_accel_var.get(),
            'concurrent_tasks': self.ui.concurrent_tasks_var.get()
        }
        
        # 检查输出目录（除了源文件目录选项）
        option = self.ui.output_option_var.get()
        if option == "桌面":
            output_dir = os.path.expanduser("~/Desktop")
            if self.ui.create_subdir_var.get():
                date_str = datetime.now().strftime("%Y%m%d")
                output_dir = os.path.join(output_dir, f"视频旋转_{date_str}")
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir)
                except OSError as e:
                    messagebox.showerror("错误", f"无法创建输出目录: {e}")
                    return
        elif option == "指定目录":
            output_dir = self.ui.output_dir_var.get()
            if self.ui.create_subdir_var.get():
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
        self.ui.start_btn.config(state=tk.DISABLED)
        self.ui.stop_btn.config(state=tk.NORMAL)
        self.ui.overall_progress_bar.config(value=0)
        self.ui.current_progress_bar.config(value=0)
        
        # 在新线程中开始处理
        processing_thread = threading.Thread(target=self._process_videos_thread, args=(processing_params,))
        processing_thread.daemon = True
        processing_thread.start()
    
    def _process_videos_thread(self, processing_params):
        """处理视频的线程函数"""
        try:
            self.video_processor.start_processing(self.video_files, processing_params)
        finally:
            # 恢复UI状态
            self.root.after(0, self._restore_ui_state)
    
    def _restore_ui_state(self):
        """恢复UI状态"""
        self.processing = False
        self.ui.start_btn.config(state=tk.NORMAL)
        self.ui.stop_btn.config(state=tk.DISABLED)
    
    def save_current_settings(self):
        """保存当前设置到配置文件"""
        settings = {
            'default_rotation': self.ui.rotation_var.get(),
            'default_suffix': self.ui.suffix_var.get(),
            'default_output_option': self.ui.output_option_var.get(),
            'default_output_dir': self.ui.output_dir_var.get(),
            'create_subdir': self.ui.create_subdir_var.get(),
            'hardware_acceleration': self.ui.hw_accel_var.get(),
            'max_concurrent_tasks': self.ui.concurrent_tasks_var.get()
        }
        
        self.config_manager.update_processing_config(settings)
    
    def stop_processing(self):
        """停止处理"""
        self.stop_requested = True
        self.video_processor.stop_processing()
        self.ui.log_message("用户请求停止处理...")
        self._restore_ui_state()
    

    

    

    

    

    

    

    
    def load_config(self):
        """加载配置"""
        processing_config = self.config_manager.get_processing_config()
        
        # 设置默认值
        self.ui.rotation_var.set(processing_config.get('default_rotation', '顺时针90度'))
        self.ui.suffix_var.set(processing_config.get('default_suffix', '_rotated'))
        self.ui.output_option_var.set(processing_config.get('default_output_option', '源文件目录'))
        self.ui.output_dir_var.set(processing_config.get('default_output_dir', os.path.expanduser('~/Desktop')))
        self.ui.create_subdir_var.set(processing_config.get('create_subdir', False))
        self.ui.hw_accel_var.set(processing_config.get('hardware_acceleration', '无'))
        self.ui.concurrent_tasks_var.set(processing_config.get('max_concurrent_tasks', 1))
        
        # 更新界面状态
        self.ui.on_output_option_changed()
        self.ui.on_concurrent_changed()
    
    def save_config(self):
        """保存配置"""
        self.save_current_settings()

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