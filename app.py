# app.py
from flask import Flask, redirect, url_for, request, render_template
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_bootstrap import Bootstrap
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from flask_sqlalchemy import SQLAlchemy
from flask.cli import with_appcontext
import click

# カレントディレクトリをパスに追加
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from models import db, User, OperationLog
from routes.auth import auth_bp
from routes.books import books_bp
from routes.users import users_bp
from routes.admin import admin_bp
from routes.reservations import reservations_bp
from utils.logger import setup_logger
from config import config

@click.command('init-db')
@with_appcontext
def init_db_command():
    """データベースを初期化し、初期管理者ユーザーを作成します。"""
    db.create_all()
    # 初期管理者ユーザーの作成
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', name='管理者', is_admin=True)
        # 環境変数 ADMIN_PASSWORD を取得、なければデフォルト値を使用
        admin_password = os.environ.get('ADMIN_PASSWORD', 'change_me_immediately')
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        print(f'Initialized the database and created the admin user with password: {admin_password}')

        # 操作ログの記録 (requestオブジェクトがないためIPアドレスは'localhost'とする)
        # init-db実行時にはまだadmin.idが決まっていない可能性があるので注意 -> commit後に取得
        admin = User.query.filter_by(username='admin').first() # commit後に再度取得
        if admin:
            log = OperationLog(
                user_id=admin.id,
                action='user_created',
                target='Initial admin user',
                ip_address='localhost' # CLIからの実行を示す
            )
            db.session.add(log)
            db.session.commit()
    else:
        print('Admin user already exists.')

@click.command('reset-admin-password')
@with_appcontext
def reset_admin_password_command():
    """管理者(admin)のパスワードを環境変数 ADMIN_PASSWORD の値でリセットします。"""
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        print("Error: Admin user 'admin' not found.")
        return

    admin_password = os.environ.get('ADMIN_PASSWORD')
    if not admin_password:
        print("Error: ADMIN_PASSWORD environment variable is not set.")
        print("Please set the ADMIN_PASSWORD environment variable and try again.")
        return

    try:
        admin_user.set_password(admin_password)
        db.session.add(admin_user) # オブジェクトが変更されたのでセッションに追加
        db.session.commit()
        print(f"Admin user 'admin' password has been reset using the ADMIN_PASSWORD environment variable.")

        # 必要であれば操作ログを記録
        log = OperationLog(
            user_id=admin_user.id,
            action='admin_password_reset',
            target=f'User: {admin_user.username}',
            details='Admin password reset via CLI command.',
            ip_address='localhost' # CLIからの実行を示す
        )
        db.session.add(log)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print(f"Error resetting admin password: {e}")

def create_app(config_name=None):
    """アプリケーションファクトリ"""
    # FLASK_ENV から設定名を決定、未設定なら 'default' を使う
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(__name__, 
              template_folder='templates',
              static_folder='static')
    
    # CORS設定の追加
    CORS(app)
    
    # 決定した設定名で設定を読み込む
    try:
        app.config.from_object(config[config_name])
    except KeyError:
        print(f"Error: Invalid config name '{config_name}'. Using 'default' config instead.")
        config_name = 'default'
        app.config.from_object(config[config_name])

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }
    
    # ★★★ デバッグ用ログ変更 ★★★
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    log_message = (
        f"!!! DEBUG: Using config '{config_name}'. "
        f"SQLALCHEMY_DATABASE_URI = {db_uri}"
    )
    print(log_message) # print も念のため追加
    # ★★★★★★★★★★★★★★★★★★
    
    # デバッグモードの設定
    app.config['DEBUG'] = True
    
    # テンプレート自動リロードの有効化
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    
    # セッション設定
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1時間
    
    # データベース初期化
    db.init_app(app)
    Bootstrap(app)
    migrate = Migrate(app, db)
    
    # ログインマネージャー設定
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    login_manager.session_protection = 'strong'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # ロガー設定
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/library.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Library startup')
    
    # ブループリント登録
    app.register_blueprint(auth_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(reservations_bp)
    
    # セキュリティヘッダーの設定（開発環境では一部制限を緩和）
    if not app.debug:
        Talisman(app,
            force_https=True,
            session_cookie_secure=True,
            session_cookie_http_only=True,
            feature_policy={
                'geolocation': '\'none\'',
                'midi': '\'none\'',
                'notifications': '\'none\'',
                'push': '\'none\'',
                'sync-xhr': '\'none\'',
                'microphone': '\'none\'',
                'camera': '\'none\'',
                'magnetometer': '\'none\'',
                'gyroscope': '\'none\'',
                'speaker': '\'none\'',
                'vibrate': '\'none\'',
                'fullscreen': '\'none\'',
                'payment': '\'none\''
            }
        )
    else:
        Talisman(app,
            force_https=False,
            session_cookie_secure=False,
            content_security_policy=None
        )
    
    # レート制限の設定
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )
    
    @app.route('/')
    def index():
        return redirect(url_for('books.index'))
    
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return render_template('429.html'), 429
    
    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        app.logger.error(f'Server Error: {e}')
        return render_template('500.html'), 500
    
    @app.before_request
    def before_request():
        if not request.is_secure and not app.debug:
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)
    
    # Flask CLI コマンドの登録
    app.cli.add_command(init_db_command)
    app.cli.add_command(reset_admin_password_command)

    return app