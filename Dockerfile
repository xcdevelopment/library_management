# ベースイメージ（Python公式）
FROM python:3.11-slim

# 作業ディレクトリを作成・設定
WORKDIR /app

# 依存パッケージとアプリコードをコピー
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

#アプリ全体をコピー
COPY . .  

# Flask用環境変数（開発用）
ENV FLASK_APP=app.py
ENV FLASK_ENV=development

# ポート5000を開放（Flaskはデフォルトで5000番）
EXPOSE 5000

# Flaskアプリを起動
CMD ["flask", "run", "--host=0.0.0.0"]

# entrypoint.sh をコンテナにコピー
COPY entrypoint.sh /app/entrypoint.sh

# コピーしたスクリプトに実行権限を付与
RUN chmod +x /app/entrypoint.sh

# ... (残りのDockerfileのステップ) ...

# ENTRYPOINT を設定 (docker-compose.yml で上書きすることも可能)
# ENTRYPOINT ["/app/entrypoint.sh"]
# CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"] # あなたのアプリの起動コマンド
