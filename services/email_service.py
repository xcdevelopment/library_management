from flask import current_app, render_template
from flask_mail import Message
from datetime import datetime, timedelta
import logging
import os
from threading import Thread

logger = logging.getLogger(__name__)

def send_async_email(app, msg):
    """非同期でメールを送信"""
    with app.app_context():
        try:
            from app import mail
            mail.send(msg)
        except Exception as e:
            logger.error(f"Failed to send async email: {str(e)}")

def send_email(subject, recipients, template, **kwargs):
    """
    メールを送信する汎用関数
    
    Args:
        subject (str): メールの件名
        recipients (list): 受信者のメールアドレスリスト
        template (str): 使用するテンプレート名（拡張子なし）
        **kwargs: テンプレートに渡す追加の変数
    """
    # メール機能が無効化されている場合はスキップ
    if not os.environ.get('MAIL_ENABLED', 'false').lower() in ['true', '1', 'yes']:
        logger.info(f"Email sending disabled. Would have sent: {subject} to {recipients}")
        return True
    
    try:
        app = current_app._get_current_object()
        
        msg = Message(
            subject=subject,
            recipients=recipients if isinstance(recipients, list) else [recipients]
        )
        
        # HTMLとテキスト両方のテンプレートを使用
        try:
            msg.html = render_template(f'{template}.html', **kwargs)
        except Exception as e:
            logger.error(f"Failed to render HTML template '{template}.html': {str(e)}")
            msg.html = f"<p>Message content could not be rendered properly.</p>"
        
        # テキスト版のテンプレートがある場合は使用
        try:
            msg.body = render_template(f'{template}.txt', **kwargs)
        except Exception as e:
            logger.warning(f"Text template '{template}.txt' not found or error: {str(e)}")
            # HTMLからプレーンテキストを生成する簡易的な方法
            msg.body = f"This is a plain text version of the email. Subject: {subject}"
        
        # メール送信を非同期で行う
        Thread(target=send_async_email, args=(app, msg)).start()
        
        logger.info(f"Email queued for sending to {recipients}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to prepare email: {str(e)}")
        return False

def send_reservation_notification(user, book):
    """
    予約可能通知を送信する
    """
    if not user.email:
        logger.warning(f"Cannot send reservation notification to user {user.id}: No email address")
        return False
    
    expiry_date = datetime.utcnow() + timedelta(days=7)
    
    return send_email(
        f"【図書予約通知】{book.title}が利用可能になりました",
        user.email,
        "emails/reservation_available",
        user=user,
        book=book,
        expiry_date=expiry_date
    )

def send_due_date_reminder(loan):
    """
    返却期限リマインダーを送信する
    """
    if not loan.borrower or not loan.borrower.email:
        logger.warning(f"Cannot send due date reminder for loan {loan.id}: No borrower email")
        return False
    
    days_remaining = (loan.due_date - datetime.utcnow()).days
    
    return send_email(
        f"【返却期限のお知らせ】{loan.book_title}",
        loan.borrower.email,
        "emails/due_date_reminder",
        user=loan.borrower,
        book=loan.book,
        loan=loan,
        days_remaining=days_remaining
    )

def send_borrow_confirmation(loan):
    """
    書籍貸出時の確認メールを送信する
    """
    if not loan.borrower or not loan.borrower.email:
        logger.warning(f"Cannot send borrow confirmation for loan {loan.id}: No borrower email")
        return False
    
    return send_email(
        f"【貸出完了】{loan.book_title}",
        loan.borrower.email,
        "emails/borrow_confirmation",
        user=loan.borrower,
        book=loan.book,
        loan=loan
    )

def send_admin_borrow_notification(loan):
    """
    管理者に書籍貸出を通知するメールを送信する
    """
    if not loan.borrower or not loan.book:
        logger.warning(f"Cannot send admin borrow notification for loan {loan.id}: Missing data")
        return False
    
    from models import User
    admins = User.query.filter_by(is_admin=True).all()
    admin_emails = [admin.email for admin in admins if admin.email]

    if not admin_emails:
        logger.info("No admin users found with email addresses to notify.")
        return True # 管理者がいない場合はエラーとしない

    return send_email(
        f"【管理者通知】書籍貸出：{loan.book.title}",
        admin_emails,
        "emails/admin_borrow_notification",
        book_title=loan.book.title,
        loan_date=loan.loan_date,
        borrower_name=loan.borrower.name
    )
