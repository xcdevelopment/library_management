# 図書館管理システム

セキュアで拡張性のある図書館管理システムです。Flask、MySQL、Nginxを使用した本格的なWebアプリケーションです。

## 🚀 特徴

- **セキュアな設計**: HTTPS対応、セキュリティヘッダー、CSRF保護
- **環境別設定**: 開発・テスト・本番環境の分離
- **コンテナ化**: Docker Composeによる簡単なデプロイ
- **監視・ログ**: 包括的なログ管理とヘルスチェック
- **バックアップ**: 自動バックアップと復元機能
- **セキュリティ監査**: 定期的なセキュリティチェック

## 📋 前提条件

- Docker 20.10+
- Docker Compose 2.0+
- Git
- 4GB以上のメモリ
- 20GB以上のストレージ

## 🛠️ クイックスタート

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd library_management
```

### 2. 環境変数の設定

```bash
# 開発環境
cp env.development .env

# または本番環境
cp env.production .env

# .envファイルを編集して必要な値を設定
nano .env
```

### 3. アプリケーションの起動

```bash
# 開発環境（メールサーバー含む）
docker-compose --profile dev up -d

# または通常起動
docker-compose up -d
```

### 4. 初期化

```bash
# データベースのマイグレーション
docker-compose exec web flask db upgrade

# 管理者ユーザーの作成
docker-compose exec web flask create-admin
```

### 5. アクセス

- **アプリケーション**: http://localhost (HTTP) / https://localhost (HTTPS)
- **メールサーバー（開発用）**: http://localhost:8025

## 🔧 環境別設定

### 開発環境

```bash
# 開発用設定で起動
cp env.development .env
docker-compose --profile dev up -d
```

### 本番環境

```bash
# 本番用設定で起動
cp env.production .env
# .envファイルを編集して本番用の値を設定
docker-compose up -d
```

## 🔒 セキュリティ機能

### 実装済みセキュリティ対策

- ✅ HTTPS/TLS暗号化
- ✅ セキュリティヘッダー（HSTS、CSP、X-Frame-Options等）
- ✅ CSRF保護
- ✅ セッション管理の強化
- ✅ 入力検証とサニタイゼーション
- ✅ SQLインジェクション対策
- ✅ XSS対策
- ✅ レート制限
- ✅ 環境変数による機密情報管理
- ✅ 非rootユーザーでのコンテナ実行
- ✅ ファイル権限の適切な設定

### セキュリティ監査

```bash
# セキュリティ監査の実行
./scripts/security_audit.sh
```

## 💾 バックアップ

### 自動バックアップ

```bash
# フルバックアップの実行
./scripts/backup.sh backup

# バックアップ一覧の表示
./scripts/backup.sh list

# バックアップの検証
./scripts/backup.sh verify <backup_file>

# バックアップからの復元
./scripts/backup.sh restore <backup_file>
```

### 定期バックアップの設定

```bash
# crontabに追加（毎日午前2時にバックアップ）
0 2 * * * /path/to/library_management/scripts/backup.sh backup
```

## 📊 監視とログ

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

## 🏗️ アーキテクチャ

```
[Internet] → [Nginx (SSL/TLS)] → [Flask App] → [MySQL Database]
                ↓
            [Static Files]
                ↓
            [Logs & Monitoring]
