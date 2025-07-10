# config.py
import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

load_dotenv()

def validate_required_env_vars() -> None:
    """必須環境変数の検証"""
    required_vars = [
        'SECRET_KEY',
        'MYSQL_ROOT_PASSWORD'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")

def validate_secret_key_strength() -> None:
    """シークレットキーの強度検証"""
    secret_key = os.environ.get('SECRET_KEY', '')
    if len(secret_key) < 32:
        raise ValueError("SECRET_KEY must be at least 32 characters long")

class Config:
    """基本設定"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_urlsafe(32)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.environ.get('SESSION_LIFETIME_HOURS', 2)))
    
    # セッションセキュリティ設定
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_NAME = '__Host-session' if SESSION_COOKIE_SECURE else 'session'
    
    # CSRF保護
    WTF_CSRF_ENABLED = os.environ.get('WTF_CSRF_ENABLED', 'true').lower() == 'true'
    WTF_CSRF_TIME_LIMIT = int(os.environ.get('WTF_CSRF_TIME_LIMIT', 3600))
    WTF_CSRF_SSL_STRICT = SESSION_COOKIE_SECURE
    
    # Power Automate Webhook URL
    POWER_AUTOMATE_WEBHOOK_URL = os.environ.get('POWER_AUTOMATE_WEBHOOK_URL')
    
    # アップロードフォルダの設定
    UPLOAD_FOLDER = os.path.join(basedir, os.environ.get('UPLOAD_FOLDER', 'uploads'))
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    
    # APIキーの設定
    API_KEY = os.environ.get('API_KEY') or secrets.token_urlsafe(32)
    
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
    
    # パスワードポリシー
    MIN_PASSWORD_LENGTH = int(os.environ.get('MIN_PASSWORD_LENGTH', 8))
    REQUIRE_SPECIAL_CHARS = os.environ.get('REQUIRE_SPECIAL_CHARS', 'false').lower() == 'true'
    REQUIRE_NUMBERS = os.environ.get('REQUIRE_NUMBERS', 'false').lower() == 'true'
    REQUIRE_UPPERCASE = os.environ.get('REQUIRE_UPPERCASE', 'false').lower() == 'true'
    
    # ログ設定
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/library.log')
    LOG_MAX_SIZE = int(os.environ.get('LOG_MAX_SIZE', 10 * 1024 * 1024))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 5))
    
    # レート制限
    RATE_LIMIT_ENABLED = os.environ.get('RATE_LIMIT_ENABLED', 'false').lower() == 'true'
    RATE_LIMIT_REQUESTS = int(os.environ.get('RATE_LIMIT_REQUESTS', 100))
    RATE_LIMIT_WINDOW = int(os.environ.get('RATE_LIMIT_WINDOW', 900))  # 15分
    
    # ヘルスチェック
    HEALTH_CHECK_ENABLED = os.environ.get('HEALTH_CHECK_ENABLED', 'true').lower() == 'true'
    HEALTH_CHECK_INTERVAL = int(os.environ.get('HEALTH_CHECK_INTERVAL', 30))
    
    @staticmethod
    def init_app(app):
        # 環境変数の検証
        try:
            validate_required_env_vars()
            validate_secret_key_strength()
        except ValueError as e:
            app.logger.error(f"Configuration error: {e}")
            if app.config['ENV'] == 'production':
                raise

class DevelopmentConfig(Config):
    """開発環境設定"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'mysql+pymysql://root:password@db/library_dev'
    PREFERRED_URL_SCHEME = 'http'
    
    # 開発環境ではセキュリティ設定を緩和
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_SSL_STRICT = False

class TestingConfig(Config):
    """テスト環境設定"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'mysql+pymysql://root:password@db/library_test'
    WTF_CSRF_ENABLED = False
    
    # テスト環境ではセキュリティ設定を緩和
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_SSL_STRICT = False

class ProductionConfig(Config):
    """本番環境設定"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://root:password@db/library'
    
    # 本番環境ではセキュリティ設定を強化
    SESSION_COOKIE_SECURE = True
    WTF_CSRF_SSL_STRICT = True
    
    # 本番環境専用設定
    SERVER_NAME = os.environ.get('SERVER_NAME')
    PREFERRED_URL_SCHEME = 'https'
    
    # セキュリティヘッダー
    STRICT_TRANSPORT_SECURITY = os.environ.get('STRICT_TRANSPORT_SECURITY', 'true').lower() == 'true'
    CONTENT_SECURITY_POLICY = os.environ.get('CONTENT_SECURITY_POLICY', 'true').lower() == 'true'
    X_FRAME_OPTIONS = os.environ.get('X_FRAME_OPTIONS', 'DENY')
    X_CONTENT_TYPE_OPTIONS = os.environ.get('X_CONTENT_TYPE_OPTIONS', 'nosniff')
    X_XSS_PROTECTION = os.environ.get('X_XSS_PROTECTION', '1; mode=block')
    
    # SSL/TLS設定
    SSL_CERT_FILE = os.environ.get('SSL_CERT_FILE')
    SSL_KEY_FILE = os.environ.get('SSL_KEY_FILE')

# 環境設定辞書
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}