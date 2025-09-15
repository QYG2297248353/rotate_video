import os
import subprocess
import sys
import shutil
from pathlib import Path

def check_dependencies():
    """检查必要的依赖"""
    print("🔍 检查依赖...")
    
    # 检查pyinstaller
    try:
        import PyInstaller
        print(f"✅ PyInstaller 已安装 (版本: {PyInstaller.__version__})")
    except ImportError:
        print("❌ PyInstaller 未安装，正在安装...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)
        print("✅ PyInstaller 安装完成")
    
    # 检查必要文件
    required_files = ['rotate_video.py', 'ui_components.py', 'video_processor.py', 'config_manager.py']
    for file in required_files:
        if not os.path.exists(file):
            print(f"❌ 缺少必要文件: {file}")
            sys.exit(1)
        print(f"✅ 找到文件: {file}")

def clean_build():
    """清理之前的构建文件"""
    print("🧹 清理构建文件...")
    
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"✅ 清理目录: {dir_name}")
    
    # 清理.pyc文件
    for pyc_file in Path('.').rglob('*.pyc'):
        pyc_file.unlink()
    
    # 清理.spec文件
    spec_files = list(Path('.').glob('*.spec'))
    for spec_file in spec_files:
        spec_file.unlink()
        print(f"✅ 清理文件: {spec_file}")

def build_executable():
    """构建可执行文件"""
    print("🚀 开始构建可执行文件...")
    
    # 构建命令
    cmd = [
        'pyinstaller',
        '--onefile',                    # 打包成单个文件
        '--windowed',                   # 无控制台窗口
        '--name=视频旋转工具',           # 可执行文件名称
        '--icon=favicon.ico',           # 图标文件
        '--add-data=ui_components.py;.',     # 添加UI组件模块
        '--add-data=video_processor.py;.',   # 添加视频处理模块
        '--add-data=config_manager.py;.',    # 添加配置管理模块
        '--hidden-import=tkinter',           # 确保tkinter被包含
        '--hidden-import=tkinter.ttk',       # 确保ttk被包含
        '--hidden-import=tkinter.filedialog', # 确保文件对话框被包含
        '--hidden-import=tkinter.messagebox', # 确保消息框被包含
        '--clean',                      # 清理临时文件
        '--noconfirm',                  # 不询问覆盖
        'rotate_video.py'               # 主入口文件
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ 打包完成！")
        print(f"📁 可执行文件位于: {os.path.abspath('dist')}")
        
        # 检查生成的文件
        exe_path = os.path.join('dist', '视频旋转工具.exe')
        if os.path.exists(exe_path):
            file_size = os.path.getsize(exe_path) / (1024 * 1024)  # MB
            print(f"📊 文件大小: {file_size:.1f} MB")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 打包失败：{e}")
        if e.stderr:
            print(f"错误详情：{e.stderr}")
        return False

def test_executable():
    """测试可执行文件"""
    exe_path = os.path.join('dist', '视频旋转工具.exe')
    if not os.path.exists(exe_path):
        print("❌ 可执行文件不存在")
        return False
    
    print("🧪 测试可执行文件...")
    try:
        # 简单测试：启动程序并立即关闭
        process = subprocess.Popen([exe_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # 等待一秒钟让程序启动
        import time
        time.sleep(1)
        process.terminate()
        process.wait(timeout=5)
        print("✅ 可执行文件测试通过")
        return True
    except Exception as e:
        print(f"❌ 可执行文件测试失败：{e}")
        return False

def main():
    """主函数"""
    print("🎯 视频旋转工具 - 构建脚本")
    print("=" * 40)
    
    try:
        # 1. 检查依赖
        check_dependencies()
        print()
        
        # 2. 清理构建文件
        clean_build()
        print()
        
        # 3. 构建可执行文件
        if build_executable():
            print()
            
            # 4. 测试可执行文件
            if test_executable():
                print()
                print("🎉 构建完成！")
                print(f"📁 可执行文件路径: {os.path.abspath(os.path.join('dist', '视频旋转工具.exe'))}")
                print("💡 提示: 可以将exe文件复制到任意位置使用")
            else:
                print("⚠️  构建完成但测试失败，请手动测试可执行文件")
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n❌ 用户取消构建")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 构建过程中发生错误：{e}")
        sys.exit(1)

if __name__ == '__main__':
    main()