```

### コンポーネント

- **Nginx**: リバースプロキシ、SSL終端、静的ファイル配信
- **Flask**: Webアプリケーション
- **MySQL**: データベース
- **MailHog**: 開発用メールサーバー

## 📁 プロジェクト構造

```
library_management/
├── app.py                 # メインアプリケーション
├── config.py             # 設定ファイル
├── models.py             # データベースモデル
├── requirements.txt      # Python依存関係
├── docker-compose.yml    # Docker Compose設定
├── Dockerfile           # Flaskアプリケーション用Dockerfile
├── nginx/               # Nginx設定
│   ├── nginx.conf
│   └── Dockerfile
├── mysql/               # MySQL設定
│   └── conf.d/
├── scripts/             # ユーティリティスクリプト
│   ├── backup.sh
│   └── security_audit.sh
├── docs/                # ドキュメント
│   ├── DEPLOYMENT.md
│   └── SECURITY.md
├── env.example          # 環境変数テンプレート
├── env.development      # 開発環境設定
├── env.production       # 本番環境設定
├── .gitignore          # Git除外設定
└── .dockerignore       # Docker除外設定
```

## 🔧 設定

### 環境変数

主要な環境変数：

- `SECRET_KEY`: アプリケーションのシークレットキー
- `DATABASE_URL`: データベース接続URL
- `MYSQL_ROOT_PASSWORD`: MySQL rootパスワード
- `MAIL_SERVER`: メールサーバー設定
- `SLACK_BOT_TOKEN`: Slack連携トークン

詳細は `env.example` を参照してください。

### SSL証明書

本番環境では、Let's Encryptを使用したSSL証明書の設定を推奨します：

```bash
# Let's Encrypt証明書の取得
sudo certbot certonly --standalone -d lib-mng.xcap.co.jp

# 証明書をNginx用ディレクトリにコピー
sudo mkdir -p nginx/ssl
sudo cp /etc/letsencrypt/live/lib-mng.xcap.co.jp/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/lib-mng.xcap.co.jp/privkey.pem nginx/ssl/key.pem
sudo chown -R $USER:$USER nginx/ssl/
```

## 🚀 デプロイ

### 本番環境へのデプロイ

1. **サーバーの準備**
   ```bash
   # ファイアウォールの設定
   sudo ufw allow 22/tcp    # SSH
   sudo ufw allow 80/tcp    # HTTP
   sudo ufw allow 443/tcp   # HTTPS
   sudo ufw enable
   ```

2. **アプリケーションのデプロイ**
   ```bash
   # コードの取得
   git clone <repository-url>
   cd library_management
   
   # 環境変数の設定
   cp env.production .env
   # .envファイルを編集
   
   # SSL証明書の設定
   # （上記のSSL証明書セクションを参照）
   
   # アプリケーションの起動
   docker-compose up -d
   ```

3. **初期化**
   ```bash
   docker-compose exec web flask db upgrade
   docker-compose exec web flask create-admin
   ```

詳細なデプロイ手順は `docs/DEPLOYMENT.md` を参照してください。

## 🔍 トラブルシューティング

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
   ```

3. **SSL証明書の問題**
   ```bash
   # 証明書の有効性確認
   openssl x509 -in nginx/ssl/cert.pem -text -noout
   ```

### ログの確認

```bash
# 全サービスのログ
docker-compose logs

# 特定サービスのログ
docker-compose logs web
docker-compose logs nginx
docker-compose logs db
```

## 📚 ドキュメント

- [デプロイメントガイド](docs/DEPLOYMENT.md)
- [セキュリティ設定ガイド](docs/SECURITY.md)
- [ユーザーマニュアル](USER_MANUAL.md)
- [開発ノート](DEVELOPMENT_NOTES.md)

## 🤝 貢献

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🆘 サポート

問題が発生した場合は、以下の情報を収集してください：

1. システム情報
2. ログファイル
3. 環境変数設定（機密情報は除く）
4. Docker Compose設定
5. エラーメッセージ

これらの情報を開発チームに提供してください。

## 🔄 更新

### アプリケーションの更新

```bash
# コードの更新
git pull origin main

# イメージの再ビルド
docker-compose build --no-cache

# サービスの再起動
docker-compose down
docker-compose up -d

# データベースマイグレーション
docker-compose exec web flask db upgrade
```

### セキュリティパッチの適用

```bash
# セキュリティ監査の実行
./scripts/security_audit.sh

# 依存関係の更新
docker-compose exec web pip install --upgrade -r requirements.txt
```

---

**注意**: 本番環境では、必ず強力なパスワードとシークレットキーを設定し、定期的なセキュリティ監査を実行してください。 