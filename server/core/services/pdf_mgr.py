"""
PDF 管理服务
提供 PDF 文件上传、解密、列表等功能
"""
import os
import json
import shutil
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass, asdict
from datetime import datetime
from werkzeug.utils import secure_filename

import pikepdf

from core.log_config import root_logger
from core.models.const import PDF_BASE_DIR, PDF_UPLOAD_DIR, PDF_UNLOCK_DIR, ALLOWED_PDF_EXTENSIONS
from core.utils import ensure_directory, get_file_info, is_allowed_pdf_file

log = root_logger()


@dataclass
class PdfFileRecord:
    """PDF 文件记录"""
    filename: str  # 文件名
    uploaded_path: str  # 上传文件路径
    uploaded_info: Dict  # 上传文件信息（name, path, size, modified）
    unlocked_path: Optional[str] = None  # 已解密文件路径
    unlocked_info: Optional[Dict] = None  # 已解密文件信息
    has_unlocked: bool = False  # 是否有已解密文件
    create_time: float = 0  # 创建时间戳
    update_time: float = 0  # 更新时间戳


class PdfMgr:
    """PDF 管理器"""
    
    RECORD_FILE = 'pdf.json'  # 记录文件名
    MAX_FILES = 30  # 最大保留文件数
    
    def __init__(self):
        """初始化管理器"""
        self._files: Dict[str, PdfFileRecord] = {}  # key: filename
        self._processing_files: set = set()  # 正在处理的文件集合
        self._load_history_records()
    
    def _load_history_records(self):
        """加载历史记录"""
        try:
            if not os.path.exists(PDF_BASE_DIR):
                return
            
            record_file = os.path.join(PDF_BASE_DIR, self.RECORD_FILE)
            if not os.path.exists(record_file):
                return
            
            with open(record_file, 'r', encoding='utf-8') as f:
                all_records_data = json.load(f)
            
            if not isinstance(all_records_data, dict):
                log.warning("[PDF] pdf.json 格式错误，应为字典格式")
                return
            
            loaded_count = 0
            for filename, record_data in all_records_data.items():
                try:
                    # 验证上传文件是否存在
                    uploaded_path = record_data.get('uploaded_path')
                    if not uploaded_path or not os.path.exists(uploaded_path):
                        log.warning(f"[PDF] 上传文件不存在: {filename}")
                        continue
                    
                    # 重新获取上传文件信息
                    uploaded_info = get_file_info(uploaded_path)
                    if not uploaded_info:
                        log.warning(f"[PDF] 无法获取上传文件信息: {filename}")
                        continue
                    
                    # 验证已解密文件是否存在
                    unlocked_path = record_data.get('unlocked_path')
                    unlocked_info = None
                    has_unlocked = False
                    if unlocked_path and os.path.exists(unlocked_path):
                        unlocked_info = get_file_info(unlocked_path)
                        has_unlocked = unlocked_info is not None
                    
                    # 创建记录对象
                    record = PdfFileRecord(
                        filename=filename,
                        uploaded_path=uploaded_path,
                        uploaded_info=uploaded_info,
                        unlocked_path=unlocked_path if has_unlocked else None,
                        unlocked_info=unlocked_info,
                        has_unlocked=has_unlocked,
                        create_time=record_data.get('create_time', 0),
                        update_time=record_data.get('update_time', 0)
                    )
                    
                    self._files[filename] = record
                    loaded_count += 1
                    log.info(f"[PDF] 加载历史记录: {filename}")
                    
                except Exception as e:
                    log.error(f"[PDF] 加载记录失败 {filename}: {e}")
                    continue
            
            log.info(f"[PDF] 共加载 {loaded_count} 个历史记录")
            
        except json.JSONDecodeError as e:
            log.error(f"[PDF] 解析 pdf.json 失败: {e}")
        except Exception as e:
            log.error(f"[PDF] 加载历史记录失败: {e}")
    
    def _save_all_records(self):
        """保存所有记录到统一的 pdf.json 文件"""
        try:
            record_file = os.path.join(PDF_BASE_DIR, self.RECORD_FILE)
            os.makedirs(PDF_BASE_DIR, exist_ok=True)
            
            all_records_data = {
                filename: asdict(record)
                for filename, record in self._files.items()
            }
            
            with open(record_file, 'w', encoding='utf-8') as f:
                json.dump(all_records_data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            log.error(f"[PDF] 保存所有记录失败: {e}")
    
    def _update_record_time(self, record: PdfFileRecord):
        """更新记录的更新时间"""
        record.update_time = datetime.now().timestamp()
    
    def upload_file(self, file_obj, filename: str) -> Tuple[int, str, Optional[Dict]]:
        """
        上传 PDF 文件
        
        :param file_obj: 文件对象（werkzeug FileStorage）
        :param filename: 原始文件名
        :return: (错误码, 消息, 文件信息)，0 表示成功
        """
        try:
            if not is_allowed_pdf_file(filename):
                return -1, "只支持 PDF 文件", None
            
            # 确保目录存在
            ensure_directory(PDF_UPLOAD_DIR)
            ensure_directory(PDF_UNLOCK_DIR)
            
            # 使用安全文件名
            safe_filename = secure_filename(filename)
            file_path = os.path.join(PDF_UPLOAD_DIR, safe_filename)
            
            # 如果文件已存在，添加序号
            if os.path.exists(file_path):
                base_name, ext = os.path.splitext(safe_filename)
                counter = 1
                while os.path.exists(file_path):
                    new_filename = f"{base_name}_{counter}{ext}"
                    file_path = os.path.join(PDF_UPLOAD_DIR, new_filename)
                    counter += 1
                safe_filename = os.path.basename(file_path)
            
            # 保存文件
            file_obj.save(file_path)
            log.info(f"[PDF] 文件上传成功: {file_path}")
            
            # 获取文件信息
            file_info = get_file_info(file_path)
            if not file_info:
                return -1, "无法获取文件信息", None
            
            # 创建或更新记录
            now = datetime.now().timestamp()
            if safe_filename in self._files:
                record = self._files[safe_filename]
                record.uploaded_path = file_path
                record.uploaded_info = file_info
                record.update_time = now
            else:
                record = PdfFileRecord(
                    filename=safe_filename,
                    uploaded_path=file_path,
                    uploaded_info=file_info,
                    create_time=now,
                    update_time=now
                )
                self._files[safe_filename] = record
            
            # 限制文件数量
            self._limit_files()
            
            # 保存记录
            self._save_all_records()
            
            return 0, "文件上传成功", file_info
            
        except Exception as e:
            log.error(f"[PDF] 上传文件失败: {e}")
            return -1, f"上传文件失败: {str(e)}", None
    
    def _limit_files(self):
        """限制文件数量，删除最旧的文件"""
        if len(self._files) <= self.MAX_FILES:
            return
        
        # 按更新时间排序
        sorted_files = sorted(
            self._files.items(),
            key=lambda x: x[1].update_time,
            reverse=True
        )
        
        # 删除最旧的文件
        files_to_delete = sorted_files[self.MAX_FILES:]
        for filename, record in files_to_delete:
            try:
                # 删除上传文件
                if record.uploaded_path and os.path.exists(record.uploaded_path):
                    os.remove(record.uploaded_path)
                    log.info(f"[PDF] 删除旧文件: {record.uploaded_path}")
                
                # 删除已解密文件
                if record.unlocked_path and os.path.exists(record.unlocked_path):
                    os.remove(record.unlocked_path)
                    log.info(f"[PDF] 删除对应的已解密文件: {record.unlocked_path}")
                
                # 从记录中移除
                del self._files[filename]
                
            except Exception as e:
                log.error(f"[PDF] 删除文件失败 {filename}: {e}")
    
    def decrypt_file(self, filename: str, password: Optional[str] = None) -> Tuple[int, str]:
        """
        解密 PDF 文件
        
        :param filename: 文件名
        :param password: 密码（可选）
        :return: (错误码, 消息)，0 表示成功
        """
        try:
            # 检查记录是否存在
            if filename not in self._files:
                return -1, f"文件不存在: {filename}"
            
            record = self._files[filename]
            
            # 检查文件是否存在
            if not os.path.exists(record.uploaded_path):
                return -1, f"上传文件不存在: {filename}"
            
            # 检查是否正在处理中
            if filename in self._processing_files:
                return -1, "文件正在处理中，请稍候"
            
            # 构建输出文件路径
            base_name, ext = os.path.splitext(filename)
            output_filename = f"{base_name}_unlocked{ext}"
            output_path = os.path.join(PDF_UNLOCK_DIR, output_filename)
            
            # 添加到处理中集合
            self._processing_files.add(filename)
            
            try:
                # 执行解密
                code, msg = self._decrypt_with_pikepdf(
                    record.uploaded_path,
                    output_path,
                    password
                )
                
                if code != 0:
                    return code, msg
                
                # 获取已解密文件信息
                unlocked_info = get_file_info(output_path)
                if not unlocked_info:
                    return -1, "无法获取已解密文件信息"
                
                # 更新记录
                record.unlocked_path = output_path
                record.unlocked_info = unlocked_info
                record.has_unlocked = True
                self._update_record_time(record)
                self._save_all_records()
                
                log.info(f"[PDF] 文件解密成功: {output_path}")
                return 0, "PDF 解密成功"
                
            finally:
                # 从处理中集合移除
                self._processing_files.discard(filename)
                
        except Exception as e:
            log.error(f"[PDF] 解密文件失败: {e}")
            if filename in self._processing_files:
                self._processing_files.discard(filename)
            return -1, f"解密文件失败: {str(e)}"
    
    def _decrypt_with_pikepdf(
        self,
        input_path: str,
        output_path: str,
        password: Optional[str] = None
    ) -> Tuple[int, str]:
        """使用 pikepdf 解密 PDF"""
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
            log.error(f"[PDF] pikepdf 解密失败: {e}")
            return -1, f"PDF 解密失败: {str(e)}"
    
    def list_files(self) -> Dict:
        """
        列出所有 PDF 文件
        
        :return: 包含 uploaded, unlocked, mapping 的字典
        """
        try:
            # 确保目录存在
            ensure_directory(PDF_UPLOAD_DIR)
            ensure_directory(PDF_UNLOCK_DIR)
            
            # 扫描上传目录，添加不在记录中的文件
            if os.path.exists(PDF_UPLOAD_DIR):
                for filename in os.listdir(PDF_UPLOAD_DIR):
                    file_path = os.path.join(PDF_UPLOAD_DIR, filename)
                    if os.path.isfile(file_path) and is_allowed_pdf_file(filename):
                        if filename not in self._files:
                            # 新文件，添加到记录
                            file_info = get_file_info(file_path)
                            if file_info:
                                now = datetime.now().timestamp()
                                record = PdfFileRecord(
                                    filename=filename,
                                    uploaded_path=file_path,
                                    uploaded_info=file_info,
                                    create_time=now,
                                    update_time=now
                                )
                                self._files[filename] = record
            
            # 重新验证文件是否存在，更新记录
            files_to_remove = []
            for filename, record in self._files.items():
                # 验证上传文件
                if not os.path.exists(record.uploaded_path):
                    files_to_remove.append(filename)
                    continue
                
                # 重新获取上传文件信息
                uploaded_info = get_file_info(record.uploaded_path)
                if uploaded_info:
                    record.uploaded_info = uploaded_info
                else:
                    files_to_remove.append(filename)
                    continue
                
                # 验证已解密文件
                if record.unlocked_path and os.path.exists(record.unlocked_path):
                    unlocked_info = get_file_info(record.unlocked_path)
                    if unlocked_info:
                        record.unlocked_info = unlocked_info
                        record.has_unlocked = True
                    else:
                        record.unlocked_path = None
                        record.unlocked_info = None
                        record.has_unlocked = False
                else:
                    # 检查是否有对应的已解密文件
                    base_name, ext = os.path.splitext(filename)
                    unlocked_filename = f"{base_name}_unlocked{ext}"
                    unlocked_path = os.path.join(PDF_UNLOCK_DIR, unlocked_filename)
                    if os.path.exists(unlocked_path):
                        unlocked_info = get_file_info(unlocked_path)
                        if unlocked_info:
                            record.unlocked_path = unlocked_path
                            record.unlocked_info = unlocked_info
                            record.has_unlocked = True
                    else:
                        record.unlocked_path = None
                        record.unlocked_info = None
                        record.has_unlocked = False
            
            # 移除不存在的文件记录
            for filename in files_to_remove:
                del self._files[filename]
            
            if files_to_remove or len(files_to_remove) != len(self._files):
                self._save_all_records()
            
            # 限制文件数量
            self._limit_files()
            
            # 按更新时间排序（最新的在前）
            sorted_records = sorted(
                self._files.values(),
                key=lambda x: x.update_time,
                reverse=True
            )
            
            # 构建返回数据
            uploaded_files = [record.uploaded_info for record in sorted_records]
            unlocked_files = [
                record.unlocked_info
                for record in sorted_records
                if record.unlocked_info
            ]
            
            file_mapping = []
            for record in sorted_records:
                file_mapping.append({
                    "uploaded": record.uploaded_info,
                    "unlocked": record.unlocked_info if record.has_unlocked else None,
                    "has_unlocked": record.has_unlocked,
                    "_decrypting": record.filename in self._processing_files
                })
            
            return {
                "uploaded": uploaded_files,
                "unlocked": unlocked_files,
                "mapping": file_mapping
            }
            
        except Exception as e:
            log.error(f"[PDF] 列出文件失败: {e}")
            return {
                "uploaded": [],
                "unlocked": [],
                "mapping": []
            }
    
    def delete_file(self, filename: str, file_type: str = 'both') -> Tuple[int, str]:
        """
        删除 PDF 文件
        
        :param filename: 文件名
        :param file_type: 文件类型，'uploaded' 或 'unlocked' 或 'both'（默认 'both'）
        :return: (错误码, 消息)，0 表示成功
        """
        try:
            if filename not in self._files:
                return -1, f"文件不存在: {filename}"
            
            record = self._files[filename]
            deleted_files = []
            
            if file_type in ('uploaded', 'both'):
                if record.uploaded_path and os.path.exists(record.uploaded_path):
                    os.remove(record.uploaded_path)
                    deleted_files.append(record.uploaded_path)
                    log.info(f"[PDF] 删除上传文件: {record.uploaded_path}")
            
            if file_type in ('unlocked', 'both'):
                if record.unlocked_path and os.path.exists(record.unlocked_path):
                    os.remove(record.unlocked_path)
                    deleted_files.append(record.unlocked_path)
                    log.info(f"[PDF] 删除已解密文件: {record.unlocked_path}")
                    record.unlocked_path = None
                    record.unlocked_info = None
                    record.has_unlocked = False
            
            if not deleted_files:
                return -1, "文件不存在"
            
            # 如果删除的是 both，移除记录
            if file_type == 'both':
                del self._files[filename]
            
            # 保存记录
            self._save_all_records()
            
            return 0, "文件删除成功"
            
        except Exception as e:
            log.error(f"[PDF] 删除文件失败: {e}")
            return -1, f"删除文件失败: {str(e)}"


# 创建全局实例
pdf_mgr = PdfMgr()


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
    code, msg = pdf_mgr._decrypt_with_pikepdf(input_path, output_path, password=None)

    if code == 0:
        print(f"✓ {msg}")
        sys.exit(0)
    else:
        print(f"✗ {msg}")
        sys.exit(1)
