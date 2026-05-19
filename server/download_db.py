#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从远程服务器下载文件并替换本地文件
服务器配置: SSH Host Mini
下载文件:
  - data.db
  - logs/app.log
  - logs/app.log.YYYY-MM-DD (最近3天的日志)
"""

import subprocess
import os
import sys
from datetime import datetime, timedelta


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
    files_to_download = [{
        'remote': '/mnt/data/project/MyTodo/server/data.db',
        'local': os.path.join(script_dir, 'data.db'),
        'desc': '数据库文件'
    }, {
        'remote': '/mnt/data/project/MyTodo/server/logs/app.log',
        'local': os.path.join(script_dir, 'logs', 'app.log'),
        'desc': '应用日志'
    }]

    # 添加最近3天的日志文件
    today = datetime.now()
    for i in range(1, 4):  # 1, 2, 3 天前
        date = today - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        log_filename = f'app.log.{date_str}'

        files_to_download.append({
            'remote': f'/mnt/data/project/MyTodo/server/logs/{log_filename}',
            'local': os.path.join(script_dir, 'logs', log_filename),
            'desc': f'应用日志 ({date_str})'
        })

    print("=" * 60)
    print("从服务器下载文件")
    print("=" * 60)
    print(f"远程服务器: {remote_host}")
    print(f"文件数量: {len(files_to_download)}")
    print("=" * 60)

    # 确保本地目录存在
    logs_dir = os.path.join(script_dir, 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir, exist_ok=True)

    # 使用 ControlMaster 复用 SSH 连接（跨平台兼容）
    # 先建立主连接
    control_path = os.path.join('/tmp', '.ssh_ctrl_%r@%h:%p')

    print(f"\n建立 SSH 连接 ...")
    try:
        # 建立主控连接
        master_cmd = [
            'ssh', '-o', 'ControlMaster=yes', '-o', f'ControlPath={control_path}', '-o', 'ControlPersist=600',
            remote_host, 'echo connected'
        ]

        result = subprocess.run(master_cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            print(f"✗ SSH 连接失败: {result.stderr}")
            return 0, len(files_to_download)

        print("✓ SSH 连接已建立\n")

    except Exception as e:
        print(f"✗ 建立 SSH 连接失败: {e}")
        return 0, len(files_to_download)

    # 使用复用的连接下载所有文件
    success_count = 0
    fail_count = 0

    for file_info in files_to_download:
        # 确保本地目录存在
        local_dir = os.path.dirname(file_info['local'])
        if local_dir and not os.path.exists(local_dir):
            os.makedirs(local_dir, exist_ok=True)

        # 使用 ControlPath 复用连接
        cmd = ['scp', '-o', f'ControlPath={control_path}', f'{remote_host}:{file_info["remote"]}', file_info['local']]

        print(f"[{file_info['desc']}]")
        print(f"  远程: {file_info['remote']}")
        print(f"  本地: {file_info['local']}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                print(f"  ✓ 下载成功")
                if os.path.exists(file_info['local']):
                    file_size = os.path.getsize(file_info['local'])
                    if file_size > 1024 * 1024:
                        print(f"  文件大小: {file_size / (1024 * 1024):.2f} MB")
                    else:
                        print(f"  文件大小: {file_size / 1024:.2f} KB")
                success_count += 1
            else:
                print(f"  ✗ 下载失败: {result.stderr.strip()}")
                fail_count += 1

        except subprocess.TimeoutExpired:
            print(f"  ✗ 下载超时")
            fail_count += 1
        except Exception as e:
            print(f"  ✗ 错误: {e}")
            fail_count += 1

    # 关闭主控连接
    try:
        close_cmd = ['ssh', '-o', f'ControlPath={control_path}', '-O', 'exit', remote_host]
        subprocess.run(close_cmd, capture_output=True, timeout=5)
    except:
        pass

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
