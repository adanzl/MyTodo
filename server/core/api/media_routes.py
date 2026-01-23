"""媒体管理路由。

提供媒体文件访问、音频合成（merge）与音频转码（convert）相关的 HTTP API。

高风险点：
- 文件系统读写（上传/删除/转存）；
- 路径安全校验（防止目录穿越）；
- 大文件 I/O 与外部工具（ffmpeg/ffprobe）调用引发的超时与异常。
"""
import os
import shutil
from datetime import datetime

from flask import Blueprint, request, send_file, abort
from werkzeug.exceptions import HTTPException
from flask.typing import ResponseReturnValue
from werkzeug.utils import secure_filename

from core.config import app_logger
from core.services.audio_merge_mgr import audio_merge_mgr
from core.services.audio_convert_mgr import audio_convert_mgr
from core.config import get_media_task_dir, ALLOWED_AUDIO_EXTENSIONS, MIMETYPE_MAP
from core.config import config
from core import limiter
from core.utils import get_media_duration, validate_and_normalize_path, _ok, _err, ensure_directory, is_allowed_audio_file, get_file_info, read_json_from_request, get_unique_filepath, get_file_type_by_magic_number
from core.tools.validation import parse_with_model
from pydantic import BaseModel, Field


class _TaskIdBody(BaseModel):
    task_id: str


class _SaveResultBody(BaseModel):
    task_id: str
    target_path: str


class _CreateConvertTaskBody(BaseModel):
    name: str = Field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    output_dir: str | None = None
    overwrite: bool | None = None


log = app_logger
media_bp = Blueprint('media', __name__)

# 常量定义
DEFAULT_BASE_DIR = config.DEFAULT_BASE_DIR

# ========== 媒体文件服务接口（用于 DLNA 播放）==========


@media_bp.route("/media/getDuration", methods=['GET'])
def get_duration() -> ResponseReturnValue:
    """获取媒体文件的时长。

    Query Args:
        path (str): 媒体文件路径（相对/绝对路径）。

    Returns:
        ResponseReturnValue: 成功时返回 `{"code": 0, "data": {"duration": float, "path": str}}`；
            失败时返回 `{"code": -1, "msg": str}`。
    """
    try:
        file_path = request.args.get('path', '')

        # 验证和规范化路径
        normalized_path, error_msg = validate_and_normalize_path(file_path, DEFAULT_BASE_DIR, must_be_file=True)
        if error_msg:
            return _err(error_msg)

        # 获取媒体文件时长
        duration = get_media_duration(normalized_path)
        if duration is not None:
            return _ok({"duration": duration, "path": normalized_path})
        else:
            return _err("无法获取媒体文件时长")

    except PermissionError as e:
        file_path_str = file_path if 'file_path' in locals() else 'unknown'
        log.error(f"Permission denied for {file_path_str}: {e}")
        return _err(f"Permission denied: {str(e)}")
    except Exception as e:
        log.error(f"Error getting media duration: {e}")
        return _err(f"Error: {str(e)}")


@media_bp.route("/media/files/<path:filepath>", methods=['GET'])
def serve_media_file(filepath: str) -> ResponseReturnValue:
    """提供媒体文件访问服务（用于 DLNA 播放）。

    Args:
        filepath (str): URL 路径参数，指定要访问的媒体文件路径。

    Returns:
        ResponseReturnValue: 返回文件内容，或 HTTP 404/500 错误。

    Notes:
        - 自动处理路径安全（过滤 `../` 等危险字符）
        - 自动设置 MIME 类型
        - 支持 HTTP Range 请求（通过 Flask 的 `send_file` 自动处理）
    """
    try:
        # 安全处理：移除路径中的危险字符
        filepath = filepath.replace('../', '').replace('..\\', '')

        # 如果路径不是以 / 开头，添加 /
        if not filepath.startswith('/'):
            filepath = '/' + filepath

        # 检查文件是否存在
        if not os.path.exists(filepath) or not os.path.isfile(filepath):
            log.warning(f"[MEDIA] File not found: {filepath}")
            abort(404)

        # 获取文件扩展名以确定 Content-Type
        ext = os.path.splitext(filepath)[1].lower()
        mimetype = MIMETYPE_MAP.get(ext, 'application/octet-stream')

        log.info(f"[MEDIA] Serving file: {filepath} (MIME: {mimetype})")
        return send_file(filepath, mimetype=mimetype)
    except HTTPException as e:
        # Re-raise HTTP exceptions (like aborts) directly
        raise e
    except Exception as e:
        log.error(f"[MEDIA] Error serving file {filepath}: {e}")
        abort(500)


