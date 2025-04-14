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
    
    # アップロードフォルダの設定
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 最大アップロードサイズ: 16MB
    
    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    """開発環境設定"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'library-dev.db')

class TestingConfig(Config):
    """テスト環境設定"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'library-test.db')
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """本番環境設定"""
    # 環境変数に頼らず、常に絶対パスを指定する
    SQLALCHEMY_DATABASE_URI = 'sqlite:////home/xcdevelopment/library_management/library.db'
    # os.environ.get('DATABASE_URL') or \
    #'sqlite:///' + os.path.join(basedir, 'library.db') # 元のコードをコメントアウト

# 環境設定辞書
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}