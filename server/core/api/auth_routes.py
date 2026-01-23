"""Auth routes for JWT login/refresh/logout."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict

from flask import Blueprint, jsonify
from flask.typing import ResponseReturnValue
from flask_jwt_extended import (create_access_token, create_refresh_token, get_jwt_identity, jwt_required,
                                set_refresh_cookies, unset_jwt_cookies)

from core.config import app_logger, config
from core.db import db_obj
from core.models.user import User
from core.utils import read_json_from_request

log = app_logger

# Mounted at /api by create_app registration, so routes are /auth/login etc
auth_bp = Blueprint('auth', __name__)


@auth_bp.route("/auth/login", methods=["POST"])
def auth_login() -> ResponseReturnValue:
    """Username/password login.

    Returns access_token in JSON and sets refresh_token as HttpOnly cookie.
    """
    try:
        data: Dict[str, Any] = read_json_from_request()
        username = str(data.get('username') or '').strip()
        password = str(data.get('password') or '')

        if not username or not password:
            return {"code": -1, "msg": "username and password required"}, 400

        # Password compatibility:
        # legacy frontend uses CryptoJS.MD5(password).toString() and compares to user.pwd.
        user = db_obj.session.query(User).filter(User.name == username).first()
        if not user:
            return {"code": -1, "msg": "invalid credentials"}, 401

        ok = False
        if user.pwd is None:
            ok = True
        elif str(user.pwd) == password:
            ok = True
        else:
            try:
                import hashlib

                md5 = hashlib.md5(password.encode('utf-8')).hexdigest()
                if str(user.pwd) == md5:
                    ok = True
            except Exception:
                pass

        if not ok:
            return {"code": -1, "msg": "invalid credentials"}, 401

        identity = {"id": user.id, "name": user.name, "admin": int(user.admin or 0)}
        access_expires = timedelta(days=int(config.JWT_ACCESS_DAYS))
        refresh_expires = timedelta(days=int(config.JWT_REFRESH_DAYS))

        access_token = create_access_token(identity=identity, expires_delta=access_expires)
        refresh_token = create_refresh_token(identity=identity, expires_delta=refresh_expires)

        resp = jsonify({
            "code": 0,
            "msg": "ok",
            "access_token": access_token,
            "expires_in": int(access_expires.total_seconds()),
            "user": user.to_dict(),
        })
        set_refresh_cookies(resp, refresh_token)
        return resp

    except Exception as e:
        log.error(f"[Auth] login failed: {e}")
        return {"code": -1, "msg": f"error: {str(e)}"}, 500


@auth_bp.route("/auth/refresh", methods=["POST"])
@jwt_required(refresh=True)
def auth_refresh() -> ResponseReturnValue:
    identity = get_jwt_identity()
    access_expires = timedelta(days=int(config.JWT_ACCESS_DAYS))
    access_token = create_access_token(identity=identity, expires_delta=access_expires)
    return {
        "code": 0,
        "msg": "ok",
        "access_token": access_token,
        "expires_in": int(access_expires.total_seconds()),
    }


@auth_bp.route("/auth/logout", methods=["POST"])
def auth_logout() -> ResponseReturnValue:
    resp = jsonify({"code": 0, "msg": "ok"})
    unset_jwt_cookies(resp)
    return resp