# ========== 音频合成接口 ==========


class _CreateMediaTaskBody(BaseModel):
    name: str = Field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


@media_bp.route("/media/merge/create", methods=['POST'])
def create_media_task() -> ResponseReturnValue:
    """创建音频合成任务。

    JSON Body:
        name (str, optional): 任务名称；未提供时默认使用当前时间戳字符串。

    Returns:
        ResponseReturnValue: 成功时返回新建任务信息；失败时返回 `{"code": -1, "msg": str}`。
    """
    try:
        data = read_json_from_request()
        body, err = parse_with_model(_CreateMediaTaskBody, data, err_factory=_err)
        if err:
            return err
        name = body.name

        code, msg, task_id = audio_merge_mgr.create_task(name)

        if code != 0:
            return _err(msg)

        task_info = audio_merge_mgr.get_task(task_id)
        return _ok(task_info)

    except Exception as e:
        log.error(f"[AudioMerge] 创建任务失败: {e}")
        return _err(f"创建任务失败: {str(e)}")


class _UploadFileArgs(BaseModel):
    task_id: str


@limiter.limit("10 per minute; 50 per hour")
@media_bp.route("/media/merge/upload", methods=['POST'])
def upload_file() -> ResponseReturnValue:
    """上传文件到音频合成任务。

    风险点：该接口涉及文件写入与文件名处理，需确保：
    - 仅允许白名单音频扩展名；
    - 文件名通过 `secure_filename` 清洗；
    - 任务目录存在且可写。

    Form / Query Args:
        task_id (str): 任务 ID。

    Form Files:
        file: 上传文件（multipart/form-data）。

    Returns:
        ResponseReturnValue: 成功时返回上传后的文件信息；失败时返回 `{"code": -1, "msg": str}`。

    Raises:
        Exception: I/O 异常或服务内部异常会被捕获并转换为错误响应。
    """
    try:
        args_data = {**request.form.to_dict(), **request.args.to_dict()}
        validated_args, err = parse_with_model(_UploadFileArgs, args_data, err_factory=_err)
        if err:
            return err
        task_id = validated_args.task_id

        if 'file' not in request.files:
            return _err("未找到上传的文件")

        file = request.files['file']
        if file.filename == '':
            return _err("文件名不能为空")

        # 验证文件大小
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        if file_size > config.MAX_UPLOAD_FILE_SIZE:
            return _err(f"文件大小超过限制 ({config.MAX_UPLOAD_FILE_SIZE // 1024 // 1024}MB)")

        file = request.files['file']
        if file.filename == '':
            return _err("文件名不能为空")

        # 验证文件类型
        file_type = get_file_type_by_magic_number(file)
        if file_type is None or f".{file_type}" not in ALLOWED_AUDIO_EXTENSIONS:
            # 降级检查文件扩展名
            if not is_allowed_audio_file(file.filename):
                return _err(f"不支持的文件类型，支持的格式: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}")

        # 确保任务目录存在
        task_dir = get_media_task_dir(task_id)
        ensure_directory(task_dir)

        # 保存文件，如果文件已存在则添加序号
        filename = secure_filename(file.filename)
        base_name, ext = os.path.splitext(filename)
        file_path = get_unique_filepath(task_dir, base_name, ext)
        filename = os.path.basename(file_path)

        file.save(file_path)
        log.info(f"[AudioMerge] 文件上传成功: {file_path}")

        # 添加到任务
        code, msg = audio_merge_mgr.add_file(task_id, file_path, filename)
        if code != 0:
            return _err(msg)

        file_info = get_file_info(file_path)
        return _ok(file_info)

    except Exception as e:
        log.error(f"[AudioMerge] 上传文件失败: {e}")
        return _err(f"上传文件失败: {str(e)}")


