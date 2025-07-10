# セキュリティ設定ガイド

## 目次
1. [概要](#概要)
2. [環境変数の管理](#環境変数の管理)
3. [データベースセキュリティ](#データベースセキュリティ)
4. [Webアプリケーションセキュリティ](#webアプリケーションセキュリティ)
5. [ネットワークセキュリティ](#ネットワークセキュリティ)
6. [コンテナセキュリティ](#コンテナセキュリティ)
7. [監査とログ](#監査とログ)
8. [インシデント対応](#インシデント対応)

## 概要

このドキュメントでは、図書館管理システムのセキュリティ設定について詳細に説明します。

### セキュリティ原則
- 最小権限の原則
- 多層防御
- セキュリティバイデザイン
- 継続的な監視

## 環境変数の管理

### 機密情報の分類

**高機密情報**
- データベースパスワード
- APIキー
- シークレットキー
- SSL証明書の秘密鍵

**中機密情報**
- メールサーバー設定
- 外部サービス連携設定
- 管理者アカウント情報

**低機密情報**
- アプリケーション設定
- ログレベル設定
- 機能フラグ

### 環境変数の暗号化

```bash
# 環境変数の暗号化例
# 本番環境では、HashiCorp VaultやAWS Secrets Managerの使用を推奨

# 一時的な暗号化（開発用）
echo "your-secret-password" | base64
```

### 環境変数の検証

```python
# config.py に追加する検証ロジック
import os
from typing import Optional

def validate_required_env_vars() -> None:
    """必須環境変数の検証"""
    required_vars = [
        'SECRET_KEY',
        'DATABASE_URL',
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
```

## データベースセキュリティ

### MySQL設定の強化

```sql
-- ユーザー権限の最小化
CREATE USER 'library_user'@'%' IDENTIFIED BY 'strong_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON library.* TO 'library_user'@'%';
GRANT EXECUTE ON library.* TO 'library_user'@'%';
FLUSH PRIVILEGES;

-- 不要なユーザーの削除
DROP USER IF EXISTS 'test'@'%';
DROP USER IF EXISTS 'anonymous'@'%';

-- パスワードポリシーの設定
SET GLOBAL validate_password.policy=MEDIUM;
SET GLOBAL validate_password.length=12;
```

### 接続の暗号化

```python
# SQLAlchemy設定でSSL接続を有効化
SQLALCHEMY_DATABASE_URI = (
    "mysql+pymysql://user:password@host/database"
    "?ssl_ca=/path/to/ca-cert.pem"
    "&ssl_cert=/path/to/client-cert.pem"
    "&ssl_key=/path/to/client-key.pem"
)
```

### データベース監査

```sql
-- 監査ログの有効化
CREATE TABLE audit_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action VARCHAR(50),
    table_name VARCHAR(50),
    record_id INT,
    old_values JSON,
    new_values JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45)
);

-- トリガーの作成例
DELIMITER //
CREATE TRIGGER books_audit_update
AFTER UPDATE ON books
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (user_id, action, table_name, record_id, old_values, new_values)
    VALUES (
        @current_user_id,
        'UPDATE',
        'books',
        NEW.id,
        JSON_OBJECT('title', OLD.title, 'author', OLD.author),
        JSON_OBJECT('title', NEW.title, 'author', NEW.author)
    );
END//
DELIMITER ;
```

## Webアプリケーションセキュリティ

### セッション管理

```python
# Flask-Session設定の強化
from datetime import timedelta

class ProductionConfig(Config):
    # セッション設定
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_NAME = '__Host-session'
    
    # CSRF保護
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_SSL_STRICT = True
```

### 入力検証

```python
# 入力検証の強化
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Length, Email, Regexp

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(),
        Email(),
        Length(max=254)
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, max=128),
        Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]',
               message='Password must contain uppercase, lowercase, number and special character')
    ])
```

### XSS対策

```python
# テンプレートでのXSS対策
from markupsafe import escape

@app.route('/search')
def search():
    query = escape(request.args.get('q', ''))
    return render_template('search.html', query=query)

# テンプレート内
{{ query|safe }}  # 危険 - 使用しない
{{ query }}       # 安全 - 自動エスケープ
```

### SQLインジェクション対策

```python
# SQLAlchemy ORMの使用（推奨）
books = Book.query.filter_by(author=author).all()

# 生SQLを使用する場合のパラメータ化
from sqlalchemy import text
result = db.session.execute(
    text("SELECT * FROM books WHERE author = :author"),
    {"author": author}
)
```

## ネットワークセキュリティ

### ファイアウォール設定

```bash
# UFW設定例
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# iptables設定例（より詳細な制御）
# SSH接続制限
iptables -A INPUT -p tcp --dport 22 -m state --state NEW -m recent --set --name SSH
iptables -A INPUT -p tcp --dport 22 -m state --state NEW -m recent --update --seconds 60 --hitcount 4 --name SSH -j DROP

# レート制限
iptables -A INPUT -p tcp --dport 80 -m limit --limit 25/minute --limit-burst 100 -j ACCEPT
```

### SSL/TLS設定

```nginx
# Nginx SSL設定の強化
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;

# HSTS設定
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

# セキュリティヘッダー
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';" always;
```

## コンテナセキュリティ

### Dockerfileのセキュリティ

```dockerfile
# マルチステージビルド
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim

# 非rootユーザーの作成
RUN groupadd -r appuser && useradd -r -g appuser appuser

# セキュリティアップデート
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /root/.local /home/appuser/.local
COPY . .

# 権限設定
RUN chown -R appuser:appuser /app
USER appuser

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1
```

### Docker Composeセキュリティ

```yaml
version: '3.8'
services:
  web:
    build: .
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp
    environment:
      - PYTHONUNBUFFERED=1
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
```

## 監査とログ

### ログ設定

```python
# ログ設定の強化
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging(app):
    if not app.debug and not app.testing:
        # ファイルログ
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/library.log', 
            maxBytes=10240000, 
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        # セキュリティイベントのログ
        security_handler = RotatingFileHandler(
            'logs/security.log',
            maxBytes=10240000,
            backupCount=10
        )
        security_handler.setLevel(logging.WARNING)
        app.logger.addHandler(security_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Library startup')
```

### セキュリティイベントの監視

```python
# セキュリティイベントの記録
import logging
from datetime import datetime
from flask import request, g

security_logger = logging.getLogger('security')

def log_security_event(event_type, details, user_id=None, ip_address=None):
    """セキュリティイベントをログに記録"""
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': event_type,
        'user_id': user_id or g.user.id if hasattr(g, 'user') else None,
        'ip_address': ip_address or request.remote_addr,
        'user_agent': request.headers.get('User-Agent'),
        'details': details
    }
    security_logger.warning(f"Security event: {log_entry}")

# 使用例
@app.route('/login', methods=['POST'])
def login():
    try:
        # ログイン処理
        if login_successful:
            log_security_event('LOGIN_SUCCESS', {'email': email})
        else:
            log_security_event('LOGIN_FAILURE', {'email': email, 'reason': 'invalid_credentials'})
    except Exception as e:
        log_security_event('LOGIN_ERROR', {'error': str(e)})
```

## インシデント対応

### セキュリティインシデントの分類

**重大度レベル**
1. **Critical**: データ漏洩、システム侵害
2. **High**: 認証バイパス、権限昇格
3. **Medium**: 情報開示、サービス拒否
4. **Low**: 設定ミス、軽微な脆弱性

### インシデント対応手順

```python
# インシデント対応フレームワーク
class SecurityIncident:
    def __init__(self, severity, description, affected_systems):
        self.severity = severity
        self.description = description
        self.affected_systems = affected_systems
        self.timestamp = datetime.utcnow()
        self.status = 'open'
    
    def escalate(self):
        """重大インシデントのエスカレーション"""
        if self.severity in ['Critical', 'High']:
            # 管理者への通知
            send_security_alert(self)
            # ログの保存
            log_security_event('INCIDENT_ESCALATED', self.__dict__)
    
    def contain(self):
        """インシデントの封じ込め"""
        # 影響を受けたシステムの隔離
        # アクセスの一時停止
        pass
    
    def eradicate(self):
        """根本原因の除去"""
        # 脆弱性の修正
        # マルウェアの除去
        pass
    
    def recover(self):
        """システムの復旧"""
        # サービスの再開
        # データの復元
        pass
```

### 自動化されたセキュリティ監視

```python
# セキュリティ監視スクリプト
import subprocess
import json
from datetime import datetime, timedelta

def check_security_events():
    """セキュリティイベントの定期チェック"""
    # ログファイルの監視
    with open('logs/security.log', 'r') as f:
        recent_events = []
        for line in f:
            if 'Security event' in line:
                # 最近のイベントを解析
                pass
    
    # 異常検知
    failed_logins = count_failed_logins(recent_events)
    if failed_logins > 10:  # 閾値
        send_security_alert('Multiple failed login attempts detected')
    
    # システムリソースの監視
    check_system_resources()

def check_system_resources():
    """システムリソースの監視"""
    # CPU使用率
    cpu_usage = subprocess.check_output(['top', '-bn1']).decode()
    
    # メモリ使用率
    memory_usage = subprocess.check_output(['free', '-m']).decode()
    
    # ディスク使用率
    disk_usage = subprocess.check_output(['df', '-h']).decode()
    
    # 異常値の検出
    if cpu_usage > 90:
        send_security_alert('High CPU usage detected')
```

### 定期的なセキュリティ監査

```bash
#!/bin/bash
# security_audit.sh

# 1. 脆弱性スキャン
docker run --rm -v $(pwd):/app owasp/zap2docker-stable zap-baseline.py -t http://localhost

# 2. 依存関係の脆弱性チェック
pip-audit

# 3. セキュリティ設定の確認
docker-compose exec web python -c "
import os
from config import validate_required_env_vars, validate_secret_key_strength
validate_required_env_vars()
validate_secret_key_strength()
print('Security validation passed')
"

# 4. ログの分析
grep -i "security\|error\|warning" logs/library.log | tail -100

# 5. ファイル権限の確認
find . -type f -exec ls -la {} \; | grep -E "\.(py|conf|env)$"
```

## セキュリティチェックリスト

### デプロイ前チェックリスト
- [ ] 環境変数の暗号化
- [ ] データベースパスワードの変更
- [ ] SSL証明書の設定
- [ ] ファイアウォールの設定
- [ ] ログ設定の確認
- [ ] バックアップ設定の確認

### 定期チェックリスト
- [ ] セキュリティパッチの適用
- [ ] ログの監視
- [ ] アクセス権限の確認
- [ ] バックアップの検証
- [ ] パフォーマンス監視
- [ ] セキュリティスキャンの実行

### インシデント対応チェックリスト
- [ ] インシデントの記録
- [ ] 影響範囲の特定
- [ ] 封じ込め措置の実施
- [ ] 根本原因の調査
- [ ] 修正措置の実施
- [ ] 再発防止策の検討 