# routes/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse

from models import User, db, OperationLog

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """ログイン処理"""
    if current_user.is_authenticated:
        return redirect(url_for('books.index'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = 'remember' in request.form
        
        user = User.query.filter_by(username=username).first()
        
        if user is None or not user.check_password(password):
            flash('ユーザー名またはパスワードが正しくありません。', 'danger')
            return render_template('auth/login.html')
            
        login_user(user, remember=remember)
        
        # 操作ログの記録
        log = OperationLog(
            user_id=user.id,
            action='login',
            target=f'User: {user.username}',
            details=f'Login successful for user {user.username}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('books.index')
            
        return redirect(next_page)
        
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """ログアウト処理"""
    # 操作ログの記録
    log = OperationLog(
        user_id=current_user.id,
        action='logout',
        target=f'User: {current_user.username}',
        details=f'Logout successful for user {current_user.username}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    logout_user()
    flash('ログアウトしました。', 'info')
    return redirect(url_for('auth.login'))