class _AddFileByPathBody(BaseModel):
    task_id: str
    file_path: str


@media_bp.route("/media/merge/addFileByPath", methods=['POST'])
def add_file_by_path() -> ResponseReturnValue:
    """通过文件路径添加文件到音频合成任务。

    风险点：该接口允许服务端从给定路径读取文件并纳入任务，必须严格依赖
    `validate_and_normalize_path` 做目录边界与路径合法性校验。

    JSON / Form Body:
        task_id (str): 任务 ID。
        file_path (str): 要添加的文件路径。

    Returns:
        ResponseReturnValue: 成功时返回文件信息；失败时返回 `{"code": -1, "msg": str}`。

    Raises:
        Exception: I/O 异常或服务内部异常会被捕获并转换为错误响应。
    """
    try:
        data = read_json_from_request() or request.form.to_dict()
        body, err = parse_with_model(_AddFileByPathBody, data, err_factory=_err)
        if err:
            return err
        task_id = body.task_id
        file_path = body.file_path

        # 验证文件路径
        normalized_path, error_msg = validate_and_normalize_path(file_path)
        if error_msg or not normalized_path:
            return _err(error_msg or "文件路径无效")
        file_path = normalized_path

        if not os.path.exists(file_path):
            return _err(f"文件不存在: {file_path}")

        if not os.path.isfile(file_path):
            return _err(f"路径不是文件: {file_path}")

        filename = os.path.basename(file_path)
        if not is_allowed_audio_file(filename):
            return _err(f"不支持的文件类型，支持的格式: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}")

        # 添加到任务
        code, msg = audio_merge_mgr.add_file(task_id, file_path, filename)
        if code != 0:
            return _err(msg)

        file_info = get_file_info(file_path)
        return _ok(file_info)

    except Exception as e:
        log.error(f"[AudioMerge] 添加文件失败: {e}")
        return _err(f"添加文件失败: {str(e)}")


class _DeleteFileBody(BaseModel):
    task_id: str
    file_index: int


@media_bp.route("/media/merge/deleteFile", methods=['POST'])
def delete_file() -> ResponseReturnValue:
    """从音频合成任务中删除文件。

    风险点：该接口会改变任务状态并可能影响后续合成结果。

    JSON / Form Body:
        task_id (str): 任务 ID。
        file_index (int | str): 要删除的文件索引。

    Returns:
        ResponseReturnValue: 成功时返回删除结果；失败时返回 `{"code": -1, "msg": str}`。
    """
    try:
        data = read_json_from_request() or request.form.to_dict()
        body, err = parse_with_model(_DeleteFileBody, data, err_factory=_err)
        if err:
            return err

        code, msg = audio_merge_mgr.remove_file(body.task_id, body.file_index)
        if code != 0:
            return _err(msg)

        return _ok({"message": msg})

    except Exception as e:
        log.error(f"[AudioMerge] 删除文件失败: {e}")
        return _err(f"删除文件失败: {str(e)}")


@media_bp.route("/media/merge/reorderFiles", methods=['POST'])
def reorder_files() -> ResponseReturnValue:
    """
    调整文件顺序
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    - file_indices: 新的文件索引顺序列表（JSON 参数）
    """
    try:
        data = read_json_from_request() or request.form.to_dict()
        task_id = data.get('task_id')
        file_indices = data.get('file_indices')

        if not task_id:
            return _err("task_id 参数不能为空")

        if not file_indices:
            return _err("file_indices 参数不能为空")

        if not isinstance(file_indices, list):
            return _err("file_indices 必须是数组")

        try:
            file_indices = [int(i) for i in file_indices]
        except (ValueError, TypeError):
            return _err("file_indices 必须都是整数")

        code, msg = audio_merge_mgr.reorder_files(task_id, file_indices)
        if code != 0:
            return _err(msg)

        task_info = audio_merge_mgr.get_task(task_id)
        return _ok(task_info)

    except Exception as e:
        log.error(f"[AudioMerge] 调整文件顺序失败: {e}")
        return _err(f"调整文件顺序失败: {str(e)}")


