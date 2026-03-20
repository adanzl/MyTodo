'''
独立测试 get_key_config 返回格式
不依赖项目其他模块
'''
from datetime import datetime, timedelta
import json

# 模拟配置管理器
class MockConfigMgr:
    def __init__(self):
        self.config = {
            'key_valid_time': '09:00',
            'key_valid_duration': '480',
            'keyboard.F13.url': 'http://example.com/f13',
            'keyboard.F13.method': 'POST',
            'keyboard.F14.url': 'http://example.com/f14',
            'keyboard.F14.method': 'GET'
        }
    
    def get(self, key, default=""):
        return self.config.get(key, default)

config_mgr = MockConfigMgr()

# 简化的日志
class MockLog:
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass
    def debug(self, msg): pass

log = MockLog()

# 常量
KEY_NAMES = [f'F{i}' for i in range(12, 20)]
DEFAULT_HTTP_METHOD = "GET"

def _get_config_key(key_name: str, suffix: str) -> str:
    return f"keyboard.{key_name}.{suffix}"

def _build_full_url(url: str) -> str:
    """简化版本，直接返回 URL"""
    return url if url.startswith(('http://', 'https://')) else url

def _parse_config_data(data_str: str) -> dict:
    try:
        return json.loads(data_str) if data_str else {}
    except:
        return {}

def _get_key_config_raw(key: str):
    url_config = config_mgr.get(_get_config_key(key, "url"))
    if not url_config:
        return None
    
    return {
        "url": url_config,
        "method": config_mgr.get(_get_config_key(key, "method"), DEFAULT_HTTP_METHOD),
        "data": config_mgr.get(_get_config_key(key, "data"), "")
    }

def _get_key_config(key: str):
    raw_config = _get_key_config_raw(key)
    if not raw_config:
        return None
    
    url_value = raw_config.get("url")
    if not url_value:
        return None
    
    full_url = _build_full_url(url_value)
    if not full_url:
        return None
    
    result = {
        "method": raw_config.get("method", DEFAULT_HTTP_METHOD),
        "url": full_url,
    }
    
    data_value = raw_config.get("data")
    if data_value:
        data = _parse_config_data(data_value)
        if data:
            result["data"] = data
    
    return result

def _build_key_config(key: str):
    return _get_key_config(key) or {}

def get_key_config(key=None):
    """获取按键配置（包含 global 节点）"""
    if key:
        if key not in KEY_NAMES:
            return {}
        return _build_key_config(key)
    else:
        # 返回所有按键配置 + 全局配置
        result = {}
        
        # 添加全局配置到 global 节点
        result["global"] = {
            "key_valid_time": config_mgr.get("key_valid_time", ""),
            "key_valid_duration": config_mgr.get("key_valid_duration", "")
        }
        
        # 添加所有按键配置
        configs = {}
        for k in KEY_NAMES:
            key_config = _build_key_config(k)
            if key_config:
                configs[k] = key_config
        
        # 只有在有按键配置时才添加到结果中
        if configs:
            result["keys"] = configs
        
        return result

# 运行测试
if __name__ == "__main__":
    print("\n=== 测试 get_key_config 返回格式 ===\n")
    
    # 测试 1: 获取所有按键配置（应该包含 global 节点）
    print("测试 1: 获取所有按键配置")
    all_configs = get_key_config()
    
    print(f"返回的键：{list(all_configs.keys())}")
    print(f"数据结构:")
    print(json.dumps(all_configs, indent=2, ensure_ascii=False))
    
    # 验证结构
    assert "global" in all_configs, "❌ 缺少 global 节点"
    assert "key_valid_time" in all_configs["global"], "❌ global 节点缺少 key_valid_time"
    assert "key_valid_duration" in all_configs["global"], "❌ global 节点缺少 key_valid_duration"
    print("\n✓ global 节点结构正确")
    
    if "keys" in all_configs:
        assert isinstance(all_configs["keys"], dict), "❌ keys 应该是字典"
        print(f"✓ keys 节点包含 {len(all_configs['keys'])} 个按键配置")
    
    # 测试 2: 获取单个按键配置（不应该有 global 节点）
    print("\n\n测试 2: 获取单个按键配置 (F13)")
    f13_config = get_key_config("F13")
    print(f"返回的键：{list(f13_config.keys()) if f13_config else '空'}")
    print(f"数据结构:")
    print(json.dumps(f13_config, indent=2, ensure_ascii=False))
    
    assert "global" not in f13_config, "❌ 单个按键配置不应包含 global 节点"
    assert "url" in f13_config, "❌ 单个按键配置应包含 url"
    print("\n✓ 单个按键配置结构正确")
    
    # 测试 3: 获取不存在的按键配置
    print("\n\n测试 3: 获取不存在的按键配置 (F20)")
    f20_config = get_key_config("F20")
    print(f"返回：{f20_config}")
    assert f20_config == {}, "❌ 不存在的按键应返回空字典"
    print("✓ 不存在的按键返回空字典")
    
    # 测试 4: 没有按键配置时的结构
    print("\n\n测试 4: 清空配置后的结构")
    config_mgr.config = {
        'key_valid_time': '10:00',
        'key_valid_duration': '60'
    }
    empty_configs = get_key_config()
    print(f"返回的键：{list(empty_configs.keys())}")
    print(f"数据结构:")
    print(json.dumps(empty_configs, indent=2, ensure_ascii=False))
    
    assert "global" in empty_configs, "❌ 即使没有按键配置也应该有 global 节点"
    assert "keys" not in empty_configs, "❌ 没有按键配置时不应包含 keys 节点"
    print("\n✓ 没有按键配置时结构正确（只有 global 节点）")
    
    print("\n=== 所有测试通过 ===\n")
