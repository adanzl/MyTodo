#!/usr/bin/env python
"""
测试 TTS 任务执行（在 Flask 环境中）
在 Flask 应用上下文中测试 TTS 功能，模拟真实环境
"""
import sys
import os
import time
import tempfile
import shutil

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 应用 gevent monkey patching（不 patch subprocess）
from gevent import monkey

monkey.patch_all(subprocess=False, thread=False, queue=False)

from dotenv import load_dotenv

load_dotenv()

from core import create_app
from core.services.tts_mgr import tts_mgr
from core.config import TASK_STATUS_PENDING, TASK_STATUS_PROCESSING, TASK_STATUS_SUCCESS, TASK_STATUS_FAILED


def test_tts_task_execution():
    """测试 TTS 任务执行"""
    print("=" * 60)
    print("测试 TTS 任务执行（在 Flask 环境中）")
    print("=" * 60)

    # 使用临时目录
    temp_dir = tempfile.mkdtemp(prefix="tts_test_")
    print(f"\n使用临时目录: {temp_dir}")

    try:
        # 临时修改 TTS_BASE_DIR
        import core.services.tts_mgr as tts_mgr_module
        original_base_dir = tts_mgr_module.TTS_BASE_DIR
        tts_mgr_module.TTS_BASE_DIR = temp_dir

        # 创建 Flask 应用并在应用上下文中运行测试
        print("\n[步骤 0] 创建 Flask 应用...")
        app = create_app()
        app.config['TESTING'] = True

        # 在 Flask 应用上下文中运行测试
        with app.app_context():
            print("✓ Flask 应用上下文已创建")

            # 等待一下让应用完全初始化
            time.sleep(0.5)

            # 创建测试任务
            print("\n[步骤 1] 创建 TTS 任务...")
            code, msg, task_id = tts_mgr.create_task(text="你好，这是一个测试文本。", name="Flask 环境 TTS 测试任务")

            if code != 0:
                print(f"✗ 创建任务失败: {msg}")
                return False

            print(f"✓ 任务创建成功，task_id: {task_id}")

            # 检查任务状态
            task = tts_mgr.get_task(task_id)
            assert task is not None, "应该能获取到任务"
            assert task['status'] == TASK_STATUS_PENDING, f"任务状态应该是 pending，但是: {task['status']}"
            print(f"✓ 任务状态: {task['status']}")

            # 启动任务
            print("\n[步骤 2] 启动 TTS 任务...")
            code, msg = tts_mgr.start_task(task_id)

            if code != 0:
                print(f"✗ 启动任务失败: {msg}")
                return False

            print(f"✓ 任务已启动: {msg}")

            # 等待任务完成
            print("\n[步骤 3] 等待任务完成...")
            deadline = 5.0  # 最多等待 5 秒
            start = time.time()
            last_status = None
            check_count = 0

            while True:
                elapsed = time.time() - start
                if elapsed >= deadline:
                    print(f"✗ 等待超时（{deadline}秒）")
                    task = tts_mgr.get_task(task_id)
                    if task:
                        print(f"  最终状态: {task['status']}")
                        if task.get('error_message'):
                            print(f"  错误信息: {task['error_message']}")
                    return False

                task = tts_mgr.get_task(task_id)
                if task is None:
                    print("✗ 无法获取任务信息")
                    return False

                status = task['status']
                if status != last_status:
                    print(f"  状态变化: {last_status} -> {status} ({elapsed:.1f}秒)")
                    last_status = status

                check_count += 1
                if check_count % 2 == 0:  # 每 1 秒打印一次进度
                    print(f"  等待中... ({elapsed:.1f}秒)")

                if status == TASK_STATUS_SUCCESS:
                    print(f"✓ 任务完成！状态: {status} ({elapsed:.1f}秒)")
                    break
                elif status == TASK_STATUS_FAILED:
                    error_msg = task.get('error_message', '未知错误')
                    print(f"✗ 任务失败！状态: {status}, 错误: {error_msg} ({elapsed:.1f}秒)")
                    return False

                time.sleep(0.5)

            # 检查最终状态
            task = tts_mgr.get_task(task_id)
            if task is None:
                print("✗ 无法获取任务信息")
                return False

            if task['status'] != TASK_STATUS_SUCCESS:
                print(f"✗ 任务未完成，状态: {task['status']}")
                if task.get('error_message'):
                    print(f"  错误信息: {task['error_message']}")
                return False

            # 检查输出文件
            print("\n[步骤 4] 检查输出文件...")
            output_file = task.get('output_file')
            if output_file and os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                print(f"✓ 输出文件存在: {output_file}")
                print(f"  文件大小: {file_size} 字节")
                if file_size > 0:
                    print("✓ 文件大小正常")
                    return True
                else:
                    print("✗ 文件大小为 0")
                    return False
            else:
                print(f"✗ 输出文件不存在: {output_file}")
                return False

    except Exception as e:
        print(f"\n✗ 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 清理临时目录
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                print(f"\n✓ 已清理临时目录: {temp_dir}")
        except Exception as e:
            print(f"\n⚠ 清理临时目录失败: {e}")


if __name__ == "__main__":
    print("\n开始测试 TTS 任务执行（在 Flask 环境中）...\n")

    success = test_tts_task_execution()

    print("\n" + "=" * 60)
    print("测试结果")
    print("=" * 60)
    if success:
        print("✓ TTS 任务执行测试通过！")
        sys.exit(0)
    else:
        print("✗ TTS 任务执行测试失败！")
        sys.exit(1)
