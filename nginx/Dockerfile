FROM nginx:alpine

# セキュリティアップデート
RUN apk update && apk upgrade

# opensslをインストール
RUN apk add --no-cache openssl

# 不要なファイルを削除
RUN rm -rf /var/cache/apk/*

# Nginx設定ファイルをコピー
COPY nginx.conf /etc/nginx/nginx.conf

# SSL証明書ディレクトリを作成
RUN mkdir -p /etc/nginx/ssl

# 自己署名証明書を生成（開発用）
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/key.pem \
    -out /etc/nginx/ssl/cert.pem \
    -subj "/C=JP/ST=Tokyo/L=Tokyo/O=XCAP/CN=lib-mng.xcap.co.jp"

# 静的ファイル用ディレクトリを作成
RUN mkdir -p /app/static

# 非rootユーザーで実行
RUN chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

# ポート80と443を公開
EXPOSE 80 443

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Nginxを起動
CMD ["nginx", "-g", "daemon off;"] 