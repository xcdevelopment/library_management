# 開発メモ

このプロジェクトは、開発環境の構築と管理に **Docker Compose** を使用します。
MySQLデータベースを含め、必要なサービスはすべてコンテナ内で実行されます。

## 1. 開発環境のセットアップ

新しい環境でこのプロジェクトを開始するための手順です。

### 前提条件
- Docker Desktop がインストールされ、正常に起動していること。

### 起動手順

1. **プロジェクトディレクトリへの移動**
   `docker-compose` コマンドは、必ず `docker-compose.yml` があるプロジェクトのルートディレクトリで実行する必要があります。
   ```powershell
   cd path/to/library_management
   ```
   これを忘れると `no configuration file provided: not found` というエラーが出ます。

2. **コンテナのビルドと起動**
   以下のコマンドを一度だけ実行すれば、アプリケーションコンテナとデータベースコンテナがバックグラウンドで起動します。
   ```powershell
   docker-compose up --build -d
   ```
   - `--build`: `Dockerfile` に変更があった場合にイメージを再ビルドします。初回は必須です。
   - `-d`: コンテナをバックグラウンドで起動します (detached mode)。

3. **アプリケーションへのアクセス**
   ブラウザで `http://localhost:8080` を開きます。

4. **データベースのマイグレーション**
   初回起動時や、`models.py` を変更した後は、データベースのテーブル構造を更新する必要があります。
   詳細は「3. データベースのマイグレーション」セクションを参照してください。

## 2. 日常的な開発ワークフロー

### コンテナの停止
開発を終了する際は、以下のコマンドでコンテナを停止・削除できます。
```powershell
docker-compose down
```
※データベースのデータは `db-data` ボリュームに残るので、このコマンドで消えることはありません。

### コンテナ内でのコマンド実行
`flask` コマンドなど、コンテナ内で何らかのコマンドを実行したい場合は `docker-compose exec` を使います。
**非常に重要な注意点として、必ずサービス名 (`web`) を指定してください。** コンテナ名 (`library_web`) ではありません。
```powershell
# 正しい例
docker-compose exec web <実行したいコマンド>

# 間違った例 (service not running エラーになる)
docker-compose exec library_web <実行したいコマンド>
```

### スクリプト実行時の注意 (`ModuleNotFoundError`)
`data_migration` のように、`app` をインポートする自作スクリプトをコンテナ内で実行すると `ModuleNotFoundError: No module named 'app'` エラーが出ることがあります。
その場合は、`PYTHONPATH` を明示的に指定して実行してください。
```powershell
docker-compose exec -e PYTHONPATH=/app web python your_script_name.py
```

## 3. データベースのマイグレーション

`models.py` に変更（テーブルやカラムの追加・削除など）を加えた場合、その変更をデータベースに反映させるためにマイグレーション作業が必要です。

1. **マイグレーション環境の初期化 (初回のみ)**
   `migrations` フォルダがない場合、最初に一度だけ実行します。
   ```powershell
   docker-compose exec web flask db init
   ```

2. **マイグレーションスクリプトの自動生成**
   モデルの変更点を検知し、変更用スクリプトを生成します。
   ```powershell
   docker-compose exec web flask db migrate -m "変更内容のコメント"
   ```

3. **データベースへの適用**
   生成されたスクリプトを実行し、実際のデータベースにテーブル変更を適用します。
   ```powershell
   docker-compose exec web flask db upgrade
   ```

## 4. トラブルシューティング

### `http://` が `https://` に勝手にリダイレクトされる
開発環境でHTTPSへの強制リダイレクトが発生する場合、以下の2点を確認してください。
1. **`Flask-Talisman` の設定:** `app.py` 内の `Talisman` 初期化部分で、`force_https=is_production` のように本番環境でのみ有効になっているか。
2. **`@app.before_request`:** `app.py` 内に自作のリダイレクト処理がないか。ここでも `is_production` などの本番フラグで処理を分岐させる必要があります。
   * **原因**: ブラウザのキャッシュ(HSTS)が原因の場合もあります。まずはシークレットモードで試すのが有効です。

### Dockerコマンドがエラーになる
`service "..." is not running` や `error during connect` のようなエラーが出てDockerの動作が不安定な場合：
1. **Docker Desktopを再起動する** のが最も効果的です。
2. `docker-compose ps` を実行して、コンテナの状態 (`STATUS` 列が `Up` になっているか) を確認します。

## 5. その他

### `admin` ユーザーの初期パスワード
`admin`ユーザーは、`app.py` 内の `init-db` コマンドで作成されます。
- **ユーザー名:** `admin`
- **初期パスワード:** `change_me_immediately`
このパスワードは、`os.environ.get('ADMIN_PASSWORD', '...')` の部分で定義されています。