@media_bp.route("/media/merge/start", methods=['POST'])
def start_task() -> ResponseReturnValue:
    """
    开始音频合成任务
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    """
    try:
        data = read_json_from_request() or request.form.to_dict()
        task_id = data.get('task_id')

        if not task_id:
            return _err("task_id 参数不能为空")

        code, msg = audio_merge_mgr.start_task(task_id)
        if code != 0:
            return _err(msg)

        task_info = audio_merge_mgr.get_task(task_id)
        return _ok(task_info)

    except Exception as e:
        log.error(f"[AudioMerge] 启动任务失败: {e}")
        return _err(f"启动任务失败: {str(e)}")


@media_bp.route("/media/merge/get", methods=['POST'])
def get_task_info() -> ResponseReturnValue:
    """
    获取任务信息
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    """
    try:
        data = read_json_from_request() or request.form.to_dict()
        task_id = data.get('task_id')

        if not task_id:
            return _err("task_id 参数不能为空")

        task_info = audio_merge_mgr.get_task(task_id)
        if not task_info:
            return _err("任务不存在")

        return _ok(task_info)

    except Exception as e:
        log.error(f"[AudioMerge] 获取任务信息失败: {e}")
        return _err(f"获取任务信息失败: {str(e)}")


@media_bp.route("/media/merge/list", methods=['GET'])
def list_all_tasks() -> ResponseReturnValue:
    """
    列出所有任务
    """
    try:
        tasks = audio_merge_mgr.list_tasks()
        return _ok({"tasks": tasks})

    except Exception as e:
        log.error(f"[AudioMerge] 列出任务失败: {e}")
        return _err(f"列出任务失败: {str(e)}")


@media_bp.route("/media/merge/delete", methods=['POST'])
def delete_task() -> ResponseReturnValue:
    """删除音频合成任务及其关联文件。

    风险点：该操作会从文件系统删除任务目录，是破坏性操作。

    JSON / Form Body:
        task_id (str): 要删除的任务 ID。

    Returns:
        ResponseReturnValue: 成功时返回 `{"code": 0, "msg": str}`；失败时返回错误信息。
    """
    try:
        data = read_json_from_request() or request.form.to_dict()
        body, err = parse_with_model(_TaskIdBody, data, err_factory=_err)
        if err:
            return err

        code, msg = audio_merge_mgr.delete_task(body.task_id)
        if code != 0:
            return _err(msg)

        return _ok({"message": msg})

    except Exception as e:
        log.error(f"[AudioMerge] 删除任务失败: {e}")
        return _err(f"删除任务失败: {str(e)}")


@media_bp.route("/media/merge/download", methods=['GET'])
def download_result() -> ResponseReturnValue:
    """下载音频合成结果文件。

    风险点：该接口直接返回服务器文件内容，需要确保只允许下载任务产物。

    Query Args:
        task_id (str): 任务 ID。

    Returns:
        ResponseReturnValue: 成功时返回结果文件（附件下载）；失败时返回 `{"code": -1, "msg": str}`。

    Raises:
        Exception: I/O 异常或服务内部异常会被捕获并转换为错误响应。
    """
    try:
        args, err = parse_with_model(_TaskIdBody, request.args.to_dict(), err_factory=_err)
        if err:
            return err
        task_id = args.task_id

        task_info = audio_merge_mgr.get_task(task_id)
        if not task_info:
            return _err("任务不存在")

        if task_info['status'] != 'success' or not task_info.get('result_file'):
            return _err("任务未完成或结果文件不存在")

        result_file = task_info['result_file']
        if not os.path.exists(result_file):
            return _err("结果文件不存在")

        return send_file(result_file, as_attachment=True, download_name='merged.mp3')

    except Exception as e:
        log.error(f"[AudioMerge] 下载文件失败: {e}")
        return _err(f"下载文件失败: {str(e)}")


