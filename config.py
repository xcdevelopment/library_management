# config.py
import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """基本設定クラス"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///library.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)  # セッション有効期限
    
    # アップロード設定
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    
    # メール設定
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.example.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USE_STARTTLS = os.environ.get('MAIL_USE_STARTTLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'library@example.com'
    
    # 予約設定
    MAX_RESERVATIONS_PER_USER = 5
    RESERVATION_HOLD_DAYS = 7
    DEFAULT_LOAN_DAYS = 14
    
    @staticmethod
    def init_app(app):
        # アップロードディレクトリの作成
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

class DevelopmentConfig(Config):
    """開発環境設定"""
    DEBUG = True

class TestingConfig(Config):
    """テスト環境設定"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

class ProductionConfig(Config):
    """本番環境設定"""
    pass

class DefaultConfig(Config):
    """デフォルト設定"""
    DEBUG = True

# 設定の辞書
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DefaultConfig
}