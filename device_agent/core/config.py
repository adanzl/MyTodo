"""
配置文件读取模块
读取 config.properties 文件中的配置
"""
import os
from typing import Dict, Optional


class Config:
    """配置管理类"""
    
    def __init__(self, config_file: str = "config.properties"):
        self.config_file = config_file
        self.config: Dict[str, str] = {}
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_file):
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # 跳过空行和注释行
                    if not line or line.startswith('#'):
                        continue
                    
                    # 解析键值对
                    if '=' in line:
                        key, value = line.split('=', 1)
                        self.config[key.strip()] = value.strip()
        except Exception as e:
            print(f"读取配置文件失败: {e}")
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """获取配置值"""
        return self.config.get(key, default)
    
    def reload(self):
        """重新加载配置"""
        self.config.clear()
        self.load_config()
    
    def set(self, key: str, value: str):
        """设置配置值"""
        self.config[key] = value
    
    def save_config(self):
        """保存配置到文件"""
        try:
            # 读取原始文件内容，保留注释和格式
            lines = []
            keys_in_file = set()
            
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        stripped = line.strip()
                        # 保留空行和注释行
                        if not stripped or stripped.startswith('#'):
                            lines.append(line)
                        elif '=' in line:
                            # 解析键值对
                            key = line.split('=', 1)[0].strip()
                            keys_in_file.add(key)
                            # 如果配置中有这个键，使用新值
                            if key in self.config:
                                lines.append(f"{key}={self.config[key]}\n")
                            else:
                                lines.append(line)
                        else:
                            lines.append(line)
            
            # 添加新的配置项（不在原文件中的）
            for key, value in self.config.items():
                if key not in keys_in_file:
                    lines.append(f"{key}={value}\n")
            
            # 写入文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get_default_bluetooth_device(self) -> Optional[str]:
        """获取默认蓝牙设备地址"""
        return self.get('default_bluetooth_device')
    
    def set_default_bluetooth_device(self, address: str) -> bool:
        """设置默认蓝牙设备地址"""
        try:
            self.config['default_bluetooth_device'] = address
            return self.save_config()
        except Exception as e:
            print(f"设置默认蓝牙设备失败: {e}")
            return False


# 全局配置实例
_config_instance = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance

