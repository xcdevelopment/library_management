# ベースイメージ（Python公式）
FROM python:3.11-slim

# メタデータ
LABEL maintainer="Library Management System"
LABEL version="1.0"
LABEL description="Library Management System with enhanced security"

# セキュリティアップデート
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 非rootユーザーを作成
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 作業ディレクトリを作成・設定
WORKDIR /app

# 依存パッケージをコピーしてインストール
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# アプリ全体をコピー
COPY . .

# entrypoint.shの改行コードをLFに変換
RUN sed -i 's/\r$//' /app/entrypoint.sh

# entrypoint.shに実行権限を付与
RUN chmod +x /app/entrypoint.sh

# 必要なディレクトリを作成
RUN mkdir -p /app/logs /app/uploads /app/temp && \
    chown -R appuser:appuser /app

# セキュリティ設定
RUN chmod 755 /app && \
    chmod 644 /app/*.py && \
    chmod 644 /app/requirements.txt && \
    chmod 755 /app/entrypoint.sh

# Flask用環境変数
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# ポート5000を開放
EXPOSE 5000

# 非rootユーザーに切り替え
USER appuser

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# アプリケーションを起動
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
