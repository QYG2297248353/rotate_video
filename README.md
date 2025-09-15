# 视频旋转工具

一个基于Python和FFmpeg的视频旋转工具，支持批量处理和硬件加速。采用模块化设计，界面友好，功能完善。

## 🌟 功能特点

- ✅ 支持多种视频格式（MP4、AVI、MOV、MKV等）
- ✅ 批量处理视频文件
- ✅ 硬件加速支持（NVENC、QSV、AMF）
- ✅ 直观的图形界面
- ✅ 实时处理进度显示
- ✅ 拖拽添加文件支持
- ✅ 配置文件自动保存
- ✅ 多线程并发处理
- ✅ 详细的日志记录

## 📁 项目结构

```
rotate_video/
├── rotate_video.py      # 主程序入口
├── ui_components.py     # UI界面组件
├── video_processor.py   # 视频处理核心
├── config_manager.py    # 配置管理
├── build.py            # 打包构建脚本
├── requirements.txt    # Python依赖
├── favicon.ico         # 程序图标
└── README.md          # 说明文档
```

## 🔧 系统要求

- **操作系统**: Windows 10/11
- **Python版本**: 3.8+
- **FFmpeg**: 程序会自动检测系统中的FFmpeg

## 📦 安装和运行

### 方法一：直接运行Python脚本

1. **克隆或下载项目**
   ```bash
   git clone <repository-url>
   cd rotate_video
   ```

2. **安装Python依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **运行程序**
   ```bash
   python rotate_video.py
   ```

### 方法二：使用打包后的可执行文件

1. **运行构建脚本**
   ```bash
   python build.py
   ```

2. **运行生成的exe文件**
   ```
   dist/视频旋转工具.exe
   ```

## 🛠️ 详细使用说明

### 基本操作流程

1. **添加视频文件**
   - 点击"📁 添加文件"按钮选择单个或多个视频文件
   - 点击"📂 添加文件夹"按钮添加整个文件夹中的视频
   - 直接拖拽文件到程序窗口（需安装tkinterdnd2）

2. **设置旋转参数**
   - 选择旋转方向：顺时针90度、逆时针90度、180度
   - 设置输出文件后缀（默认：_rotated）

3. **配置输出选项**
   - 源文件目录：输出到原文件所在目录
   - 桌面：输出到桌面
   - 指定目录：选择自定义输出目录
   - 可选择是否创建子目录

4. **高级设置**
   - 硬件加速：选择合适的硬件加速方式
   - 并发任务数：设置同时处理的文件数量

5. **开始处理**
   - 点击"🚀 开始处理"按钮
   - 查看实时进度和日志信息
   - 可随时点击"⏹ 停止"按钮中断处理

### 硬件加速说明

- **NVENC**: 适用于NVIDIA显卡（GTX 10系列及以上）
- **QSV**: 适用于Intel集成显卡或独立显卡
- **AMF**: 适用于AMD显卡
- **无**: 使用CPU软件编码（兼容性最好但速度较慢）

## 🔨 开发和构建

### 开发环境设置

1. **安装开发依赖**
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller  # 用于打包
   ```

2. **可选依赖**
   ```bash
   pip install tkinterdnd2  # 拖拽功能支持
   ```

### 构建可执行文件

项目提供了完善的构建脚本 `build.py`，具有以下功能：

- ✅ 自动检查和安装PyInstaller
- ✅ 验证必要文件存在
- ✅ 清理之前的构建文件
- ✅ 使用优化的打包参数
- ✅ 自动测试生成的可执行文件
- ✅ 显示详细的构建信息

**运行构建脚本：**
```bash
python build.py
```

**手动打包命令：**
```bash
pyinstaller --onefile --windowed --name=视频旋转工具 --icon=favicon.ico --add-data=ui_components.py;. --add-data=video_processor.py;. --add-data=config_manager.py;. --hidden-import=tkinter --hidden-import=tkinter.ttk --clean --noconfirm rotate_video.py
```

### 构建参数说明

- `--onefile`: 打包成单个exe文件
- `--windowed`: 无控制台窗口
- `--icon=favicon.ico`: 设置程序图标
- `--add-data`: 包含必要的Python模块
- `--hidden-import`: 确保tkinter相关模块被包含
- `--clean`: 清理临时文件
- `--noconfirm`: 不询问覆盖确认

## 🐛 故障排除

### 常见问题

1. **程序无法启动**
   - 检查Python版本是否为3.8+
   - 确认所有依赖已正确安装
   - 检查是否有杀毒软件误报

2. **FFmpeg相关错误**
   - 确保系统PATH中包含FFmpeg
   - 或将ffmpeg.exe放在程序同目录下

3. **拖拽功能不可用**
   - 安装tkinterdnd2库：`pip install tkinterdnd2`

4. **硬件加速不工作**
   - 检查显卡驱动是否最新
   - 确认显卡支持对应的硬件加速

5. **打包失败**
   - 确保PyInstaller已安装
   - 检查所有必要文件是否存在
   - 查看详细错误信息

### 日志文件

程序运行时会在界面底部显示详细日志，包括：
- 文件处理状态
- 错误信息
- 进度更新
- 系统信息

## 📄 许可证

MIT License - 详见LICENSE文件

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目！

## 📞 支持

如果遇到问题，请：
1. 查看本README的故障排除部分
2. 检查程序日志中的错误信息
3. 提交Issue并附上详细的错误信息和系统环境