from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def admin_required(f):
    """管理者権限が必要な処理のためのデコレータ"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('この操作には管理者権限が必要です。', 'danger')
            return redirect(url_for('books.index'))
        return f(*args, **kwargs)
    return decorated_function