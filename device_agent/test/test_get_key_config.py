'''
测试 get_key_config 返回格式
验证全局配置是否在 global 节点下
'''
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    
    def set(self, key, value):
        self.config[key] = value
    
    def save_config(self):
        return True

# 替换真实配置管理器
import core.service.keyboard_mgr as keyboard_module
keyboard_module.config_mgr = MockConfigMgr()

from core.service.keyboard_mgr import KeyboardMgr

def test_get_key_config():
    """测试 get_key_config 方法"""
    mgr = KeyboardMgr()
    
    print("\n=== 测试 get_key_config 返回格式 ===\n")
    
    # 测试 1: 获取所有按键配置（应该包含 global 节点）
    print("测试 1: 获取所有按键配置")
    all_configs = mgr.get_key_config()
    
    print(f"返回的键：{list(all_configs.keys())}")
    print(f"数据结构:")
    import json
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
    f13_config = mgr.get_key_config("F13")
    print(f"返回的键：{list(f13_config.keys()) if f13_config else '空'}")
    print(f"数据结构:")
    print(json.dumps(f13_config, indent=2, ensure_ascii=False))
    
    assert "global" not in f13_config, "❌ 单个按键配置不应包含 global 节点"
    assert "url" in f13_config, "❌ 单个按键配置应包含 url"
    print("\n✓ 单个按键配置结构正确")
    
    # 测试 3: 获取不存在的按键配置
    print("\n\n测试 3: 获取不存在的按键配置 (F20)")
    f20_config = mgr.get_key_config("F20")
    print(f"返回：{f20_config}")
    assert f20_config == {}, "❌ 不存在的按键应返回空字典"
    print("✓ 不存在的按键返回空字典")
    
    print("\n=== 所有测试通过 ===\n")

if __name__ == "__main__":
    test_get_key_config()
