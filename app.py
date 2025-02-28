# app.py
import sys
import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from flask_migrate import Migrate

from models import db, User
from routes.auth import auth_bp
from routes.books import books_bp
from routes.users import users_bp
from routes.reservations import reservations_bp
from utils.logger import setup_logger

def create_app(config_name='default'):
    """アプリケーションファクトリ"""
    app = Flask(__name__)
    
    # 設定の読み込み
    from config import config
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # 基本設定
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///library.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # アップロードディレクトリの設定
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # データベース初期化
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # ログインマネージャー設定
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'ログインしてください。'
    
    # ユーザーローダー設定
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # ロガー設定
    setup_logger(app)
    
    # ブループリント登録
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(reservations_bp)
    
    @app.route('/')
    def index():
        return redirect(url_for('books.index'))
    
    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()  # 開発段階ではこれでDBを初期化（本番ではMigrateを利用）
        
        # 初期管理者ユーザーの作成
        if not db.session.query(User).filter_by(username='admin').first():
            admin = User(username='admin', name='管理者', is_admin=True)
            admin.set_password('adminpass')  # 本番環境では強固なパスワードに変更
            db.session.add(admin)
            db.session.commit()
            
    app.run(debug=True, host='127.0.0.1', port=5000)