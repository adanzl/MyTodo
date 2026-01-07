#!/usr/bin/env python3
"""
PDF 解密工具 - 独立脚本
最小化版本，不依赖项目其他模块
"""
import os
import sys
import pikepdf


def decrypt_pdf(input_path: str, output_path: str, password: str = None) -> tuple[int, str]:
    """
    解密 PDF 文件
    
    :param input_path: 输入 PDF 文件路径
    :param output_path: 输出 PDF 文件路径
    :param password: 密码（可选）
    :return: (错误码, 消息)，0 表示成功
    """
    try:
        if password is not None:
            # 如果明确提供了密码（包括空字符串），使用该密码
            try:
                with pikepdf.open(input_path, password=password) as pdf:
                    pdf.save(output_path)
            except pikepdf.PasswordError:
                return -1, "密码错误"
        else:
            # 先尝试无密码打开（处理无密码的 PDF）
            try:
                with pikepdf.open(input_path) as pdf:
                    pdf.save(output_path)
            except pikepdf.PasswordError:
                return -1, "PDF 需要密码，但未提供密码"

        return 0, "PDF 解密成功"

    except Exception as e:
        return -1, f"PDF 解密失败: {str(e)}"


if __name__ == '__main__':
    # 默认文件路径
    default_input = r"C:\Users\adanz\Downloads\MHE_RDG_Wonders_Teachers_Edition_Grade1_Unit4.pdf"
    default_output = r"C:\Users\adanz\Downloads\MHE_RDG_Wonders_Teachers_Edition_Grade1_Unit4_unlocked.pdf"

    print("=========== PDF 解密工具 ===========")

    # 获取输入文件路径
    input_path = input(f"请输入输入 PDF 文件路径（默认: {default_input}）: ").strip()
    if not input_path:
        input_path = default_input

    # 检查输入文件是否存在
    if not os.path.exists(input_path):
        print(f"错误：输入文件不存在: {input_path}")
        sys.exit(1)

    # 获取输出文件路径
    output_path = input(f"请输入输出 PDF 文件路径（默认: {default_output}）: ").strip()
    if not output_path:
        output_path = default_output

    # 检查输出目录是否存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            print(f"错误：无法创建输出目录: {e}")
            sys.exit(1)

    # 先尝试无密码解密
    print(f"\n开始解密: {input_path}")
    print(f"输出文件: {output_path}")
    print("正在尝试无密码解密...")
    
    code, msg = decrypt_pdf(input_path, output_path, password=None)

    # 如果需要密码，提示用户输入
    if code != 0 and "需要密码" in msg:
        print(f"\n提示: {msg}")
        password = input("请输入密码（留空则跳过）: ").strip()
        if password:
            print("正在使用密码解密...")
            code, msg = decrypt_pdf(input_path, output_path, password=password)
        else:
            print("已跳过密码输入")
            sys.exit(1)

    if code == 0:
        print(f"\n[成功] {msg}")
        print(f"输出文件: {output_path}")
        sys.exit(0)
    else:
        print(f"\n[失败] {msg}")
        sys.exit(1)

