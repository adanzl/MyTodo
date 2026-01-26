"""TTS routes.

提供文本转语音（TTS）任务的 API 接口：
- 创建、更新、启动、停止、删除任务
- 查询任务信息和列表
- 下载生成的音频文件
- OCR 图片文字识别（将结果追加到任务文本末尾）

所有路由挂载在 `/api` 下（由 create_app 设置 url_prefix='/'）。
"""

from __future__ import annotations

import os

from flask import Blueprint, request, send_file
from flask.typing import ResponseReturnValue
from pydantic import BaseModel

from core.config import app_logger
from core.services.tts_mgr import tts_mgr
from core.tools.validation import parse_with_model
from core.utils import (
    _err,
    _ok,
    cleanup_temp_files,
    read_json_from_request,
    save_uploaded_files,
)

log = app_logger

tts_bp = Blueprint('tts', __name__)


class _CreateTTSTaskBody(BaseModel):
    text: str
    name: str | None = None
    role: str | None = None
    speed: float | None = None
    vol: int | None = None


class _UpdateTTSTaskBody(BaseModel):
    task_id: str
    name: str | None = None
    text: str | None = None
    role: str | None = None
    speed: float | None = None
    vol: int | None = None


class _TaskIdBody(BaseModel):
    task_id: str


class _TTSOCRBody(BaseModel):
    """TTS OCR 请求体"""
    task_id: str


@tts_bp.route('/tts/create', methods=['POST'])
def create_tts_task() -> ResponseReturnValue:
    json_data = read_json_from_request()
    body, err = parse_with_model(_CreateTTSTaskBody, json_data, err_factory=_err)
    if err:
        return err
    code, msg, task_id = tts_mgr.create_task(
        text=body.text,
        name=body.name,
        role=body.role,
        speed=body.speed,
        vol=body.vol,
    )
    if code != 0:
        return _err(msg)
    return _ok({'task_id': task_id})


@tts_bp.route('/tts/update', methods=['POST'])
def update_tts_task() -> ResponseReturnValue:
    json_data = read_json_from_request()
    body, err = parse_with_model(_UpdateTTSTaskBody, json_data, err_factory=_err)
    if err:
        return err
    code, msg = tts_mgr.update_task(
        task_id=body.task_id,
        name=body.name,
        text=body.text,
        role=body.role,
        speed=body.speed,
        vol=body.vol,
    )
    if code != 0:
        return _err(msg)
    return _ok(None)


@tts_bp.route('/tts/start', methods=['POST'])
def start_tts_task() -> ResponseReturnValue:
    json_data = read_json_from_request()
    body, err = parse_with_model(_TaskIdBody, json_data, err_factory=_err)
    if err:
        return err
    code, msg = tts_mgr.start_task(body.task_id)
    if code != 0:
        return _err(msg)
    return _ok(None)


@tts_bp.route('/tts/stop', methods=['POST'])
def stop_tts_task() -> ResponseReturnValue:
    json_data = read_json_from_request()
    body, err = parse_with_model(_TaskIdBody, json_data, err_factory=_err)
    if err:
        return err
    code, msg = tts_mgr.stop_task(body.task_id)
    if code != 0:
        return _err(msg)
    return _ok(None)


@tts_bp.route('/tts/delete', methods=['POST'])
def delete_tts_task() -> ResponseReturnValue:
    json_data = read_json_from_request()
    body, err = parse_with_model(_TaskIdBody, json_data, err_factory=_err)
    if err:
        return err
    code, msg = tts_mgr.delete_task(body.task_id)
    if code != 0:
        return _err(msg)
    return _ok(None)


@tts_bp.route('/tts/get', methods=['GET'])
def get_tts_task() -> ResponseReturnValue:
    task_id = (request.args.get('task_id') or '').strip()
    if not task_id:
        return _err('task_id is required')

    task = tts_mgr.get_task(task_id)
    if not task:
        return _err('任务不存在')
    return _ok(task)


