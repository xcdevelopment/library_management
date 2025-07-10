# app.py
from flask import Flask, redirect, url_for, request, render_template
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_bootstrap import Bootstrap
from flask_mail import Mail
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from flask_sqlalchemy import SQLAlchemy
from flask.cli import with_appcontext
import click
from services.slack_service import send_error_notification
import traceback

# カレントディレクトリをパスに追加
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from models import db, User, OperationLog

# Flask-Mail instance for email services
mail = Mail()
from routes.auth import auth_bp
from routes.books import books_bp
from routes.users import users_bp
from routes.admin import admin_bp
from routes.reservations import reservations_bp
from routes.api import api_bp
from routes.home import home_bp
from utils.logger import setup_logger
from config import config

@click.command('init-db')
@with_appcontext
def init_db_command():
    """データベースを初期化し、初期管理者ユーザーを作成します。"""
    db.create_all()
    # 初期管理者ユーザーの作成
    admin_email = 'Development@xcap.co.jp'
    if not User.query.filter_by(email=admin_email).first():
        admin = User(email=admin_email, name='管理者', is_admin=True)
        # 環境変数からパスワードを取得
        from flask import current_app
        admin_password = current_app.config['ADMIN_PASSWORD']
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        print(f'Initialized the database and created the admin user with email: {admin_email}')

        # 操作ログの記録 (requestオブジェクトがないためIPアドレスは'localhost'とする)
        # init-db実行時にはまだadmin.idが決まっていない可能性があるので注意 -> commit後に取得
        admin = User.query.filter_by(email=admin_email).first() # commit後に再度取得
        if admin:
            log = OperationLog(
                user_id=admin.id,
                action='user_created',
                target=f'Initial admin user: {admin.email}',
                ip_address='localhost' # CLIからの実行を示す
            )
            db.session.add(log)
            db.session.commit()
    else:
        print(f"Admin user '{admin_email}' already exists.")

@click.command('reset-admin-password')
@with_appcontext
def reset_admin_password_command():
    """管理者(admin)のパスワードを環境変数 ADMIN_PASSWORD の値でリセットします。"""
    admin_email = 'Development@xcap.co.jp'
    admin_user = User.query.filter_by(email=admin_email).first()
    if not admin_user:
        print(f"Error: Admin user '{admin_email}' not found.")
        return

    from flask import current_app
    admin_password = current_app.config['ADMIN_PASSWORD']

    try:
        admin_user.set_password(admin_password)
        db.session.add(admin_user) # オブジェクトが変更されたのでセッションに追加
        db.session.commit()
        print(f"Admin user '{admin_user.email}' password has been reset using the ADMIN_PASSWORD environment variable.")

        # 必要であれば操作ログを記録
        log = OperationLog(
            user_id=admin_user.id,
            action='admin_password_reset',
            target=f'User: {admin_user.email} - CLI command',
            ip_address='localhost' # CLIからの実行を示す
        )
        db.session.add(log)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print(f"Error resetting admin password for {admin_email}: {e}")

@click.command('create-admin')
@click.option('--email', prompt='管理者のメールアドレス', help='管理者のメールアドレス')
@click.option('--name', prompt='管理者の名前', help='管理者の名前')
@click.option('--password', prompt='パスワード', hide_input=True, confirmation_prompt=True, help='管理者のパスワード')
@with_appcontext
def create_admin_command(email, name, password):
    """新しい管理者ユーザーを作成します。"""
    # 既存ユーザーの確認
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        print(f"Error: User with email '{email}' already exists.")
        return

    try:
        # 新しい管理者ユーザーを作成
        admin = User(
            email=email,
            name=name,
            is_admin=True
        )
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        
        print(f"✅ 管理者ユーザー '{email}' が正常に作成されました。")
        
        # 操作ログの記録
        log = OperationLog(
            user_id=admin.id,
            action='admin_created',
            target=f'User: {admin.email} (Name: {admin.name}) - CLI command',
            ip_address='localhost' # CLIからの実行を示す
        )
        db.session.add(log)
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ 管理者ユーザーの作成中にエラーが発生しました: {e}")

