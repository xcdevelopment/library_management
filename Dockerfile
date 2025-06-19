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
