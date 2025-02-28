import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(app):
    """アプリケーションのロガーをセットアップする"""
    # ログディレクトリの確保
    log_dir = os.path.join(app.root_path, 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # ログハンドラーの設定
    log_file = os.path.join(log_dir, 'library.log')
    handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=5)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    handler.setLevel(logging.INFO)
    
    # アプリケーションロガーの設定
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('図書管理アプリ 起動')
    
    return app.logger

def log_operation(logger, user, action, target, details):
    """操作ログを記録する"""
    logger.info(f'USER: {user} - ACTION: {action} - TARGET: {target} - DETAILS: {details}')