# 図書館管理システム - デプロイメントガイド

## 目次
1. [概要](#概要)
2. [前提条件](#前提条件)
3. [環境別デプロイ](#環境別デプロイ)
4. [セキュリティ設定](#セキュリティ設定)
5. [監視とログ](#監視とログ)
6. [バックアップ](#バックアップ)
7. [トラブルシューティング](#トラブルシューティング)

## 概要

このドキュメントでは、図書館管理システムの安全なデプロイ手順について説明します。

### アーキテクチャ
```
[Internet] → [Nginx (SSL/TLS)] → [Flask App] → [MySQL Database]
```

## 前提条件

### 必要なソフトウェア
- Docker 20.10+
- Docker Compose 2.0+
- Git
- OpenSSL（証明書生成用）

### システム要件
- CPU: 2コア以上
- メモリ: 4GB以上
- ストレージ: 20GB以上
- OS: Linux (Ubuntu 20.04+推奨)

## 環境別デプロイ

### 開発環境

1. **リポジトリのクローン**
```bash
git clone <repository-url>
cd library_management
```

2. **環境変数の設定**
```bash
cp env.development .env
# .envファイルを編集して必要な値を設定
```

3. **開発環境の起動**
```bash
# 開発用プロファイルで起動（メールサーバー含む）
docker-compose --profile dev up -d

# または通常起動
docker-compose up -d
```

4. **初期化**
```bash
# データベースのマイグレーション
docker-compose exec web flask db upgrade

# 管理者ユーザーの作成
docker-compose exec web flask create-admin
```

### 本番環境

1. **環境変数の設定**
```bash
cp env.production .env
# 本番用の安全な値を設定
```

2. **SSL証明書の準備**
```bash
# Let's Encryptを使用する場合
sudo certbot certonly --standalone -d lib-mng.xcap.co.jp

# 証明書をNginx用ディレクトリにコピー
sudo mkdir -p nginx/ssl
sudo cp /etc/letsencrypt/live/lib-mng.xcap.co.jp/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/lib-mng.xcap.co.jp/privkey.pem nginx/ssl/key.pem
sudo chown -R $USER:$USER nginx/ssl/
```

3. **本番環境の起動**
```bash
# 本番用設定で起動
docker-compose -f docker-compose.yml up -d
```

4. **初期化**
```bash
# データベースのマイグレーション
docker-compose exec web flask db upgrade

# 管理者ユーザーの作成
docker-compose exec web flask create-admin
```

## セキュリティ設定

### 環境変数の管理

**重要**: 本番環境では以下の項目を必ず変更してください：

1. **SECRET_KEY**: 強力なランダム文字列
```bash
# 強力なシークレットキーを生成
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

2. **データベースパスワード**: 強力なパスワード
3. **管理者パスワード**: 強力なパスワード
4. **API_KEY**: 強力なランダム文字列

### ファイアウォール設定

```bash
# UFWの設定例
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### SSL証明書の自動更新

```bash
# crontabに追加
0 12 * * * /usr/bin/certbot renew --quiet && docker-compose restart nginx
```

## 監視とログ

### ログの確認

```bash
# アプリケーションログ
docker-compose logs -f web

# Nginxログ
docker-compose logs -f nginx

# データベースログ
docker-compose logs -f db
```

### ヘルスチェック

```bash
# アプリケーションのヘルスチェック
curl -f http://localhost/health

# データベースのヘルスチェック
docker-compose exec db mysqladmin ping -h localhost
```

### 監視設定

Prometheus + Grafanaの設定例：

```yaml
# docker-compose.monitoring.yml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    networks:
      - library_network

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    networks:
      - library_network
```

## バックアップ

### 自動バックアップスクリプト

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup"
DB_CONTAINER="library_db"

# データベースバックアップ
docker-compose exec -T db mysqldump -u root -p${MYSQL_ROOT_PASSWORD} --all-databases > $BACKUP_DIR/db_backup_$DATE.sql

# アップロードファイルのバックアップ
tar -czf $BACKUP_DIR/uploads_backup_$DATE.tar.gz uploads/

# 古いバックアップの削除（30日以上）
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

### バックアップの復元

```bash
# データベースの復元
docker-compose exec -T db mysql -u root -p${MYSQL_ROOT_PASSWORD} < backup_file.sql

# アップロードファイルの復元
tar -xzf backup_file.tar.gz
```

## トラブルシューティング

### よくある問題

1. **ポートの競合**
```bash
# 使用中のポートを確認
sudo netstat -tulpn | grep :80
sudo netstat -tulpn | grep :443
```

2. **データベース接続エラー**
```bash
# データベースの状態確認
docker-compose exec db mysqladmin ping -h localhost

# ログの確認
docker-compose logs db
```

3. **SSL証明書の問題**
```bash
# 証明書の有効性確認
openssl x509 -in nginx/ssl/cert.pem -text -noout

# Nginx設定のテスト
docker-compose exec nginx nginx -t
```

### ログの場所

- アプリケーションログ: `logs/library.log`
- Nginxログ: コンテナ内 `/var/log/nginx/`
- MySQLログ: コンテナ内 `/var/log/mysql/`

### 緊急時の対応

1. **サービスの停止**
```bash
docker-compose down
```

2. **データの保護**
```bash
# ボリュームのバックアップ
docker run --rm -v library-db-data:/data -v $(pwd):/backup alpine tar czf /backup/emergency_backup.tar.gz -C /data .
```

3. **復旧手順**
```bash
# バックアップから復元
docker-compose down -v
docker volume create library-db-data
docker run --rm -v library-db-data:/data -v $(pwd):/backup alpine tar xzf /backup/emergency_backup.tar.gz -C /data
docker-compose up -d
```

## パフォーマンスチューニング

### データベース設定

```sql
-- MySQL設定の最適化
SET GLOBAL innodb_buffer_pool_size = 1073741824; -- 1GB
SET GLOBAL max_connections = 200;
```

### Nginx設定

```nginx
# 静的ファイルのキャッシュ
location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

## 更新手順

1. **コードの更新**
```bash
git pull origin main
```

2. **イメージの再ビルド**
```bash
docker-compose build --no-cache
```

3. **サービスの再起動**
```bash
docker-compose down
docker-compose up -d
```

4. **データベースマイグレーション**
```bash
docker-compose exec web flask db upgrade
```

## サポート

問題が発生した場合は、以下の情報を収集してください：

1. システム情報
2. ログファイル
3. 環境変数設定（機密情報は除く）
4. Docker Compose設定
5. エラーメッセージ

これらの情報を開発チームに提供してください。 