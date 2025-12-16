"""
PDF 解密工具
用于对有密码保护的 PDF 进行解密，包括能打开但不能编辑/打印的权限保护

使用 pikepdf 实现（对加密 PDF 支持更好）
"""
import os
from typing import Optional, Tuple, Callable

import pikepdf

try:
    from core.log_config import root_logger
    log = root_logger()
except Exception as e:
    import logging
    log = logging.getLogger(__name__)


def decrypt_pdf(input_path: str,
                output_path: str,
                password: Optional[str] = None,
                password_callback: Optional[Callable[[], str]] = None) -> Tuple[int, str]:
    """
    解密 PDF 文件
    
    :param input_path: 输入 PDF 文件路径
    :param output_path: 输出 PDF 文件路径
    :param password: 密码（可选），如果提供则直接使用，否则通过 callback 获取
    :param password_callback: 密码获取回调函数，当需要密码时调用，返回密码字符串
    :return: (错误码, 消息)，0 表示成功，-1 表示失败
    """
    # 验证输入文件
    if not input_path or not os.path.exists(input_path):
        error_msg = f"无效的输入文件路径: {input_path}"
        log.error(f"[PDF] {error_msg}")
        return -1, error_msg

    # 验证输出目录
    output_dir = os.path.dirname(output_path)
    if not output_path or not os.path.exists(output_dir):
        error_msg = f"无效的输出文件路径或目录不存在: {output_path}"
        log.error(f"[PDF] {error_msg}")
        return -1, error_msg

    try:
        return _decrypt_with_pikepdf(input_path, output_path, password, password_callback)
    except Exception as e:
        error_msg = f"PDF 解密失败: {str(e)}"
        log.error(f"[PDF] {error_msg}")
        return -1, error_msg


def _decrypt_with_pikepdf(
    input_path: str,
    output_path: str,
    password: Optional[str] = None,
    password_callback: Optional[Callable[[], str]] = None
) -> Tuple[int, str]:
    """使用 pikepdf 解密 PDF"""
    # 如果明确提供了密码（包括空字符串），使用该密码
    if password is not None:
        try:
            with pikepdf.open(input_path, password=password) as pdf:
                pdf.save(output_path)
        except pikepdf.PasswordError:
            error_msg = "密码错误"
            log.error(f"[PDF] {error_msg}")
            return -1, error_msg
    else:
        # 先尝试无密码打开（处理无密码的 PDF）
        try:
            with pikepdf.open(input_path) as pdf:
                pdf.save(output_path)
        except pikepdf.PasswordError:
            # PDF 需要密码，通过 callback 获取
            if not password_callback:
                error_msg = "PDF 需要密码，但未提供密码或密码回调函数"
                log.error(f"[PDF] {error_msg}")
                return -1, error_msg
            
            # 尝试解密，如果密码错误会抛出异常
            while True:
                password = password_callback()
                if password is None:
                    error_msg = "未提供密码"
                    log.error(f"[PDF] {error_msg}")
                    return -1, error_msg
                
                try:
                    with pikepdf.open(input_path, password=password) as pdf:
                        pdf.save(output_path)
                    break
                except pikepdf.PasswordError:
                    log.warning("[PDF] 密码错误，请重试")
                    continue
    
    log.info(f"[PDF] 解密成功，保存到: {output_path}")
    return 0, "PDF 解密成功"


if __name__ == '__main__':
    """
    命令行工具入口
    用于交互式解密 PDF
    """
    import sys

    # 默认文件路径（仅用于命令行工具）
    default_input = "/Users/zhaolin/Downloads/ico_o.pdf"
    default_output = "/Users/zhaolin/Downloads/t.pdf"

    print("=========== PDF 解密工具 ===========")

    # 获取输入文件路径
    input_path = input(f"请输入输入 PDF 文件路径（默认: {default_input}）: ").strip()
    if not input_path:
        input_path = default_input

    # 获取输出文件路径
    output_path = input(f"请输入输出 PDF 文件路径（默认: {default_output}）: ").strip()
    if not output_path:
        output_path = default_output

    # 定义密码获取回调函数（仅在需要密码时调用）
    def get_password():
        return input("PDF 需要密码，请输入密码（按 Ctrl+C 退出）: ").strip()

    # 执行解密（先尝试无密码，如果需要密码会通过 callback 获取）
    code, msg = decrypt_pdf(input_path, output_path, password_callback=get_password)

    if code == 0:
        print(f"✓ {msg}")
        sys.exit(0)
    else:
        print(f"✗ {msg}")
        sys.exit(1)
