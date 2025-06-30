# routes/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse

from models import User, db, OperationLog
from forms.auth import LoginForm, SignupForm

# ★★★ デバッグログ追加 ★★★
from flask import current_app # current_app をインポート
import logging # logging をインポート

# ロガーを取得
log = logging.getLogger(__name__)
log.setLevel(logging.INFO) # INFOレベル以上のログを出力
# 必要に応じてハンドラを設定 (uWSGIなどは標準出力/エラーに出力することが多い)
# 例: stream_handler = logging.StreamHandler()
# log.addHandler(stream_handler)
# ★★★★★★★★★★★★★★★★

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """ログイン処理"""
    # ★★★ デバッグログ追加 ★★★
    log.info("--- Login attempt initiated ---")
    # ★★★★★★★★★★★★★★★★
    if current_user.is_authenticated:
        # ★★★ デバッグログ追加 ★★★
        log.info(f"User already authenticated: {current_user.email}. Redirecting.")
        # ★★★★★★★★★★★★★★★★
        return redirect(url_for('home.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        # ★★★ デバッグログ追加 ★★★
        submitted_email = form.email.data
        # パスワード自体はログに出さない
        log.info(f"Form validated. Email submitted: '{submitted_email}'")
        # ★★★★★★★★★★★★★★★★

        try:
            user = User.query.filter_by(email=submitted_email).first()

            # ★★★ デバッグログ追加 ★★★
            if user:
                log.info(f"User found in DB: {user.email} (ID: {user.id}, Hash: {user.password_hash[:10]}...) ") # ハッシュの一部を表示
                password_check_result = user.check_password(form.password.data)
                log.info(f"Password check result for '{user.email}': {password_check_result}")
                if not password_check_result:
                     log.warning("Password check failed.") # 失敗時に警告レベルで記録
            else:
                log.warning(f"User '{submitted_email}' not found in DB.") # ユーザーが見つからない場合も警告
            # ★★★★★★★★★★★★★★★★

            if user is None or not user.check_password(form.password.data):
                flash('メールアドレスまたはパスワードが正しくありません。', 'danger')
                # ★★★ デバッグログ追加 ★★★
                log.warning("Authentication failed. Rendering login page again.")
                # ★★★★★★★★★★★★★★★★
                return render_template('auth/login.html', form=form)

            login_user(user, remember=form.remember_me.data)
            # ★★★ デバッグログ追加 ★★★
            log.info(f"login_user() called successfully for {user.email}. Redirecting...")
            # ★★★★★★★★★★★★★★★★

            # 操作ログの記録
            try:
                op_log = OperationLog(
                    user_id=user.id,
                    action='login',
                    target=f'user: {user.email}',
                    ip_address=request.remote_addr
                )
                db.session.add(op_log)
                db.session.commit()
            except Exception as e:
                current_app.logger.error(f"Failed to log login operation: {e}")
                db.session.rollback()

            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home.dashboard'))

        except Exception as e:
            # ★★★ デバッグログ追加 ★★★
            log.error(f"Error during login process for user '{submitted_email}': {e}", exc_info=True) # エラー詳細を記録
            # ★★★★★★★★★★★★★★★★
            flash('ログイン処理中にエラーが発生しました。', 'danger')
            return render_template('auth/login.html', form=form)

    elif request.method == 'POST':
         # ★★★ デバッグログ追加 ★★★
         log.warning(f"Form validation failed. Errors: {form.errors}")
         # ★★★★★★★★★★★★★★★★

    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    """ログアウト処理"""
    
    # 操作ログの記録
    try:
        op_log = OperationLog(
            user_id=current_user.id,
            action='logout',
            target=f'user: {current_user.email}',
            ip_address=request.remote_addr
        )
        db.session.add(op_log)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Failed to log logout operation: {e}")
        db.session.rollback()

    logout_user()
    flash('ログアウトしました。', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """サインアップ処理"""
    if current_user.is_authenticated:
        return redirect(url_for('home.dashboard'))
    
    form = SignupForm()
    if form.validate_on_submit():
        # ユーザー作成
        user = User(
            name=form.name.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit() # user.id を確定させるために一度コミット

        # 操作ログの記録
        op_log = OperationLog(
            user_id=user.id,
            action='signup',
            target=f'User: {user.email}',
            ip_address=request.remote_addr
        )
        db.session.add(op_log)
        db.session.commit()
        
        flash('ユーザー登録が完了しました。ログインしてください。', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/signup.html', form=form)