@tts_bp.route('/tts/list', methods=['GET'])
def list_tts_tasks() -> ResponseReturnValue:
    """获取所有 TTS 任务列表。

    Returns:
        ResponseReturnValue: 成功时返回任务列表
    """
    tasks = tts_mgr.list_tasks()
    return _ok(tasks)


@tts_bp.route('/tts/download', methods=['GET'])
def download_tts_file() -> ResponseReturnValue:
    """下载 TTS 任务生成的音频文件。

    Query Args:
        task_id (str): 任务 ID（必填）

    Returns:
        ResponseReturnValue: 成功时返回音频文件（附件下载），失败时返回错误信息

    Notes:
        - 只有任务状态为 success 且文件存在时才能下载
        - 文件保存在：{DEFAULT_BASE_DIR}/tasks/tts/{task_id}/output.mp3
    """
    try:
        task_id = (request.args.get('task_id') or '').strip()
        if not task_id:
            return _err('task_id 参数必填')

        # 获取任务信息
        task_info = tts_mgr.get_task(task_id)
        if not task_info:
            return _err('任务不存在')

        # 检查任务状态
        if task_info.get('status') != 'success':
            return _err('任务未完成，无法下载')

        # 获取输出文件路径
        output_file = tts_mgr.get_output_file_path(task_id)
        if not output_file or not os.path.exists(output_file):
            return _err('音频文件不存在')

        # 返回文件下载
        return send_file(
            output_file,
            as_attachment=True,
            download_name=f"tts_{task_id}.mp3",
            mimetype='audio/mpeg'
        )

    except Exception as e:
        log.error(f"[TTS] 下载文件失败: {e}")
        return _err(f'下载文件失败: {str(e)}')


@tts_bp.route('/tts/ocr', methods=['POST'])
def tts_ocr() -> ResponseReturnValue:
    """TTS 任务 OCR 图片文字识别接口。
    
    将 OCR 识别结果自动追加到指定 TTS 任务的文本末尾。
    开始 OCR 后，TTS 任务进入处理中状态；OCR 完成后，结果追加到文本末尾，任务状态恢复为待处理。
    该接口采用异步执行方式，立即返回成功响应，OCR 处理在后台线程中执行。
    
    Request (multipart/form-data):
        - task_id: 任务 ID（必填，可通过 form-data 或 query 参数传递）
        - file: 图片文件（支持多个，字段名可以是 'file' 或 'files[]'）
    
    Returns:
        ResponseReturnValue: 
            - 成功: {"code": 0, "msg": "ok"} - OCR 任务已启动，正在后台处理
            - 失败: {"code": -1, "msg": "错误信息"}
    """
    try:
        # 合并 form-data 和 query 参数，使用 parse_with_model 验证
        args_data = {**request.form.to_dict(), **request.args.to_dict()}
        body, err = parse_with_model(_TTSOCRBody, args_data, err_factory=_err)
        if err:
            return err
        task_id = body.task_id
        
        # 检查是否有上传的文件
        if not request.files:
            return _err("请上传图片文件")
        
        files = request.files.getlist('file') or request.files.getlist('files[]')
        if not files or all(not f.filename for f in files):
            return _err("未找到上传的图片文件")
        
        # 保存上传的文件到临时目录
        image_paths, temp_dir = save_uploaded_files(files, temp_prefix='tts_ocr_')
        if image_paths is None:
            return _err("保存上传文件失败或没有有效的图片文件")
        
        # 启动 OCR 任务（异步执行）
        code, msg = tts_mgr.start_ocr_task(task_id, image_paths, temp_dir)
        if code != 0:
            # 启动失败，清理临时文件
            cleanup_temp_files(temp_dir, image_paths)
            return _err(msg)
        
        log.info(f"[TTS OCR] OCR 任务 {task_id} 已启动，图片数量: {len(image_paths)}")
        return _ok(None)
        
    except Exception as e:
        log.error(f"[TTS OCR] OCR 接口错误: {e}", exc_info=True)
        return _err(f"OCR 识别失败: {str(e)}")
