#!/bin/sh

# データベースのマイグレーションを実行
echo "Running database migrations..."
flask db upgrade

# 元のCMDを実行
exec "$@" 