@media_bp.route("/media/merge/save", methods=['POST'])
def save_result() -> ResponseReturnValue:
    """转存音频合成结果文件到指定目录。

    风险点：该接口会在服务器文件系统中写入新文件，需要严格做路径校验与权限检查。

    JSON / Form Body:
        task_id (str): 任务 ID。
        target_path (str): 目标目录路径。

    Returns:
        ResponseReturnValue: 成功时返回目标文件路径；失败时返回 `{"code": -1, "msg": str}`。

    Raises:
        Exception: I/O 异常或服务内部异常会被捕获并转换为错误响应。
    """
    try:
        data = read_json_from_request() or request.form.to_dict()
        body, err = parse_with_model(_SaveResultBody, data, err_factory=_err)
        if err:
            return err
        task_id = body.task_id
        target_path = body.target_path

        # 验证目标路径
        normalized_path, error_msg = validate_and_normalize_path(target_path, must_be_file=False)
        if error_msg or not normalized_path:
            return _err(error_msg or "目标路径无效")
        target_path = normalized_path

        if not os.path.exists(target_path):
            return _err(f"目标目录不存在: {target_path}")

        if not os.path.isdir(target_path):
            return _err(f"目标路径不是目录: {target_path}")

        # 获取任务信息
        task_info = audio_merge_mgr.get_task(task_id)
        if not task_info:
            return _err("任务不存在")

        if task_info['status'] != 'success' or not task_info.get('result_file'):
            return _err("任务未完成或结果文件不存在")

        result_file = task_info['result_file']
        if not os.path.exists(result_file):
            return _err("结果文件不存在")

        # 获取结果文件的扩展名，默认为 .mp3
        _, ext = os.path.splitext(result_file)
        ext = ext or '.mp3'

        # 生成唯一的目标文件路径：task_id + 扩展名，如果已存在则添加序号
        target_file = get_unique_filepath(target_path, task_id, ext)

        # 复制文件到目标目录
        shutil.copy2(result_file, target_file)
        log.info(f"[AudioMerge] 文件转存成功: {result_file} -> {target_file}")

        return _ok({"target_file": target_file, "message": "转存成功"})

    except Exception as e:
        log.error(f"[AudioMerge] 转存文件失败: {e}")
        return _err(f"转存文件失败: {str(e)}")


# ========== 音频转码接口 ==========


@media_bp.route("/media/convert/list", methods=['GET'])
def list_convert_tasks() -> ResponseReturnValue:
    """
    获取所有音频转码任务列表
    """
    try:
        tasks = audio_convert_mgr.get_task_list()
        return _ok({"tasks": tasks})
    except Exception as e:
        log.error(f"[AudioConvert] 列出任务失败: {e}")
        return _err(f"列出任务失败: {str(e)}")


@media_bp.route("/media/convert/create", methods=['POST'])
def create_convert_task() -> ResponseReturnValue:
    """创建音频转码任务。

    风险点：任务执行过程中会扫描目录并调用 ffmpeg 转码（CPU/I-O 密集）。

    JSON Body:
        name (str, optional): 任务名称；未提供时使用当前时间戳。
        output_dir (str, optional): 输出目录名称（默认由服务端决定）。
        overwrite (bool, optional): 是否覆盖同名文件。

    Returns:
        ResponseReturnValue: 成功时返回任务信息；失败时返回 `{"code": -1, "msg": str}`。
    """
    try:
        data = read_json_from_request()
        body, err = parse_with_model(_CreateConvertTaskBody, data, err_factory=_err)
        if err:
            return err
        name = body.name
        output_dir = body.output_dir
        overwrite = body.overwrite

        code, msg, task_id = audio_convert_mgr.create_task(name, output_dir=output_dir, overwrite=overwrite)

        if code != 0:
            return _err(msg)

        task_info = audio_convert_mgr.get_task(task_id)
        return _ok(task_info)

    except Exception as e:
        log.error(f"[AudioConvert] 创建任务失败: {e}")
        return _err(f"创建任务失败: {str(e)}")


