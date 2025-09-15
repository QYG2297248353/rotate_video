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
        
        # 创建界面
        self.ui = VideoRotatorUI(self.root, self)
        
        # 检查FFmpeg是否可用
        if not self.video_processor.check_ffmpeg():
            messagebox.showerror("错误", "未找到FFmpeg，请确保已安装FFmpeg并添加到系统PATH中，或将ffmpeg.exe放在程序目录下")
            sys.exit(1)
            
        # 加载配置
        self.load_config()
    

    
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
            # 使用平滑的进度条更新
            if 'overall' in data:
                self._smooth_progress_update(self.ui.overall_progress_bar, data['overall'])
            if 'current' in data:
                self._smooth_progress_update(self.ui.current_progress_bar, data['current'])
            self.root.update_idletasks()
    
    def _smooth_progress_update(self, progress_bar, target_value):
        """平滑更新进度条"""
        current_value = progress_bar['value']
        if abs(target_value - current_value) > 0.1:  # 只有变化足够大时才进行平滑更新
            # 计算步长，让进度条更新更平滑
            steps = max(1, int(abs(target_value - current_value) / 2))
            step_size = (target_value - current_value) / steps
            
            def update_step(step):
                if step <= steps:
                    new_value = current_value + (step_size * step)
                    progress_bar['value'] = new_value
                    self.root.update_idletasks()
                    if step < steps:
                        self.root.after(10, lambda: update_step(step + 1))
                else:
                    progress_bar['value'] = target_value
            
            update_step(1)
        else:
            progress_bar['value'] = target_value
    

    
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