from functools import wraps
from flask import flash, redirect, url_for, request, jsonify, current_app
from flask_login import current_user

def admin_required(f):
    """管理者権限が必要な処理のためのデコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('この操作には管理者権限が必要です。', 'danger')
            return redirect(url_for('books.index'))
        return f(*args, **kwargs)
    return decorated_function

def api_key_required(f):
    """APIキー認証を要求するデコレーター"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-KEY')
        if api_key and api_key == current_app.config.get('API_KEY'):
            return f(*args, **kwargs)
        else:
            return jsonify({"error": "Invalid or missing API key"}), 401
    return decorated_function