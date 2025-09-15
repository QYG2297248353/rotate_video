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
        
        # 检查FFmpeg是否可用
        self.ffmpeg_path = self.find_ffmpeg()
        if not self.ffmpeg_path:
            messagebox.showerror("错误", "未找到FFmpeg，请确保已安装FFmpeg并添加到系统PATH中")
            sys.exit(1)
            
        # 创建界面
        self.create_widgets()
        
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
    
    def run_ffmpeg(self, cmd):
        """运行FFmpeg命令并处理Windows路径问题"""
        # 确保所有路径都用双引号括起来，避免空格问题
        formatted_cmd = []
        for part in cmd:
            if os.path.exists(part) or (part.startswith('-') and ':' in part):
                # 处理中文字符路径问题
                formatted_cmd.append(part)
            else:
                formatted_cmd.append(part)
                
        # 使用找到的ffmpeg路径
        if formatted_cmd[0] == "ffmpeg":
            formatted_cmd[0] = self.ffmpeg_path
            
        # 在Windows上使用shell=False避免编码问题
        try:
            return subprocess.Popen(
                formatted_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace'
            )
        except:
            # 如果utf-8编码失败，尝试使用默认编码
            return subprocess.Popen(
                formatted_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
    
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
        settings_frame = ttk.LabelFrame(main_frame, text="旋转设置", padding="5")
        settings_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N), pady=5)
        settings_frame.columnconfigure(1, weight=1)
        
        # 旋转方向选择
        ttk.Label(settings_frame, text="旋转方向:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.rotation_var = tk.StringVar(value="顺时针90度")
        rotation_frame = ttk.Frame(settings_frame)
        rotation_frame.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Radiobutton(rotation_frame, text="顺时针90度", variable=self.rotation_var, value="顺时针90度").pack(side=tk.LEFT)
        ttk.Radiobutton(rotation_frame, text="逆时针90度", variable=self.rotation_var, value="逆时针90度").pack(side=tk.LEFT)
        ttk.Radiobutton(rotation_frame, text="180度", variable=self.rotation_var, value="180度").pack(side=tk.LEFT)
        
        # 输出设置
        ttk.Label(settings_frame, text="输出后缀:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.suffix_var = tk.StringVar(value="_rotated")
        ttk.Entry(settings_frame, textvariable=self.suffix_var, width=15).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(settings_frame, text="输出目录:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.output_dir_var = tk.StringVar(value=os.path.expanduser("~/Desktop"))
        ttk.Entry(settings_frame, textvariable=self.output_dir_var, width=30).grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Button(settings_frame, text="浏览", command=self.select_output_dir).grid(row=2, column=2, padx=5, pady=5)
        
        # 进度区域
        progress_frame = ttk.LabelFrame(main_frame, text="处理进度", padding="5")
        progress_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(progress_frame, textvariable=self.status_var).grid(row=1, column=0, sticky=tk.W, pady=2)
        
        self.time_var = tk.StringVar(value="剩余时间: --:--:--")
        ttk.Label(progress_frame, textvariable=self.time_var).grid(row=1, column=1, sticky=tk.E, pady=2)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        self.start_btn = ttk.Button(button_frame, text="开始处理", command=self.start_processing)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="停止", command=self.stop_processing, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="5")
        log_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
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
            extensions = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v')
            for root_dir, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(extensions):
                        self.video_files.append(os.path.join(root_dir, file))
            self.update_file_list()
    
    def clear_list(self):
        """清空文件列表"""
        self.video_files = []
        self.update_file_list()
    
    def update_file_list(self):
        """更新文件列表显示"""
        self.file_listbox.delete(0, tk.END)
        for file in self.video_files:
            self.file_listbox.insert(tk.END, os.path.basename(file))
    
    def select_output_dir(self):
        """选择输出目录"""
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            self.output_dir_var.set(directory)
    
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
        
        # 检查输出目录
        output_dir = self.output_dir_var.get()
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
        self.progress_bar.config(value=0)
        
        # 开始处理线程
        thread = threading.Thread(target=self.process_videos)
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
    
    def process_videos(self):
        """处理所有视频"""
        total_files = len(self.video_files)
        processed_files = 0
        start_time = time.time()
        
        for i, input_file in enumerate(self.video_files):
            if self.stop_requested:
                break
            
            # 更新状态
            self.status_var.set(f"处理中: {os.path.basename(input_file)} ({i+1}/{total_files})")
            self.progress_bar.config(value=(i / total_files) * 100)
            
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
        self.progress_bar.config(value=100)
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
            # 生成输出文件名
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            ext = os.path.splitext(input_file)[1]
            suffix = self.suffix_var.get()
            output_file = os.path.join(self.output_dir_var.get(), f"{base_name}{suffix}{ext}")
            
            # 检查文件是否已存在
            counter = 1
            original_output = output_file
            while os.path.exists(output_file):
                if not self.confirm_overwrite(output_file):
                    return False  # 用户选择不覆盖
                break  # 用户选择覆盖，继续处理
            
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
                        self.progress_bar.config(value=progress)
            
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
                    self.output_dir_var.set(config.get('output_dir', os.path.expanduser("~/Desktop")))
            except:
                pass
    
    def save_config(self):
        """保存配置"""
        config = {
            'rotation': self.rotation_var.get(),
            'suffix': self.suffix_var.get(),
            'output_dir': self.output_dir_var.get()
        }
        
        config_path = os.path.join(os.path.expanduser("~"), ".video_rotator_config.json")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_message(f"保存配置失败: {str(e)}")

def main():
    """主函数"""
    root = tk.Tk()
    app = VideoRotator(root)
    root.mainloop()

if __name__ == "__main__":
    main()