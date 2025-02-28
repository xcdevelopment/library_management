#!/usr/bin/env python
"""
返却期限通知などの定期実行タスク

crontabなどで定期実行するためのスクリプト
例：毎日午前9時に実行
0 9 * * * /path/to/venv/bin/python /path/to/app/tasks.py
"""

import os
import sys
import logging
from datetime import datetime

# アプリケーションのルートディレクトリをパスに追加
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduled_tasks.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('scheduled_tasks')

def setup_app_context():
    """アプリケーションコンテキストのセットアップ"""
    from app import create_app
    app = create_app('production')  # 本番環境設定を使用
    return app

def run_due_date_reminders():
    """返却期限リマインダーの実行"""
    from services.reservation_service import check_due_date_reminders
    
    logger.info('返却期限リマインダーの実行を開始します')
    try:
        with app.app_context():
            count = check_due_date_reminders()
            logger.info(f'返却期限リマインダーを {count} 件送信しました')
    except Exception as e:
        logger.error(f'返却期限リマインダーの実行中にエラーが発生しました: {str(e)}')

def clean_expired_reservations():
    """期限切れ予約のクリーンアップ"""
    from models import db, Reservation
    from datetime import datetime, timedelta
    
    logger.info('期限切れ予約のクリーンアップを開始します')
    try:
        with app.app_context():
            # 「通知済み」状態で7日以上経過した予約をキャンセル
            expire_date = datetime.now() - timedelta(days=7)
            expired_reservations = Reservation.query.filter(
                Reservation.status == 'notified',
                Reservation.reservation_date < expire_date
            ).all()
            
            for reservation in expired_reservations:
                reservation.status = 'cancelled'
                logger.info(f'期限切れ予約をキャンセル: ID={reservation.id}, Book={reservation.book_id}, User={reservation.user_id}')
            
            db.session.commit()
            logger.info(f'期限切れ予約を {len(expired_reservations)} 件キャンセルしました')
    except Exception as e:
        logger.error(f'期限切れ予約クリーンアップ中にエラーが発生しました: {str(e)}')

if __name__ == '__main__':
    logger.info('定期実行タスクを開始します')
    
    try:
        app = setup_app_context()
        
        # 各タスクを実行
        run_due_date_reminders()
        clean_expired_reservations()
        
        logger.info('定期実行タスクが正常に完了しました')
    except Exception as e:
        logger.error(f'定期実行タスク中にエラーが発生しました: {str(e)}')