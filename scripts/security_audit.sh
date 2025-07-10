#!/bin/bash

# 図書館管理システム - セキュリティ監査スクリプト
# 使用方法: ./scripts/security_audit.sh

set -e

# 設定
AUDIT_LOG="logs/security_audit.log"
DATE=$(date +%Y-%m-%d_%H:%M:%S)

# 色付きログ出力
log_info() {
    echo -e "\033[32m[INFO]\033[0m $1"
    echo "[$DATE] [INFO] $1" >> "$AUDIT_LOG"
}

log_warn() {
    echo -e "\033[33m[WARN]\033[0m $1"
    echo "[$DATE] [WARN] $1" >> "$AUDIT_LOG"
}

log_error() {
    echo -e "\033[31m[ERROR]\033[0m $1"
    echo "[$DATE] [ERROR] $1" >> "$AUDIT_LOG"
}

log_pass() {
    echo -e "\033[32m[PASS]\033[0m $1"
    echo "[$DATE] [PASS] $1" >> "$AUDIT_LOG"
}

log_fail() {
    echo -e "\033[31m[FAIL]\033[0m $1"
    echo "[$DATE] [FAIL] $1" >> "$AUDIT_LOG"
}

# ログディレクトリの作成
mkdir -p logs

# 監査結果の初期化
PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

# 結果の記録
record_result() {
    local result="$1"
    case "$result" in
        "PASS")
            PASS_COUNT=$((PASS_COUNT + 1))
            ;;
        "FAIL")
            FAIL_COUNT=$((FAIL_COUNT + 1))
            ;;
        "WARN")
            WARN_COUNT=$((WARN_COUNT + 1))
            ;;
    esac
}

# 1. 環境変数のセキュリティチェック
check_environment_variables() {
    log_info "=== 環境変数のセキュリティチェック ==="
    
    # .envファイルの存在確認
    if [ -f .env ]; then
        log_pass ".env file exists"
        record_result "PASS"
        
        # 機密情報のチェック
        if grep -q "password" .env; then
            log_warn "Password found in .env file - ensure it's not committed to version control"
            record_result "WARN"
        else
            log_pass "No obvious passwords found in .env file"
            record_result "PASS"
        fi
        
        # デフォルト値のチェック
        if grep -q "dev-secret-key" .env; then
            log_fail "Default secret key found in .env file"
            record_result "FAIL"
        else
            log_pass "No default secret key found"
            record_result "PASS"
        fi
    else
        log_fail ".env file not found"
        record_result "FAIL"
    fi
    
    # 環境変数テンプレートの確認
    if [ -f env.example ]; then
        log_pass "env.example template exists"
        record_result "PASS"
    else
        log_fail "env.example template not found"
        record_result "FAIL"
    fi
}

# 2. ファイル権限のチェック
check_file_permissions() {
    log_info "=== ファイル権限のチェック ==="
    
    # 重要なファイルの権限チェック
    local critical_files=(
        ".env"
        "config.py"
        "docker-compose.yml"
        "nginx/ssl/"
    )
    
    for file in "${critical_files[@]}"; do
        if [ -e "$file" ]; then
            local perms=$(stat -c "%a" "$file" 2>/dev/null || stat -f "%Lp" "$file" 2>/dev/null)
            if [ "$perms" = "600" ] || [ "$perms" = "640" ]; then
                log_pass "Proper permissions on $file ($perms)"
                record_result "PASS"
            else
                log_warn "Insecure permissions on $file ($perms) - should be 600 or 640"
                record_result "WARN"
            fi
        fi
    done
    
    # スクリプトファイルの実行権限
    if [ -x scripts/backup.sh ]; then
        log_pass "Backup script is executable"
        record_result "PASS"
    else
        log_fail "Backup script is not executable"
        record_result "FAIL"
    fi
}

# 3. Docker設定のセキュリティチェック
check_docker_security() {
    log_info "=== Docker設定のセキュリティチェック ==="
    
    # Dockerfileのセキュリティチェック
    if [ -f Dockerfile ]; then
        # 非rootユーザーの確認
        if grep -q "USER appuser" Dockerfile; then
            log_pass "Dockerfile uses non-root user"
            record_result "PASS"
        else
            log_fail "Dockerfile does not use non-root user"
            record_result "FAIL"
        fi
        
        # セキュリティアップデートの確認
        if grep -q "apt-get upgrade" Dockerfile; then
            log_pass "Dockerfile includes security updates"
            record_result "PASS"
        else
            log_warn "Dockerfile may not include security updates"
            record_result "WARN"
        fi
        
        # 不要なファイルの削除確認
        if grep -q "rm -rf" Dockerfile; then
            log_pass "Dockerfile removes unnecessary files"
            record_result "PASS"
        else
            log_warn "Dockerfile may not remove unnecessary files"
            record_result "WARN"
        fi
    fi
    
    # docker-compose.ymlのセキュリティチェック
    if [ -f docker-compose.yml ]; then
        # 環境変数の使用確認
        if grep -q "\${MYSQL_ROOT_PASSWORD}" docker-compose.yml; then
            log_pass "docker-compose.yml uses environment variables for passwords"
            record_result "PASS"
        else
            log_fail "docker-compose.yml contains hardcoded passwords"
            record_result "FAIL"
        fi
        
        # ヘルスチェックの確認
        if grep -q "healthcheck" docker-compose.yml; then
            log_pass "docker-compose.yml includes health checks"
            record_result "PASS"
        else
            log_warn "docker-compose.yml does not include health checks"
            record_result "WARN"
        fi
    fi
}

