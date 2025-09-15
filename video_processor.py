import os
import subprocess
import threading
import time
from datetime import datetime
import sys

class VideoProcessor:
    """视频处理类，负责FFmpeg相关的视频旋转操作"""
    
    def __init__(self, ui_callback=None):
        self.ui_callback = ui_callback  # UI回调函数，用于更新界面
        self.active_processes = []  # 存储活跃的进程
        self.is_processing = False
        self.total_files = 0
        self.completed_files = 0
        self.start_time = None
        self.ffmpeg_path = self.find_ffmpeg()  # 查找FFmpeg路径
        self.ffprobe_path = self.find_ffprobe()  # 查找FFprobe路径
    
    def get_rotation_filter(self, rotation):
        """根据旋转方向返回FFmpeg滤镜参数"""
        rotation_filters = {
            "顺时针90度": "transpose=1",
            "逆时针90度": "transpose=2", 
            "180度": "transpose=1,transpose=1"
        }
        return rotation_filters.get(rotation, "transpose=1")
    
    def get_hw_accel_params(self, hw_accel):
        """根据硬件加速选项返回FFmpeg参数"""
        if hw_accel == "nvenc":
            return ["-hwaccel", "cuda", "-c:v", "h264_nvenc"]
        elif hw_accel == "qsv":
            return ["-hwaccel", "qsv", "-c:v", "h264_qsv"]
        elif hw_accel == "amf":
            return ["-hwaccel", "d3d11va", "-c:v", "h264_amf"]
        else:
            return ["-c:v", "libx264"]
    
    def get_output_path(self, input_file, suffix, output_option, output_dir, create_subdir):
        """生成输出文件路径"""
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        ext = os.path.splitext(input_file)[1]
        output_filename = f"{base_name}{suffix}{ext}"
        
        if output_option == "源文件目录":
            output_path = os.path.join(os.path.dirname(input_file), output_filename)
        elif output_option == "桌面":
            desktop_path = os.path.expanduser("~/Desktop")
            if create_subdir:
                date_str = datetime.now().strftime("%Y%m%d")
                output_dir = os.path.join(desktop_path, f"rotated_videos_{date_str}")
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, output_filename)
            else:
                output_path = os.path.join(desktop_path, output_filename)
        else:  # 指定目录
            if create_subdir:
                date_str = datetime.now().strftime("%Y%m%d")
                output_dir = os.path.join(output_dir, f"rotated_videos_{date_str}")
                os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, output_filename)
        
        return output_path
    
    def reencode_video(self, input_file, output_file, rotation, hw_accel, progress_callback=None):
        """重新编码视频文件"""
        # 首先尝试使用指定的硬件加速
        success, error = self._try_encode(input_file, output_file, rotation, hw_accel)
        
        # 如果硬件加速失败且不是软件编码，则回退到软件编码
        if not success and hw_accel != "software":
            if "进程被异常终止" in str(error) or "4294967274" in str(error):
                if self.ui_callback:
                    self.ui_callback('log', f"⚠️ 硬件加速失败，回退到软件编码: {os.path.basename(input_file)}")
                success, error = self._try_encode(input_file, output_file, rotation, "software")
        
        return success, error
    
    def _try_encode(self, input_file, output_file, rotation, hw_accel):
        """尝试编码视频文件"""
        try:
            # 构建FFmpeg命令，给文件路径加双引号以处理中文、空格和特殊字符
            cmd = [self.ffmpeg_path, "-i", f'"{input_file}"']
            
            # 添加硬件加速参数
            hw_params = self.get_hw_accel_params(hw_accel)
            cmd.extend(hw_params)
            
            # 添加旋转滤镜
            rotation_filter = self.get_rotation_filter(rotation)
            cmd.extend(["-vf", rotation_filter])
            
            # 添加音频复制和输出文件，输出路径也加双引号
            cmd.extend(["-c:a", "copy", "-y", f'"{output_file}"'])
            
            if self.ui_callback:
                accel_type = "软件编码" if hw_accel == "software" else f"{hw_accel.upper()}硬件加速"
                self.ui_callback('log', f"开始处理: {os.path.basename(input_file)} ({accel_type})")
                self.ui_callback('log', f"命令: {' '.join(cmd)}")
            
            # 启动进程
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # 将进程添加到活跃进程列表
            self.active_processes.append(process)
            
            try:
                # 等待进程完成
                stdout, stderr = process.communicate()
                
                if process.returncode == 0:
                    if self.ui_callback:
                        self.ui_callback('log', f"✅ 完成: {os.path.basename(output_file)}")
                    return True, None
                else:
                    # 处理错误信息
                    error_details = []
                    if stderr and stderr.strip():
                        error_details.append(f"错误输出: {stderr.strip()}")
                    if stdout and stdout.strip():
                        error_details.append(f"标准输出: {stdout.strip()}")
                    
                    # 根据返回码提供更具体的错误信息
                    if process.returncode == 4294967274 or process.returncode == -1073741818:
                        error_details.append("进程被异常终止，可能原因: 1)硬件加速不支持 2)文件路径包含特殊字符 3)磁盘空间不足")
                    elif process.returncode == 1:
                        error_details.append("FFmpeg参数错误或文件格式不支持")
                    
                    error_msg = f"FFmpeg错误 (返回码: {process.returncode})" + (f" - {'; '.join(error_details)}" if error_details else "")
                    
                    if self.ui_callback:
                        self.ui_callback('log', f"❌ 失败: {os.path.basename(input_file)} - {error_msg}")
                    return False, error_msg
            
            except Exception as e:
                error_msg = f"处理异常: {str(e)}"
                if self.ui_callback:
                    self.ui_callback('log', f"❌ 异常: {os.path.basename(input_file)} - {error_msg}")
                return False, error_msg
            
            finally:
                # 从活跃进程列表中移除
                if process in self.active_processes:
                    self.active_processes.remove(process)
        
        except Exception as e:
            error_msg = f"启动处理失败: {str(e)}"
            if self.ui_callback:
                self.ui_callback('log', f"❌ 启动失败: {os.path.basename(input_file)} - {error_msg}")
            return False, error_msg
    
    def process_files(self, files, rotation, suffix, output_option, output_dir, create_subdir, hw_accel, max_concurrent=1):
        """批量处理视频文件"""
        self.is_processing = True
        self.total_files = len(files)
        self.completed_files = 0
        self.start_time = time.time()
        
        if self.ui_callback:
            self.ui_callback('status', f"开始处理 {self.total_files} 个文件...")
            self.ui_callback('progress', {'overall': 0, 'current': 0})
        
        # 使用线程池进行并发处理
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def process_single_file(file_path):
            """处理单个文件的内部函数"""
            if not self.is_processing:
                return file_path, False, "处理已停止"
            
            try:
                output_path = self.get_output_path(file_path, suffix, output_option, output_dir, create_subdir)
                
                # 确保输出目录存在
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                success, error = self.reencode_video(file_path, output_path, rotation, hw_accel)
                return file_path, success, error
            
            except Exception as e:
                return file_path, False, str(e)
        
        successful_files = []
        failed_files = []
        
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            # 提交所有任务
            future_to_file = {executor.submit(process_single_file, file_path): file_path for file_path in files}
            
            # 处理完成的任务
            for future in as_completed(future_to_file):
                if not self.is_processing:
                    break
                
                file_path, success, error = future.result()
                self.completed_files += 1
                
                if success:
                    successful_files.append(file_path)
                else:
                    failed_files.append((file_path, error))
                
                # 更新进度
                overall_progress = (self.completed_files / self.total_files) * 100
                if self.ui_callback:
                    self.ui_callback('progress', {'overall': overall_progress, 'current': 100})
                    
                    # 计算剩余时间
                    if self.completed_files > 0:
                        elapsed_time = time.time() - self.start_time
                        avg_time_per_file = elapsed_time / self.completed_files
                        remaining_files = self.total_files - self.completed_files
                        remaining_time = avg_time_per_file * remaining_files
                        
                        hours = int(remaining_time // 3600)
                        minutes = int((remaining_time % 3600) // 60)
                        seconds = int(remaining_time % 60)
                        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                        
                        self.ui_callback('time', f"剩余时间: {time_str}")
                        self.ui_callback('status', f"已完成 {self.completed_files}/{self.total_files} 个文件")
        
        # 处理完成
        self.is_processing = False
        
        if self.ui_callback:
            if successful_files:
                self.ui_callback('log', f"\n🎉 处理完成! 成功: {len(successful_files)} 个文件")
            
            if failed_files:
                self.ui_callback('log', f"❌ 失败: {len(failed_files)} 个文件")
                for file_path, error in failed_files:
                    self.ui_callback('log', f"  - {os.path.basename(file_path)}: {error}")
            
            self.ui_callback('status', "处理完成")
            self.ui_callback('time', "剩余时间: --:--:--")
            self.ui_callback('progress', {'overall': 100, 'current': 0})
        
        return successful_files, failed_files
    
    def start_processing(self, files, processing_params):
        """开始处理视频文件"""
        if self.ui_callback:
            self.ui_callback('log', f"🚀 开始处理 {len(files)} 个视频文件...")
        
        # 调用process_files方法
        return self.process_files(
            files,
            processing_params['rotation'],
            processing_params['suffix'],
            processing_params['output_option'],
            processing_params['output_dir'],
            processing_params['create_subdir'],
            processing_params['hw_accel'],
            processing_params['concurrent_tasks']
        )
    
    def stop_processing(self):
        """停止所有正在进行的处理"""
        self.is_processing = False
        
        # 终止所有活跃的进程
        for process in self.active_processes[:]:
            try:
                if process and process.poll() is None:
                    process.terminate()
                    # 等待进程终止，如果超时则强制杀死
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
            except Exception as e:
                if self.ui_callback:
                    self.ui_callback('log', f"停止进程时出错: {str(e)}")
        
        # 清空活跃进程列表
        self.active_processes.clear()
        
        if self.ui_callback:
            self.ui_callback('log', "⏹ 处理已停止")
            self.ui_callback('status', "已停止")
    
    def find_ffmpeg(self):
        """查找FFmpeg可执行文件路径"""
        # 优先级：1. 打包的资源 2. 程序同目录 3. 系统环境变量
        
        # 1. 检查打包的资源（PyInstaller）
        if getattr(sys, 'frozen', False):
            # 运行在打包的可执行文件中
            bundle_dir = sys._MEIPASS
            ffmpeg_bundled = os.path.join(bundle_dir, 'ffmpeg.exe')
            if os.path.exists(ffmpeg_bundled):
                return ffmpeg_bundled
        
        # 2. 检查程序同目录
        if getattr(sys, 'frozen', False):
            # 可执行文件目录
            exe_dir = os.path.dirname(sys.executable)
        else:
            # 脚本文件目录
            exe_dir = os.path.dirname(os.path.abspath(__file__))
        
        ffmpeg_local = os.path.join(exe_dir, 'ffmpeg.exe')
        if os.path.exists(ffmpeg_local):
            return ffmpeg_local
        
        # 3. 使用系统环境变量中的ffmpeg
        return 'ffmpeg'
    
    def find_ffprobe(self):
        """查找FFprobe可执行文件路径"""
        # 优先级：1. 打包的资源 2. 程序同目录 3. 系统环境变量
        
        # 1. 检查打包的资源（PyInstaller）
        if getattr(sys, 'frozen', False):
            # 运行在打包的可执行文件中
            bundle_dir = sys._MEIPASS
            ffprobe_bundled = os.path.join(bundle_dir, 'ffprobe.exe')
            if os.path.exists(ffprobe_bundled):
                return ffprobe_bundled
        
        # 2. 检查程序同目录
        if getattr(sys, 'frozen', False):
            # 可执行文件目录
            exe_dir = os.path.dirname(sys.executable)
        else:
            # 脚本文件目录
            exe_dir = os.path.dirname(os.path.abspath(__file__))
        
        ffprobe_local = os.path.join(exe_dir, 'ffprobe.exe')
        if os.path.exists(ffprobe_local):
            return ffprobe_local
        
        # 3. 使用系统环境变量中的ffprobe
        return 'ffprobe'
    
    def check_ffmpeg(self):
        """检查FFmpeg是否可用"""
        try:
            result = subprocess.run([self.ffmpeg_path, "-version"], 
                                  capture_output=True, 
                                  text=True, 
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            return result.returncode == 0
        except FileNotFoundError:
            return False
        except Exception:
            return False