@click.command('list-users')
@click.option('--admin-only', is_flag=True, help='管理者ユーザーのみを表示')
@with_appcontext
def list_users_command(admin_only):
    """ユーザー一覧を表示します。"""
    try:
        if admin_only:
            users = User.query.filter_by(is_admin=True).all()
            print("📋 管理者ユーザー一覧:")
        else:
            users = User.query.all()
            print("📋 全ユーザー一覧:")
        
        if not users:
            print("  ユーザーが見つかりません。")
            return
        
        for user in users:
            admin_status = "👑 管理者" if user.is_admin else "👤 一般"
            print(f"  {admin_status} | {user.email} | {user.name}")
            
    except Exception as e:
        print(f"❌ ユーザー一覧の取得中にエラーが発生しました: {e}")

@click.command('delete-user')
@click.option('--email', prompt='削除するユーザーのメールアドレス', help='削除するユーザーのメールアドレス')
@click.option('--force', is_flag=True, help='確認なしで削除を実行')
@with_appcontext
def delete_user_command(email, force):
    """指定されたユーザーを削除します。"""
    user = User.query.filter_by(email=email).first()
    if not user:
        print(f"❌ メールアドレス '{email}' のユーザーが見つかりません。")
        return
    
    if not force:
        confirm = input(f"⚠️  ユーザー '{email}' ({user.name}) を削除しますか？ (y/N): ")
        if confirm.lower() != 'y':
            print("❌ 削除をキャンセルしました。")
            return
    
    try:
        # 操作ログの記録（削除前に実行）
        log = OperationLog(
            user_id=user.id,
            action='user_deleted',
            target=f'User: {user.email} (Name: {user.name}) - CLI command',
            ip_address='localhost'
        )
        db.session.add(log)
        
        # ユーザーを削除
        db.session.delete(user)
        db.session.commit()
        
        print(f"✅ ユーザー '{email}' が正常に削除されました。")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ ユーザーの削除中にエラーが発生しました: {e}")

@click.command('db-status')
@with_appcontext
def db_status_command():
    """データベースの状態を確認します。"""
    try:
        from sqlalchemy import text
        
        # 接続テスト
        result = db.session.execute(text('SELECT 1'))
        print("✅ データベース接続: 正常")
        
        # ユーザー数
        user_count = User.query.count()
        admin_count = User.query.filter_by(is_admin=True).count()
        print(f"📊 ユーザー統計:")
        print(f"  総ユーザー数: {user_count}")
        print(f"  管理者数: {admin_count}")
        print(f"  一般ユーザー数: {user_count - admin_count}")
        
        # テーブル一覧
        result = db.session.execute(text("SHOW TABLES"))
        tables = [row[0] for row in result]
        print(f"🗄️  テーブル一覧: {', '.join(tables)}")
        
    except Exception as e:
        print(f"❌ データベース状態の確認中にエラーが発生しました: {e}")

