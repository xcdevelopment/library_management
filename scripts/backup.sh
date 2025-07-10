#!/bin/bash

# 図書館管理システム - 自動バックアップスクリプト
# 使用方法: ./scripts/backup.sh [backup|restore] [filename]

set -e

# 設定
BACKUP_DIR="/backup"
DATE=$(date +%Y%m%d_%H%M%S)
DB_CONTAINER="library_db"
WEB_CONTAINER="library_web"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}

# 色付きログ出力
log_info() {
    echo -e "\033[32m[INFO]\033[0m $1"
}

log_warn() {
    echo -e "\033[33m[WARN]\033[0m $1"
}

log_error() {
    echo -e "\033[31m[ERROR]\033[0m $1"
}

# 環境変数の読み込み
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    log_error ".env file not found"
    exit 1
fi

# バックアップディレクトリの作成
create_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        log_info "Creating backup directory: $BACKUP_DIR"
        mkdir -p "$BACKUP_DIR"
    fi
}

# データベースバックアップ
backup_database() {
    local backup_file="$BACKUP_DIR/db_backup_$DATE.sql"
    
    log_info "Starting database backup..."
    
    if docker-compose exec -T "$DB_CONTAINER" mysqldump \
        -u root -p"${MYSQL_ROOT_PASSWORD}" \
        --single-transaction \
        --routines \
        --triggers \
        --all-databases > "$backup_file"; then
        log_info "Database backup completed: $backup_file"
        
        # バックアップファイルの圧縮
        gzip "$backup_file"
        log_info "Database backup compressed: ${backup_file}.gz"
        
        # バックアップサイズの表示
        local size=$(du -h "${backup_file}.gz" | cut -f1)
        log_info "Backup size: $size"
    else
        log_error "Database backup failed"
        exit 1
    fi
}

# アップロードファイルのバックアップ
backup_uploads() {
    local backup_file="$BACKUP_DIR/uploads_backup_$DATE.tar.gz"
    
    log_info "Starting uploads backup..."
    
    if [ -d "uploads" ]; then
        if tar -czf "$backup_file" uploads/; then
            log_info "Uploads backup completed: $backup_file"
            
            # バックアップサイズの表示
            local size=$(du -h "$backup_file" | cut -f1)
            log_info "Backup size: $size"
        else
            log_error "Uploads backup failed"
            exit 1
        fi
    else
        log_warn "Uploads directory not found, skipping uploads backup"
    fi
}

# 設定ファイルのバックアップ
backup_config() {
    local backup_file="$BACKUP_DIR/config_backup_$DATE.tar.gz"
    
    log_info "Starting configuration backup..."
    
    # 重要な設定ファイルのみをバックアップ
    if tar -czf "$backup_file" \
        config.py \
        requirements.txt \
        docker-compose.yml \
        nginx/ \
        mysql/ \
        env.example \
        env.development \
        env.production; then
        log_info "Configuration backup completed: $backup_file"
        
        # バックアップサイズの表示
        local size=$(du -h "$backup_file" | cut -f1)
        log_info "Backup size: $size"
    else
        log_error "Configuration backup failed"
        exit 1
    fi
}

# ログファイルのバックアップ
backup_logs() {
    local backup_file="$BACKUP_DIR/logs_backup_$DATE.tar.gz"
    
    log_info "Starting logs backup..."
    
    if [ -d "logs" ]; then
        if tar -czf "$backup_file" logs/; then
            log_info "Logs backup completed: $backup_file"
            
            # バックアップサイズの表示
            local size=$(du -h "$backup_file" | cut -f1)
            log_info "Backup size: $size"
        else
            log_error "Logs backup failed"
            exit 1
        fi
    else
        log_warn "Logs directory not found, skipping logs backup"
    fi
}

# 古いバックアップの削除
cleanup_old_backups() {
    log_info "Cleaning up backups older than $RETENTION_DAYS days..."
    
    local deleted_count=0
    
    # データベースバックアップの削除
    if find "$BACKUP_DIR" -name "db_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete; then
        deleted_count=$((deleted_count + $(find "$BACKUP_DIR" -name "db_backup_*.sql.gz" -mtime +$RETENTION_DAYS | wc -l)))
    fi
    
    # アップロードバックアップの削除
    if find "$BACKUP_DIR" -name "uploads_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete; then
        deleted_count=$((deleted_count + $(find "$BACKUP_DIR" -name "uploads_backup_*.tar.gz" -mtime +$RETENTION_DAYS | wc -l)))
    fi
    
    # 設定バックアップの削除
    if find "$BACKUP_DIR" -name "config_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete; then
        deleted_count=$((deleted_count + $(find "$BACKUP_DIR" -name "config_backup_*.tar.gz" -mtime +$RETENTION_DAYS | wc -l)))
    fi
    
    # ログバックアップの削除
    if find "$BACKUP_DIR" -name "logs_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete; then
        deleted_count=$((deleted_count + $(find "$BACKUP_DIR" -name "logs_backup_*.tar.gz" -mtime +$RETENTION_DAYS | wc -l)))
    fi
    
    if [ $deleted_count -gt 0 ]; then
        log_info "Deleted $deleted_count old backup files"
    else
        log_info "No old backup files to delete"
    fi
}

