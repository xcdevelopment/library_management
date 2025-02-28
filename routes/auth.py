# routes/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from datetime import datetime
from hmac import compare_digest

from models import User, OperationLog, db
from services.auth_service import create_user_operation_log
from utils.forms import LoginForm

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """ログイン処理"""
    try:
        # ログイン済みの場合はリダイレクト
        if current_user.is_authenticated:
            return redirect(url_for('books.index'))
        
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            
            # ユーザーが存在し、パスワードが一致する場合
            if user and user.check_password(form.password.data):
                # アカウントが無効化されていないか確認
                if not user.is_active:
                    flash('このアカウントは無効化されています。', 'danger')
                    return render_template('login.html', title='ログイン', form=form)
                
                login_user(user, remember=form.remember_me.data)
                
                # 操作ログの記録
                log_data = {
                    'timestamp': datetime.utcnow(),
                    'ip_address': request.remote_addr,
                    'user_agent': request.user_agent.string
                }
                create_user_operation_log(
                    user.id, 
                    'login', 
                    'ユーザー', 
                    f'{user.username}がログインしました',
                    request.remote_addr,
                    additional_data=log_data
                )
                
                # リダイレクト先の処理
                next_page = request.args.get('next')
                if not next_page or not compare_digest(urlparse(next_page).netloc, ''):
                    next_page = url_for('books.index')
                return redirect(next_page)
            
            # ログイン失敗時のログ記録
            create_user_operation_log(
                None,
                'login_failed',
                'ユーザー',
                f'ログイン失敗: {form.username.data}',
                request.remote_addr
            )
            
            # セキュリティのため、具体的なエラー理由は表示しない
            flash('ユーザー名またはパスワードが正しくありません。', 'danger')
        
        return render_template('login.html', title='ログイン', form=form)
    
    except Exception as e:
        # エラーログの記録
        create_user_operation_log(
            None,
            'error',
            'システム',
            f'ログイン処理でエラーが発生: {str(e)}',
            request.remote_addr
        )
        abort(500)

@auth_bp.route('/logout')
@login_required
def logout():
    """ログアウト処理"""
    try:
        user_id = current_user.id
        username = current_user.username
        
        # 操作ログの記録
        log_data = {
            'timestamp': datetime.utcnow(),
            'ip_address': request.remote_addr,
            'user_agent': request.user_agent.string
        }
        create_user_operation_log(
            user_id,
            'logout',
            'ユーザー',
            f'{username}がログアウトしました',
            request.remote_addr,
            additional_data=log_data
        )
        
        logout_user()
        flash('ログアウトしました。', 'info')
        return redirect(url_for('auth.login'))
    
    except Exception as e:
        # エラーログの記録
        create_user_operation_log(
            None,
            'error',
            'システム',
            f'ログアウト処理でエラーが発生: {str(e)}',
            request.remote_addr
        )
        abort(500)