# 4. データベースセキュリティチェック
check_database_security() {
    log_info "=== データベースセキュリティチェック ==="
    
    # MySQL設定ファイルの確認
    if [ -f mysql/conf.d/mysql.cnf ]; then
        log_pass "MySQL configuration file exists"
        record_result "PASS"
        
        # セキュリティ設定の確認
        if grep -q "local_infile=0" mysql/conf.d/mysql.cnf; then
            log_pass "MySQL local_infile is disabled"
            record_result "PASS"
        else
            log_warn "MySQL local_infile may be enabled"
            record_result "WARN"
        fi
        
        if grep -q "skip_symbolic_links=1" mysql/conf.d/mysql.cnf; then
            log_pass "MySQL symbolic links are disabled"
            record_result "PASS"
        else
            log_warn "MySQL symbolic links may be enabled"
            record_result "WARN"
        fi
    else
        log_fail "MySQL configuration file not found"
        record_result "FAIL"
    fi
}

# 5. Nginx設定のセキュリティチェック
check_nginx_security() {
    log_info "=== Nginx設定のセキュリティチェック ==="
    
    if [ -f nginx/nginx.conf ]; then
        log_pass "Nginx configuration file exists"
        record_result "PASS"
        
        # SSL設定の確認
        if grep -q "ssl_protocols" nginx/nginx.conf; then
            log_pass "Nginx SSL protocols are configured"
            record_result "PASS"
        else
            log_warn "Nginx SSL protocols may not be configured"
            record_result "WARN"
        fi
        
        # セキュリティヘッダーの確認
        if grep -q "X-Frame-Options" nginx/nginx.conf; then
            log_pass "Nginx security headers are configured"
            record_result "PASS"
        else
            log_warn "Nginx security headers may not be configured"
            record_result "WARN"
        fi
        
        # レート制限の確認
        if grep -q "limit_req" nginx/nginx.conf; then
            log_pass "Nginx rate limiting is configured"
            record_result "PASS"
        else
            log_warn "Nginx rate limiting may not be configured"
            record_result "WARN"
        fi
    else
        log_fail "Nginx configuration file not found"
        record_result "FAIL"
    fi
}

# 6. アプリケーションコードのセキュリティチェック
check_application_security() {
    log_info "=== アプリケーションコードのセキュリティチェック ==="
    
    # config.pyのセキュリティチェック
    if [ -f config.py ]; then
        log_pass "config.py exists"
        record_result "PASS"
        
        # 環境変数検証の確認
        if grep -q "validate_required_env_vars" config.py; then
            log_pass "Environment variable validation is implemented"
            record_result "PASS"
        else
            log_warn "Environment variable validation may not be implemented"
            record_result "WARN"
        fi
        
        # シークレットキー強度の確認
        if grep -q "validate_secret_key_strength" config.py; then
            log_pass "Secret key strength validation is implemented"
            record_result "PASS"
        else
            log_warn "Secret key strength validation may not be implemented"
            record_result "WARN"
        fi
        
        # CSRF保護の確認
        if grep -q "WTF_CSRF_ENABLED" config.py; then
            log_pass "CSRF protection is configured"
            record_result "PASS"
        else
            log_warn "CSRF protection may not be configured"
            record_result "WARN"
        fi
    fi
    
    # ログ設定の確認
    if [ -d logs ]; then
        log_pass "Logs directory exists"
        record_result "PASS"
        
        # ログファイルの権限確認
        if [ -f logs/library.log ]; then
            local log_perms=$(stat -c "%a" logs/library.log 2>/dev/null || stat -f "%Lp" logs/library.log 2>/dev/null)
            if [ "$log_perms" = "600" ] || [ "$log_perms" = "640" ]; then
                log_pass "Log file has proper permissions ($log_perms)"
                record_result "PASS"
            else
                log_warn "Log file may have insecure permissions ($log_perms)"
                record_result "WARN"
            fi
        fi
    else
        log_warn "Logs directory not found"
        record_result "WARN"
    fi
}

# 7. 依存関係の脆弱性チェック
check_dependencies() {
    log_info "=== 依存関係の脆弱性チェック ==="
    
    if [ -f requirements.txt ]; then
        log_pass "requirements.txt exists"
        record_result "PASS"
        
        # pip-auditの実行（利用可能な場合）
        if command -v pip-audit &> /dev/null; then
            log_info "Running pip-audit..."
            if pip-audit -r requirements.txt 2>/dev/null; then
                log_pass "No known vulnerabilities found in Python dependencies"
                record_result "PASS"
            else
                log_warn "Vulnerabilities may exist in Python dependencies"
                record_result "WARN"
            fi
        else
            log_warn "pip-audit not available - install with: pip install pip-audit"
            record_result "WARN"
        fi
    else
        log_fail "requirements.txt not found"
        record_result "FAIL"
    fi
}

