#!/bin/sh
# データベースが起動するまで待機
echo "Waiting for database..."
# 'db' は docker-compose.yml で定義されたMySQLサービスのホスト名
# '3306' はMySQLの標準ポート
while ! nc -z db 3306; do
  sleep 0.1
done
echo "Database started"

# データベースマイグレーションを実行
# アプリケーションによっては 'flask db upgrade' の前に 'flask db init' や 'flask db migrate' が必要かもしれません
echo "Running database migrations..."
flask db upgrade

# 初期管理者ユーザーを作成（必要に応じて）
echo "Creating initial admin user if not exists..."
flask init-db

# アプリケーションを起動
exec "$@"