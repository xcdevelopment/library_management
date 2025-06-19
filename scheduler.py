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

from flask import url_for

from models import db, User, Book, LoanHistory, Reservation, ReservationStatus
from services.slack_service import send_slack_dm_to_user
from services.book_service import release_book_from_reservation

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
    app = create_app(os.getenv('FLASK_ENV') or 'production')
    return app

def check_due_date_reminders(logger):
    """返却期限が近い貸出のリマインダーを送信"""
    now = datetime.utcnow()
    reminder_date = now + timedelta(days=3)
    
    loans = LoanHistory.query.filter(
        LoanHistory.return_date.is_(None),
        LoanHistory.reminder_sent.is_(False),
        LoanHistory.due_date <= reminder_date,
        LoanHistory.due_date > now
    ).all()
    
    reminder_count = 0
    for loan in loans:
        try:
            days_remaining = (loan.due_date.date() - datetime.utcnow().date()).days
            
            book_url = url_for('books.book_detail', book_id=loan.book_id, _external=True)
            message = (
                f"図書管理アプリです！貸出中の本の返却期限が近づいています。\n"
                f"書籍：<{book_url}|{loan.book.title}>\n"
                f"返却期限：{loan.due_date.strftime('%Y-%m-%d')} ({days_remaining}日前)\n\n"
                f"期限内のご返却にご協力をお願いいたします。"
            )
            
            # 貸出者にDMを送信
            success = send_slack_dm_to_user(loan.borrower, message)

            if success:
                loan.reminder_sent = True
                db.session.add(loan)
                db.session.commit()
                reminder_count += 1
                logger.info(f"Due date reminder sent for loan {loan.id}")
            else:
                logger.warning(f"Failed to send due date reminder for loan {loan.id}")
        except Exception as e:
            logger.error(f"Error sending reminder for loan {loan.id}: {e}")
            db.session.rollback()

    if reminder_count > 0:
        logger.info(f'返却期限リマインダーを {reminder_count} 件送信しました')
    else:
        logger.info('送信すべき返却期限リマインダーはありませんでした')
    
    return reminder_count

def cleanup_expired_reservations(logger):
    """期限切れ予約をクリーンアップ"""
    expiry_date = datetime.utcnow() - timedelta(days=7)
    
    expired_reservations = Reservation.query.filter(
        Reservation.status == ReservationStatus.NOTIFIED,
        Reservation.notification_sent_at < expiry_date
    ).all()
    
    cancelled_count = 0
    for reservation in expired_reservations:
        try:
            reservation.status = ReservationStatus.EXPIRED
            release_book_from_reservation(reservation.book)
            db.session.add(reservation)
            db.session.commit()
            cancelled_count += 1
            logger.info(f"Expired reservation {reservation.id} for book {reservation.book.title}")
        except Exception as e:
            logger.error(f"Error expiring reservation {reservation.id}: {e}")
            db.session.rollback()

    if cancelled_count > 0:
        logger.info(f'期限切れ予約を {cancelled_count} 件クリーンアップしました')
    else:
        logger.info('クリーンアップすべき期限切れ予約はありませんでした')
    
    return cancelled_count

def main():
    """メイン実行関数"""
    logger = setup_logging()
    logger.info('定期実行タスクを開始します')
    
    try:
        app = setup_app_context()
        with app.app_context():
            # url_forが動作するようにリクエストコンテキストをプッシュ
            with app.test_request_context():
                check_due_date_reminders(logger)
                cleanup_expired_reservations(logger)
        
        logger.info('定期実行タスクが正常に完了しました')
        
    except Exception as e:
        logger.error(f'定期実行タスク中にエラーが発生しました: {str(e)}', exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