# 8. バックアップ設定のチェック
check_backup_configuration() {
    log_info "=== バックアップ設定のチェック ==="
    
    if [ -f scripts/backup.sh ]; then
        log_pass "Backup script exists"
        record_result "PASS"
        
        # バックアップスクリプトの権限確認
        if [ -x scripts/backup.sh ]; then
            log_pass "Backup script is executable"
            record_result "PASS"
        else
            log_fail "Backup script is not executable"
            record_result "FAIL"
        fi
        
        # バックアップディレクトリの確認
        if [ -d "/backup" ] || [ -d "backup" ]; then
            log_pass "Backup directory exists"
            record_result "PASS"
        else
            log_warn "Backup directory not found"
            record_result "WARN"
        fi
    else
        log_fail "Backup script not found"
        record_result "FAIL"
    fi
}

# 9. ネットワークセキュリティチェック
check_network_security() {
    log_info "=== ネットワークセキュリティチェック ==="
    
    # ポートの確認
    if docker-compose ps 2>/dev/null | grep -q "Up"; then
        log_info "Checking exposed ports..."
        
        # データベースポートの確認
        if docker-compose ps 2>/dev/null | grep -q ":3306"; then
            log_warn "Database port 3306 is exposed - should be internal only"
            record_result "WARN"
        else
            log_pass "Database port is not exposed externally"
            record_result "PASS"
        fi
        
        # HTTPSポートの確認
        if docker-compose ps 2>/dev/null | grep -q ":443"; then
            log_pass "HTTPS port 443 is exposed"
            record_result "PASS"
        else
            log_warn "HTTPS port 443 is not exposed"
            record_result "WARN"
        fi
    else
        log_warn "Docker containers not running - cannot check ports"
        record_result "WARN"
    fi
}

# 10. ファイル監視
check_file_integrity() {
    log_info "=== ファイル整合性チェック ==="
    
    # 重要なファイルの存在確認
    local critical_files=(
        "app.py"
        "config.py"
        "models.py"
        "requirements.txt"
        "docker-compose.yml"
        "Dockerfile"
        "nginx/nginx.conf"
        "mysql/conf.d/mysql.cnf"
    )
    
    for file in "${critical_files[@]}"; do
        if [ -f "$file" ]; then
            log_pass "Critical file exists: $file"
            record_result "PASS"
        else
            log_fail "Critical file missing: $file"
            record_result "FAIL"
        fi
    done
    
    # .gitignoreの確認
    if [ -f .gitignore ]; then
        log_pass ".gitignore exists"
        record_result "PASS"
        
        # 機密ファイルの除外確認
        if grep -q "\.env" .gitignore; then
            log_pass ".env is excluded from version control"
            record_result "PASS"
        else
            log_fail ".env is not excluded from version control"
            record_result "FAIL"
        fi
        
        if grep -q "logs/" .gitignore; then
            log_pass "logs directory is excluded from version control"
            record_result "PASS"
        else
            log_warn "logs directory may not be excluded from version control"
            record_result "WARN"
        fi
    else
        log_fail ".gitignore not found"
        record_result "FAIL"
    fi
}

# 結果の表示
show_summary() {
    log_info "=== セキュリティ監査結果サマリー ==="
    echo
    echo "総チェック数: $((PASS_COUNT + FAIL_COUNT + WARN_COUNT))"
    echo "✅ パス: $PASS_COUNT"
    echo "❌ 失敗: $FAIL_COUNT"
    echo "⚠️  警告: $WARN_COUNT"
    echo
    
    if [ $FAIL_COUNT -eq 0 ]; then
        log_pass "セキュリティ監査完了 - 重大な問題は見つかりませんでした"
    else
        log_error "セキュリティ監査完了 - $FAIL_COUNT 個の重大な問題が見つかりました"
    fi
    
    if [ $WARN_COUNT -gt 0 ]; then
        log_warn "$WARN_COUNT 個の警告があります - 改善を検討してください"
    fi
    
    echo
    echo "詳細なログは $AUDIT_LOG に保存されました"
}

# メイン処理
main() {
    log_info "セキュリティ監査を開始します..."
    echo "監査ログ: $AUDIT_LOG"
    echo
    
    # 各チェックの実行
    check_environment_variables
    echo
    
    check_file_permissions
    echo
    
    check_docker_security
    echo
    
    check_database_security
    echo
    
    check_nginx_security
    echo
    
    check_application_security
    echo
    
    check_dependencies
    echo
    
    check_backup_configuration
    echo
    
    check_network_security
    echo
    
    check_file_integrity
    echo
    
    # 結果の表示
    show_summary
}

# スクリプトの実行
main "$@" 