def create_admin(app):
    with app.app_context():
        # 初期管理者ユーザーの作成
        email = 'Development@xcap.co.jp'
        password = 'adminpass'
        # ユーザーが既に存在するか確認
        if not User.query.filter_by(email=email).first():
            admin = User(
                email=email,
                name='管理者',
                is_admin=True
            )
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            print(f'管理者アカウント {email} が作成されました。')

            # ログ記録
            log = OperationLog(
                user_id=admin.id,
                action='admin_created',
                target=f'User: {admin.email}',
                ip_address='localhost' # システムによる自動作成
            )
            db.session.add(log)
            db.session.commit()
        else:
            print(f'管理者アカウント {email} は既に存在します。')

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
    
    # 環境に応じたセキュリティ設定
    is_production = os.environ.get('FLASK_ENV') == 'production'
    
    # Talismanの設定
    csp = {
        'default-src': '\'self\'',
        'script-src': [
            '\'self\'',
            '\'unsafe-inline\'',  # インラインJavaScriptを許可
            'https://cdn.jsdelivr.net'
        ],
        'style-src': [
            '\'self\'',
            '\'unsafe-inline\'',  # インラインCSSを許可
            'https://cdn.jsdelivr.net',
            'https://cdnjs.cloudflare.com'
        ],
        'img-src': [
            '\'self\'',
            'data:',  # data URIを許可（Bootstrap selectボックスのアイコン用）
            'https:'
        ],
        'font-src': [
            '\'self\'',
            'https://cdnjs.cloudflare.com'
        ]
    }

    Talisman(app,
        force_https=is_production,  # 本番環境でのみHTTPSを強制
        session_cookie_secure=is_production,
        session_cookie_http_only=True,
        session_cookie_samesite='Lax',
        content_security_policy=csp,
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
    
    # セッション設定
    app.config['SESSION_COOKIE_SECURE'] = is_production
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1時間
    
    # データベース初期化
    db.init_app(app)
    Bootstrap(app)
    migrate = Migrate(app, db)
    
    # メール初期化
    mail.init_app(app)
    
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
    
    # Blueprintの登録
    app.register_blueprint(home_bp)  # ルートパスで登録
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(books_bp, url_prefix='/books')
    app.register_blueprint(users_bp, url_prefix='/users')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(reservations_bp, url_prefix='/reservations')
    app.register_blueprint(api_bp, url_prefix='/api')

    # カスタムCLIコマンドの登録
    app.cli.add_command(init_db_command)
    app.cli.add_command(reset_admin_password_command)
    app.cli.add_command(create_admin_command)
    app.cli.add_command(list_users_command)
    app.cli.add_command(delete_user_command)
    app.cli.add_command(db_status_command)

    # レート制限の設定
    try:
        if is_production:
            # 本番環境ではRedisを使用
            import redis
            redis_client = redis.Redis(
                host=os.environ.get('REDIS_HOST', 'localhost'),
                port=int(os.environ.get('REDIS_PORT', 6379)),
                db=0,
                decode_responses=True
            )
            limiter = Limiter(
                app=app,
                key_func=get_remote_address,
                default_limits=["200 per day", "50 per hour"],
                storage_uri="redis://{}:{}".format(
                    os.environ.get('REDIS_HOST', 'localhost'),
                    os.environ.get('REDIS_PORT', 6379)
                )
            )
        else:
            # 開発環境ではメモリストレージを使用（警告を抑制）
            limiter = Limiter(
                app=app,
                key_func=get_remote_address,
                default_limits=["200 per day", "50 per hour"]
            )
    except Exception as e:
        # Redis接続に失敗した場合はメモリストレージにフォールバック
        print(f"Warning: Redis connection failed, using memory storage: {e}")
        limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            default_limits=["200 per day", "50 per hour"]
        )
    
    
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return render_template('429.html'), 429
    
    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        
        # スタックトレースを取得
        tb_str = traceback.format_exc()
        error_message = f"Error: {e}\nTraceback:\n{tb_str}"
        
        app.logger.error(f'Server Error: {error_message}')
        
        # Slack通知を送信
        send_error_notification(error_message)

        return render_template('500.html'), 500
    
    @app.before_request
    def before_request():
        # 'DYNO'はHerokuなどのPaaSで設定される環境変数。本番環境判定に利用。
        is_production = os.environ.get('DYNO') is not None
        if not request.is_secure and is_production:
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)

    return app

if __name__ == "__main__":
    app = create_app()
    if is_production:
        app.run(
            host="0.0.0.0",
            port=5000,
            ssl_context=("ssl/localhost.pem", "ssl/localhost-key.pem")
        )
    else:
        app.run(host="0.0.0.0", port=5000)