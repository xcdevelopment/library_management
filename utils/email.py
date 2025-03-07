from flask import current_app
from flask_mail import Message, Mail
from threading import Thread
import smtplib

mail = Mail()

def test_email_config():
    """メール設定をテストする"""
    try:
        with smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT']) as server:
            server.starttls()
            server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
            return True, "メール設定は正常です。"
    except Exception as e:
        return False, f"メール設定エラー: {str(e)}"

def send_async_email(app, msg):
    """非同期でメールを送信"""
    with app.app_context():
        mail.send(msg)

def send_email(subject, recipients, body):
    """メールを送信"""
    msg = Message(
        subject=subject,
        recipients=recipients,
        body=body,
        sender=current_app.config['MAIL_DEFAULT_SENDER']
    )
    Thread(
        target=send_async_email,
        args=(current_app._get_current_object(), msg)
    ).start()

def send_book_available_notification(user, book):
    """予約した本が利用可能になった際の通知メール"""
    try:
        subject = f'【図書管理システム】予約した本が利用可能になりました：{book.title}'
        body = f'''
{user.name} 様

予約されていた以下の本が利用可能になりました：

書籍名：{book.title}
著者：{book.author}

7日以内に借りに来てください。
7日を過ぎると予約は自動的にキャンセルされます。

※このメールは自動送信されています。返信はできません。
'''
        if user.email:
            send_email(subject, [user.email], body)
    except Exception as e:
        current_app.logger.error(f'メール送信エラー: {str(e)}')
        # エラーが発生しても処理を継続 