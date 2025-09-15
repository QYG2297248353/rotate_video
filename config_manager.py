import json
import os
from typing import Dict, Any, Optional, Tuple, List

class ConfigManager:
    """配置管理类，负责应用程序配置的读取、保存和管理"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config_path = os.path.join(os.path.dirname(__file__), config_file)
        self.default_config = self._get_default_config()
        self.config = self._load_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "ui": {
                "window_geometry": "900x650",
                "window_min_size": [750, 500],
                "theme": "default"
            },
            "processing": {
                "default_rotation": "顺时针90度",
                "default_suffix": "_rotated",
                "default_output_option": "源文件目录",
                "default_output_dir": "~/Desktop",
                "create_subdir": False,
                "hardware_acceleration": "无",
                "max_concurrent_tasks": 1
            },
            "advanced": {
                "ffmpeg_timeout": 300,  # 5分钟超时
                "log_level": "info",
                "auto_save_config": True,
                "check_ffmpeg_on_startup": True
            },
            "recent": {
                "files": [],
                "output_directories": [],
                "max_recent_items": 10
            }
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                # 合并默认配置和加载的配置
                return self._merge_config(self.default_config, loaded_config)
            else:
                return self.default_config.copy()
        except Exception as e:
            print(f"加载配置文件失败: {e}，使用默认配置")
            return self.default_config.copy()
    
    def _merge_config(self, default: Dict[str, Any], loaded: Dict[str, Any]) -> Dict[str, Any]:
        """合并配置，确保所有默认键都存在"""
        result = default.copy()
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """获取配置值，支持点分隔的路径，如 'ui.window_geometry'"""
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any) -> None:
        """设置配置值，支持点分隔的路径"""
        keys = key_path.split('.')
        config = self.config
        
        # 导航到最后一级的父级
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # 设置值
        config[keys[-1]] = value
        
        # 如果启用了自动保存，则保存配置
        if self.get('advanced.auto_save_config', True):
            self.save_config()
    
    def get_ui_config(self) -> Dict[str, Any]:
        """获取UI相关配置"""
        return self.config.get('ui', {})
    
    def get_processing_config(self) -> Dict[str, Any]:
        """获取处理相关配置"""
        return self.config.get('processing', {})
    
    def get_advanced_config(self) -> Dict[str, Any]:
        """获取高级配置"""
        return self.config.get('advanced', {})
    
    def update_processing_config(self, settings: Dict[str, Any]) -> None:
        """更新处理配置"""
        for key, value in settings.items():
            self.set(f'processing.{key}', value)
    
    def add_recent_file(self, file_path: str) -> None:
        """添加最近使用的文件"""
        recent_files = self.get('recent.files', [])
        
        # 如果文件已存在，先移除
        if file_path in recent_files:
            recent_files.remove(file_path)
        
        # 添加到开头
        recent_files.insert(0, file_path)
        
        # 限制最大数量
        max_items = self.get('recent.max_recent_items', 10)
        recent_files = recent_files[:max_items]
        
        self.set('recent.files', recent_files)
    
    def get_recent_files(self) -> list:
        """获取最近使用的文件列表"""
        recent_files = self.get('recent.files', [])
        # 过滤掉不存在的文件
        existing_files = [f for f in recent_files if os.path.exists(f)]
        
        # 如果列表发生了变化，更新配置
        if len(existing_files) != len(recent_files):
            self.set('recent.files', existing_files)
        
        return existing_files
    
    def add_recent_output_dir(self, dir_path: str) -> None:
        """添加最近使用的输出目录"""
        recent_dirs = self.get('recent.output_directories', [])
        
        # 如果目录已存在，先移除
        if dir_path in recent_dirs:
            recent_dirs.remove(dir_path)
        
        # 添加到开头
        recent_dirs.insert(0, dir_path)
        
        # 限制最大数量
        max_items = self.get('recent.max_recent_items', 10)
        recent_dirs = recent_dirs[:max_items]
        
        self.set('recent.output_directories', recent_dirs)
    
    def get_recent_output_dirs(self) -> list:
        """获取最近使用的输出目录列表"""
        recent_dirs = self.get('recent.output_directories', [])
        # 过滤掉不存在的目录
        existing_dirs = [d for d in recent_dirs if os.path.exists(d)]
        
        # 如果列表发生了变化，更新配置
        if len(existing_dirs) != len(recent_dirs):
            self.set('recent.output_directories', existing_dirs)
        
        return existing_dirs
    
    def reset_to_default(self) -> None:
        """重置为默认配置"""
        self.config = self.default_config.copy()
        self.save_config()
    
    def export_config(self, export_path: str) -> bool:
        """导出配置到指定路径"""
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"导出配置失败: {e}")
            return False
    
    def import_config(self, import_path: str) -> bool:
        """从指定路径导入配置"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            # 合并导入的配置和默认配置
            self.config = self._merge_config(self.default_config, imported_config)
            self.save_config()
            return True
        except Exception as e:
            print(f"导入配置失败: {e}")
            return False
    
    def validate_config(self) -> Tuple[bool, List[str]]:
        """验证配置的有效性"""
        errors = []
        
        # 验证UI配置
        ui_config = self.get_ui_config()
        if 'window_geometry' in ui_config:
            geometry = ui_config['window_geometry']
            if not isinstance(geometry, str) or 'x' not in geometry:
                errors.append("无效的窗口几何配置")
        
        # 验证处理配置
        processing_config = self.get_processing_config()
        if 'max_concurrent_tasks' in processing_config:
            max_tasks = processing_config['max_concurrent_tasks']
            if not isinstance(max_tasks, int) or max_tasks < 1 or max_tasks > 16:
                errors.append("无效的最大并发任务数配置")
        
        # 验证高级配置
        advanced_config = self.get_advanced_config()
        if 'ffmpeg_timeout' in advanced_config:
            timeout = advanced_config['ffmpeg_timeout']
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                errors.append("无效的FFmpeg超时配置")
        
        return len(errors) == 0, errors
    
    def get_config_info(self) -> Dict[str, Any]:
        """获取配置信息"""
        return {
            "config_file": self.config_path,
            "config_exists": os.path.exists(self.config_path),
            "config_size": os.path.getsize(self.config_path) if os.path.exists(self.config_path) else 0,
            "last_modified": os.path.getmtime(self.config_path) if os.path.exists(self.config_path) else None,
            "is_valid": self.validate_config()[0]
        }