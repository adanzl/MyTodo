"""
PDF 解密工具
用于对有密码保护的 PDF 进行解密，包括能打开但不能编辑/打印的权限保护
"""
import os
from typing import Optional, Tuple, Callable

import pypdf

from core.log_config import root_logger

log = root_logger()


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

    # 检查输出文件是否已存在
    if os.path.exists(output_path):
        error_msg = f"输出文件已存在: {output_path}"
        log.error(f"[PDF] {error_msg}")
        return -1, error_msg

    try:
        reader = pypdf.PdfReader(input_path)

        # 判断是否加密
        if reader.is_encrypted:
            # 如果提供了密码，直接使用
            if password:
                decrypt_result = reader.decrypt(password)
                if decrypt_result == 0:
                    error_msg = "密码错误"
                    log.error(f"[PDF] {error_msg}")
                    return -1, error_msg
            else:
                # 需要密码，尝试读取第一页来确认是否需要密码
                while True:
                    try:
                        _ = reader.pages[0]  # 尝试读取第一页
                        break
                    except Exception:
                        # 需要密码
                        if password_callback:
                            password = password_callback()
                        else:
                            error_msg = "PDF 需要密码，但未提供密码或密码回调函数"
                            log.error(f"[PDF] {error_msg}")
                            return -1, error_msg

                        if not password:
                            error_msg = "未提供密码"
                            log.error(f"[PDF] {error_msg}")
                            return -1, error_msg

                        decrypt_result = reader.decrypt(password)
                        if decrypt_result == 0:
                            log.warning("[PDF] 密码错误，请重试")
                            continue
                        else:
                            break
            # 获取页数
        pages_cnt = len(reader.pages)
        # 克隆整个文档结构（包括页面、书签、命名目标等）
        writer = pypdf.PdfWriter()
        writer.clone_reader_document_root(reader)

        # 不调用 writer.encrypt(...)，因此输出是完全解密的
        with open(output_path, "wb") as out_f:
            writer.write(out_f)

        log.info(f"[PDF] 解密后 总页数: {pages_cnt} 保存到: {output_path}")
        return 0, "PDF 解密成功"

    except Exception as e:
        error_msg = f"PDF 解密失败: {str(e)}"
        log.error(f"[PDF] {error_msg}")
        return -1, error_msg


if __name__ == '__main__':
    """
    命令行工具入口
    用于交互式解密 PDF
    """
    import sys

    # 默认文件路径（仅用于命令行工具）
    default_input = "/Users/zhaolin/Downloads/MHE_RDG_Wonders_Teachers_Edition_Grade1_Unit3.pdf"
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

    # 定义密码获取回调函数
    def get_password():
        return input("PDF 需要密码，请输入密码（按 Ctrl+C 退出）: ").strip()

    # 执行解密
    code, msg = decrypt_pdf(input_path, output_path, password_callback=get_password)

    if code == 0:
        print(f"✓ {msg}")
        sys.exit(0)
    else:
        print(f"✗ {msg}")
        sys.exit(1)