# バックアップの検証
verify_backup() {
    local backup_file="$1"
    
    log_info "Verifying backup: $backup_file"
    
    if [[ "$backup_file" == *.sql.gz ]]; then
        # データベースバックアップの検証
        if gunzip -t "$backup_file"; then
            log_info "Database backup verification successful"
        else
            log_error "Database backup verification failed"
            return 1
        fi
    elif [[ "$backup_file" == *.tar.gz ]]; then
        # アーカイブバックアップの検証
        if tar -tzf "$backup_file" > /dev/null; then
            log_info "Archive backup verification successful"
        else
            log_error "Archive backup verification failed"
            return 1
        fi
    fi
}

# データベースの復元
restore_database() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi
    
    log_warn "This will overwrite the current database. Are you sure? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_info "Database restore cancelled"
        exit 0
    fi
    
    log_info "Starting database restore from: $backup_file"
    
    # データベースの停止
    log_info "Stopping web application..."
    docker-compose stop web
    
    # バックアップの復元
    if [[ "$backup_file" == *.gz ]]; then
        gunzip -c "$backup_file" | docker-compose exec -T "$DB_CONTAINER" mysql -u root -p"${MYSQL_ROOT_PASSWORD}"
    else
        docker-compose exec -T "$DB_CONTAINER" mysql -u root -p"${MYSQL_ROOT_PASSWORD}" < "$backup_file"
    fi
    
    # Webアプリケーションの再起動
    log_info "Restarting web application..."
    docker-compose start web
    
    log_info "Database restore completed"
}

# アップロードファイルの復元
restore_uploads() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi
    
    log_warn "This will overwrite the current uploads directory. Are you sure? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_info "Uploads restore cancelled"
        exit 0
    fi
    
    log_info "Starting uploads restore from: $backup_file"
    
    # 現在のアップロードディレクトリのバックアップ
    if [ -d "uploads" ]; then
        mv uploads uploads.backup.$(date +%Y%m%d_%H%M%S)
    fi
    
    # バックアップの復元
    tar -xzf "$backup_file"
    
    log_info "Uploads restore completed"
}

# バックアップ一覧の表示
list_backups() {
    log_info "Available backups:"
    echo
    
    echo "Database backups:"
    ls -lh "$BACKUP_DIR"/db_backup_*.sql.gz 2>/dev/null || echo "No database backups found"
    echo
    
    echo "Uploads backups:"
    ls -lh "$BACKUP_DIR"/uploads_backup_*.tar.gz 2>/dev/null || echo "No uploads backups found"
    echo
    
    echo "Configuration backups:"
    ls -lh "$BACKUP_DIR"/config_backup_*.tar.gz 2>/dev/null || echo "No configuration backups found"
    echo
    
    echo "Logs backups:"
    ls -lh "$BACKUP_DIR"/logs_backup_*.tar.gz 2>/dev/null || echo "No logs backups found"
    echo
}

# メイン処理
main() {
    local action="$1"
    local filename="$2"
    
    case "$action" in
        "backup")
            log_info "Starting backup process..."
            create_backup_dir
            backup_database
            backup_uploads
            backup_config
            backup_logs
            cleanup_old_backups
            
            # 最新のバックアップの検証
            latest_db_backup=$(ls -t "$BACKUP_DIR"/db_backup_*.sql.gz 2>/dev/null | head -1)
            if [ -n "$latest_db_backup" ]; then
                verify_backup "$latest_db_backup"
            fi
            
            log_info "Backup process completed successfully"
            ;;
        "restore")
            if [ -z "$filename" ]; then
                log_error "Please specify backup file for restore"
                echo "Usage: $0 restore <backup_file>"
                exit 1
            fi
            
            if [[ "$filename" == *db_backup* ]]; then
                restore_database "$filename"
            elif [[ "$filename" == *uploads_backup* ]]; then
                restore_uploads "$filename"
            else
                log_error "Unknown backup type. Please specify a valid backup file."
                exit 1
            fi
            ;;
        "list")
            list_backups
            ;;
        "verify")
            if [ -z "$filename" ]; then
                log_error "Please specify backup file for verification"
                echo "Usage: $0 verify <backup_file>"
                exit 1
            fi
            verify_backup "$filename"
            ;;
        *)
            echo "Usage: $0 {backup|restore|list|verify} [filename]"
            echo
            echo "Commands:"
            echo "  backup              - Create a full backup"
            echo "  restore <file>      - Restore from backup file"
            echo "  list                - List available backups"
            echo "  verify <file>       - Verify backup file integrity"
            echo
            echo "Examples:"
            echo "  $0 backup"
            echo "  $0 restore /backup/db_backup_20231201_120000.sql.gz"
            echo "  $0 list"
            echo "  $0 verify /backup/db_backup_20231201_120000.sql.gz"
            exit 1
            ;;
    esac
}

# スクリプトの実行
main "$@" 