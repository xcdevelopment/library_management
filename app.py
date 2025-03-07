# app.py
from flask import Flask, redirect, url_for, request, render_template
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from utils.email import mail
import os
import sys
import logging
from logging.handlers import RotatingFileHandler

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

def create_app(config_name='default'):
    """アプリケーションファクトリ"""
    app = Flask(__name__)
    
    # 設定の読み込み
    app.config.from_object(config[config_name])
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }
    
    # セッション設定
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1時間
    
    # メール設定
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', '587'))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@example.com')
    
    # データベース初期化
    db.init_app(app)
    migrate = Migrate(app, db)
    mail.init_app(app)
    
    # ログインマネージャー設定
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'ログインしてください。'
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
    
    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
        
        # 初期管理者ユーザーの作成
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', name='管理者', is_admin=True)
            admin.set_password(os.environ.get('ADMIN_PASSWORD', 'change_me_immediately'))
            db.session.add(admin)
            db.session.commit()
            
            # 操作ログの記録
            log = OperationLog(
                user_id=admin.id,
                action='user_created',
                target='Initial admin user',
                ip_address=request.remote_addr if request else 'localhost'
            )
            db.session.add(log)
            db.session.commit()
    
    app.run(debug=True)