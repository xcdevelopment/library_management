# config.py
import os
from datetime import timedelta
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

load_dotenv()

class Config:
    """基本設定"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)  # セッション有効期限
    
    # Power Automate Webhook URL
    POWER_AUTOMATE_WEBHOOK_URL = os.environ.get('POWER_AUTOMATE_WEBHOOK_URL')
    
    # アップロードフォルダの設定
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 最大アップロードサイズ: 16MB
    
    # APIキーの設定
    API_KEY = os.environ.get('API_KEY') or 'your_very_secret_api_key'
    
    # メール設定
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'localhost'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@library.local'
    
    # Slack連携
    SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
    SLACK_ENABLED = os.environ.get('SLACK_ENABLED', 'false').lower() in ['true', '1', 't']
    ADMIN_SLACK_EMAIL = os.environ.get('ADMIN_SLACK_EMAIL', 'Development@xcap.co.jp')
    
    # 管理者パスワード
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'adminpass')
    
    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    """開発環境設定"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'mysql+pymysql://root:password@db/library_dev'
    # SERVER_NAME = os.environ.get('SERVER_NAME')  # コメントアウトして柔軟性を向上
    PREFERRED_URL_SCHEME = 'http'

class TestingConfig(Config):
    """テスト環境設定"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'mysql+pymysql://root:password@db/library_test'
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """本番環境設定"""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://root:password@db/library'

# 環境設定辞書
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}