#!/usr/bin/env python3
"""
测试 PDF 上传接口
"""
import requests
import os
import sys

# 测试文件路径
test_file = r"C:\Users\adanz\Downloads\MHE_RDG_Wonders_Teachers_Edition_Grade1_Unit4.pdf"
test_file = r"C:\Users\adanz\Downloads\test_10mb.pdf"

# API 地址
api_url = "http://192.168.50.171:8848/api/pdf/upload"

def test_upload():
    """测试上传文件"""
    if not os.path.exists(test_file):
        print(f"错误：文件不存在: {test_file}")
        return
    
    file_size = os.path.getsize(test_file)
    file_size_mb = file_size / 1024 / 1024
    print(f"文件大小: {file_size_mb:.2f} MB")
    print(f"开始上传到: {api_url}")
    
    try:
        with open(test_file, 'rb') as f:
            files = {'file': (os.path.basename(test_file), f, 'application/pdf')}
            
            # 使用流式上传，显示进度
            response = requests.post(
                api_url,
                files=files,
                timeout=600,  # 10分钟超时
                stream=True
            )
            
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    print("[OK] 上传成功!")
                    print(f"文件信息: {result.get('data')}")
                    return 0
                else:
                    print(f"[ERROR] 上传失败: {result.get('msg')}")
                    return 1
            else:
                print(f"[ERROR] HTTP 错误: {response.status_code}")
                print(f"响应内容: {response.text[:500]}")
                return 1
                
    except requests.exceptions.Timeout:
        print("[ERROR] 上传超时")
        return 1
    except requests.exceptions.ConnectionError as e:
        print(f"[ERROR] 连接错误: {e}")
        return 1
    except Exception as e:
        print(f"[ERROR] 错误: {e}")
        return 1
    
    return 1

if __name__ == "__main__":
    sys.exit(test_upload() or 0)

