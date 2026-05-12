#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从远程服务器下载文件并替换本地文件
服务器配置: SSH Host Mini
下载文件:
  - data.db
  - logs/app.log
"""

import subprocess
import os
import sys
from datetime import datetime


def download_single_file(remote_host, remote_path, local_path, file_desc):
    """下载单个文件"""
    print(f"\n[{file_desc}]")
    print(f"  远程: {remote_host}:{remote_path}")
    print(f"  本地: {local_path}")
    
    try:
        # 使用 scp 命令下载文件
        cmd = ['scp', f'{remote_host}:{remote_path}', local_path]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        if result.returncode == 0:
            print(f"  ✓ 下载成功")
            if os.path.exists(local_path):
                file_size = os.path.getsize(local_path)
                if file_size > 1024 * 1024:
                    print(f"  文件大小: {file_size / (1024 * 1024):.2f} MB")
                else:
                    print(f"  文件大小: {file_size / 1024:.2f} KB")
            return True
        else:
            print(f"  ✗ 下载失败")
            print(f"  错误信息: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"  ✗ 下载超时（超过5分钟）")
        return False
    except FileNotFoundError:
        print(f"  ✗ 未找到 scp 命令，请确保已安装 OpenSSH 客户端")
        return False
    except Exception as e:
        print(f"  ✗ 发生错误: {e}")
        return False


def download_files_from_server():
    """从服务器下载多个文件"""
    # 定义路径
    remote_host = "leo@mini"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 定义要下载的文件列表
    files_to_download = [
        {
            'remote': '/mnt/data/project/MyTodo/server/data.db',
            'local': os.path.join(script_dir, 'data.db'),
            'desc': '数据库文件'
        },
        {
            'remote': '/mnt/data/project/MyTodo/server/logs/app.log',
            'local': os.path.join(script_dir, 'logs', 'app.log'),
            'desc': '应用日志'
        }
    ]
    
    print("=" * 60)
    print("从服务器下载文件")
    print("=" * 60)
    print(f"远程服务器: {remote_host}")
    print(f"文件数量: {len(files_to_download)}")
    print("=" * 60)
    
    success_count = 0
    fail_count = 0
    
    for file_info in files_to_download:
        # 确保本地目录存在
        local_dir = os.path.dirname(file_info['local'])
        if local_dir and not os.path.exists(local_dir):
            os.makedirs(local_dir, exist_ok=True)
        
        if download_single_file(remote_host, file_info['remote'], file_info['local'], file_info['desc']):
            success_count += 1
        else:
            fail_count += 1
    
    return success_count, fail_count


def main():
    """主函数"""
    try:
        success_count, fail_count = download_files_from_server()
        
        print("\n" + "=" * 60)
        print("下载结果汇总")
        print("=" * 60)
        print(f"成功: {success_count} 个文件")
        print(f"失败: {fail_count} 个文件")
        print("=" * 60)
        
        if fail_count == 0:
            print("✓ 所有文件下载成功！")
            sys.exit(0)
        elif success_count > 0:
            print("⚠ 部分文件下载成功，请检查失败的文件")
            sys.exit(1)
        else:
            print("✗ 所有文件下载失败！请检查网络连接和SSH配置")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n操作被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
