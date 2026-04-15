import json
import inspect
from typing import Any, Dict

# 可自行扩展
SENSITIVE_KEYS = {"api_key", "authorization", "token", "access_token"}


def sanitize(data: Any):
    """递归脱敏 + 保证可序列化"""
    if isinstance(data, dict):
        return {
            k: ("***" if k.lower() in SENSITIVE_KEYS else sanitize(v))
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [sanitize(i) for i in data]
    elif isinstance(data, bytes):
        return f"<bytes:{len(data)}>"
    elif hasattr(data, "read"):
        return "<file>"
    elif isinstance(data, str) and data.startswith("data:"):
        return data[:100] + "...(truncated)"
    else:
        try:
            json.dumps(data)
            return data
        except Exception:
            return str(data)


def get_full_func_name(func):
    """
    获取完整函数路径：
    例如：dashscope.MultiModalConversation.call
    """
    try:
        module = func.__module__
        qualname = func.__qualname__

        # 去掉内部路径（让日志更干净）
        # 如 dashscope.api_entities.xxx.MultiModalConversation.call
        # → dashscope.MultiModalConversation.call
        parts = qualname.split(".")
        if len(parts) >= 2:
            qualname = ".".join(parts[-2:])

        # 取顶级 module（通常就是包名）
        module = module.split(".")[0]

        return f"{module}.{qualname}"
    except Exception:
        return repr(func)


def build_request_record(func, *args, **kwargs) -> Dict:
    func_name = get_full_func_name(func)

    try:
        sig = inspect.signature(func)
        bound = sig.bind_partial(*args, **kwargs)
        bound.apply_defaults()
        params = dict(bound.arguments)
    except Exception:
        # fallback（兼容 C 扩展 / 动态函数）
        params = {
            "_args": args,
            **kwargs
        }

    return {
        "function": func_name,
        "request": sanitize(params)
    }


def capture_request(func):
    """
    伪装饰器：支持 capture_request(func)(...)
    """
    def wrapper(*args, **kwargs):
        request = build_request_record(func, *args, **kwargs)
        try:
            response = func(*args, **kwargs)
        except Exception as exc:
            # 将请求快照挂到异常对象，便于上层失败日志记录 request_content。
            try:
                setattr(exc, "request_record", request)
            except Exception:
                pass
            raise
        return response, request

    return wrapper