'''
工具函数
'''
import socket
import requests
from flask import jsonify


def _ok(data=None, msg="ok"):
    """
    返回成功响应
    :param data: 响应数据
    :param msg: 响应消息
    :return: JSON响应
    """
    return jsonify({"code": 0, "msg": msg, "data": data})


def _err(msg="error", code=-1):
    """
    返回错误响应
    :param msg: 错误消息
    :param code: 错误代码，默认为-1
    :return: JSON响应
    """
    return jsonify({"code": code, "msg": msg})


def _convert_result(result):
    """
    将字典格式的结果转换为统一的响应格式
    :param result: 字典格式的结果或已经是响应对象
    :return: JSON响应
    """
    # 如果已经是响应对象，直接返回
    if hasattr(result, 'status_code'):
        return result
    
    # 如果是字典格式，转换为响应
    if isinstance(result, dict):
        code = result.get('code', -1)
        msg = result.get('msg', 'error' if code != 0 else 'ok')
        data = result.get('data')
        
        if code == 0:
            return _ok(data=data, msg=msg)
        else:
            return _err(msg=msg, code=code)
    
    # 其他情况直接返回
    return result


def _send_http_request(url: str, method: str = 'GET', data: dict = None, headers: dict = None):
    """
    发送 HTTP 请求
    :param url: 请求 URL
    :param method: HTTP 方法 (GET, POST, PUT, DELETE)
    :param data: 请求数据（用于 POST/PUT）
    :param headers: 请求头
    :return: 响应结果
    """
    try:
        method = method.upper()
        timeout = 5  # 5秒超时
        
        # 使用字典映射简化方法调用
        method_map = {
            'GET': requests.get,
            'POST': requests.post,
            'PUT': requests.put,
            'DELETE': requests.delete
        }
        
        request_func = method_map.get(method)
        if not request_func:
            return {"success": False, "error": f"不支持的 HTTP 方法: {method}"}
        
        # 统一处理请求参数
        kwargs = {'headers': headers, 'timeout': timeout}
        if method in ('POST', 'PUT') and data:
            kwargs['json'] = data
        
        response = request_func(url, **kwargs)
        
        return {
            "success": True,
            "status_code": response.status_code,
            "response": response.text[:500]  # 限制响应长度
        }
    except requests.exceptions.Timeout:
        return {"success": False, "error": "请求超时"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"未知错误: {str(e)}"}


def get_local_ip() -> str:
    """
    获取本机IP地址
    :return: IP地址字符串
    """
    try:
        # 连接到一个远程地址来获取本机IP（不实际发送数据）
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            try:
                s.connect(('8.8.8.8', 80))
                return s.getsockname()[0]
            except Exception:
                return '127.0.0.1'
    except Exception:
        return '127.0.0.1'