@media_bp.route("/media/convert/get", methods=['POST'])
def get_convert_task_info() -> ResponseReturnValue:
    """
    获取音频转码任务详情
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    """
    try:
        data = read_json_from_request() or request.form.to_dict()
        task_id = data.get('task_id')

        if not task_id:
            return _err("task_id 参数不能为空")

        task_info = audio_convert_mgr.get_task(task_id)
        if not task_info:
            return _err("任务不存在")

        return _ok(task_info)

    except Exception as e:
        log.error(f"[AudioConvert] 获取任务信息失败: {e}")
        return _err(f"获取任务信息失败: {str(e)}")


@media_bp.route("/media/convert/delete", methods=['POST'])
def delete_convert_task() -> ResponseReturnValue:
    """
    删除音频转码任务
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    """
    try:
        data = read_json_from_request() or request.form.to_dict()
        task_id = data.get('task_id')

        if not task_id:
            return _err("task_id 参数不能为空")

        code, msg = audio_convert_mgr.delete_task(task_id)
        if code != 0:
            return _err(msg)

        return _ok({"success": True})

    except Exception as e:
        log.error(f"[AudioConvert] 删除任务失败: {e}")
        return _err(f"删除任务失败: {str(e)}")


@media_bp.route("/media/convert/update", methods=['POST'])
def update_convert_task() -> ResponseReturnValue:
    """
    更新音频转码任务信息
    参数：
    - task_id: 任务ID（JSON 或 form 参数，必填）
    - name: 任务名称（JSON 或 form 参数，可选）
    - directory: 目录路径（JSON 或 form 参数，可选）
    """
    try:
        data = read_json_from_request() or request.form.to_dict()
        task_id = data.get('task_id')
        name = data.get('name')
        directory = data.get('directory')

        if not task_id:
            return _err("task_id 参数不能为空")

        # 至少需要提供一个要更新的字段
        output_dir = data.get('output_dir')
        overwrite = data.get('overwrite')
        if name is None and directory is None and output_dir is None and overwrite is None:
            return _err("至少需要提供一个要更新的字段（name、directory、output_dir 或 overwrite）")

        # 验证目录路径（如果提供了）
        if directory is not None:
            normalized_path, error_msg = validate_and_normalize_path(directory, must_be_file=False)
            if error_msg or not normalized_path:
                return _err(error_msg or "目录路径无效")
            directory = normalized_path

        code, msg = audio_convert_mgr.update_task(task_id,
                                                  name=name,
                                                  directory=directory,
                                                  output_dir=output_dir,
                                                  overwrite=overwrite)
        if code != 0:
            return _err(msg)

        task_info = audio_convert_mgr.get_task(task_id)
        return _ok(task_info)

    except Exception as e:
        log.error(f"[AudioConvert] 更新任务失败: {e}")
        return _err(f"更新任务失败: {str(e)}")


@limiter.limit("10 per minute; 50 per hour")
@media_bp.route("/media/convert/start", methods=['POST'])
def start_convert_task() -> ResponseReturnValue:
    """
    开始音频转码任务
    参数：
    - task_id: 任务ID（JSON 或 form 参数）
    """
    try:
        data = read_json_from_request() or request.form.to_dict()
        task_id = data.get('task_id')

        if not task_id:
            return _err("task_id 参数不能为空")

        code, msg = audio_convert_mgr.start_task(task_id)
        if code != 0:
            return _err(msg)

        task_info = audio_convert_mgr.get_task(task_id)
        return _ok(task_info)

    except Exception as e:
        log.error(f"[AudioConvert] 启动任务失败: {e}")
        return _err(f"启动任务失败: {str(e)}")
