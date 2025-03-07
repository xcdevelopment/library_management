#!/usr/bin/env python
"""
図書館システム定期実行タスク

以下の定期タスクを実行します：
1. 返却期限通知 (3日前)
2. 予約可能通知 (返却された本の予約待ち通知)
3. 期限切れ予約のクリーンアップ (7日間放置された予約)

使用例：
毎日午前9時に実行
0 9 * * * /path/to/venv/bin/python /path/to/app/scheduler.py
"""

import os
import sys
import logging
from datetime import datetime, timedelta

# アプリケーションのルートディレクトリをパスに追加
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from models import db, User, Book, LoanHistory, Reservation
from services.email_service import send_due_date_reminder, send_reservation_notification

# ロギング設定
def setup_logging():
    """ロギングの設定を行い、ロガーを返す"""
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, 'scheduled_tasks.log')),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('scheduled_tasks')

def setup_app_context():
    """アプリケーションコンテキストのセットアップ"""
    from app import create_app
    app = create_app('production')
    return app

def check_due_date_reminders(logger):
    """返却期限が近い貸出のリマインダーを送信"""
    # 返却期限が3日以内で、まだリマインダーを送っていない貸出を検索
    now = datetime.utcnow()
    reminder_date = now + timedelta(days=3)
    
    loans = LoanHistory.query.filter(
        LoanHistory.return_date.is_(None),
        LoanHistory.reminder_sent.is_(False),
        LoanHistory.due_date <= reminder_date,
        LoanHistory.due_date > now  # まだ期限切れではないもの
    ).all()
    
    reminder_count = 0
    for loan in loans:
        # メール送信処理
        success = send_due_date_reminder(loan)
        if success:
            loan.reminder_sent = True
            reminder_count += 1
            logger.info(f"Due date reminder sent for loan {loan.id} (book: {loan.book_title}, user: {loan.borrower.username if loan.borrower else 'unknown'})")
    
    # 変更を保存
    if reminder_count > 0:
        db.session.commit()
        logger.info(f'返却期限リマインダーを {reminder_count} 件送信しました')
    else:
        logger.info('送信すべき返却期限リマインダーはありませんでした')
    
    return reminder_count

def cleanup_expired_reservations(logger):
    """期限切れ予約をクリーンアップ"""
    # 7日以上前に通知された予約をキャンセル
    expiry_date = datetime.utcnow() - timedelta(days=7)
    
    expired_reservations = Reservation.query.filter(
        Reservation.status == 'notified',
        Reservation.notification_sent.is_(True),
        Reservation.reservation_date < expiry_date
    ).all()
    
    cancelled_count = 0
    for reservation in expired_reservations:
        # 予約をキャンセル
        reservation.status = 'cancelled'
        cancelled_count += 1
        logger.info(f"Cancelled expired reservation {reservation.id} (book: {reservation.book.title}, user: {reservation.user.username})")
    
    # 変更を保存
    if cancelled_count > 0:
        db.session.commit()
        logger.info(f'期限切れ予約を {cancelled_count} 件キャンセルしました')
    else:
        logger.info('キャンセルすべき期限切れ予約はありませんでした')
    
    return cancelled_count

def main():
    """メイン実行関数"""
    logger = setup_logging()
    logger.info('定期実行タスクを開始します')
    
    try:
        app = setup_app_context()
        with app.app_context():
            # 1. 返却期限リマインダー
            check_due_date_reminders(logger)
            
            # 2. 期限切れ予約のクリーンアップ
            cleanup_expired_reservations(logger)
        
        logger.info('定期実行タスクが正常に完了しました')
        
    except Exception as e:
        logger.error(f'定期実行タスク中にエラーが発生しました: {str(e)}', exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
