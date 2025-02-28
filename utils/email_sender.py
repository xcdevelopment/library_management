import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app, render_template

def send_email(to, subject, template, **kwargs):
    """
    メールを送信する
    
    Parameters:
    - to: 送信先メールアドレス
    - subject: メール件名
    - template: メールテンプレート名（templates/emails/ 内のファイル名）
    - **kwargs: テンプレートに渡す変数
    """
    app = current_app._get_current_object()
    
    # メール設定の取得
    sender = app.config['MAIL_DEFAULT_SENDER']
    smtp_server = app.config['MAIL_SERVER']
    smtp_port = app.config['MAIL_PORT']
    smtp_username = app.config['MAIL_USERNAME']
    smtp_password = app.config['MAIL_PASSWORD']
    use_tls = app.config['MAIL_USE_TLS']
    
    # HTML本文の作成
    html_body = render_template(f'emails/{template}.html', **kwargs)
    
    # プレーンテキスト本文の作成
    text_body = render_template(f'emails/{template}.txt', **kwargs)
    
    # メッセージオブジェクトの作成
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to
    
    # プレーンテキストとHTMLパートの追加
    msg.attach(MIMEText(text_body, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))
    
    try:
        # SMTPサーバー接続
        if use_tls:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            if app.config['MAIL_USE_STARTTLS']:
                server.starttls()
        
        # ログイン
        if smtp_username and smtp_password:
            server.login(smtp_username, smtp_password)
        
        # メール送信
        server.sendmail(sender, to, msg.as_string())
        server.quit()
        
        app.logger.info(f'メール送信成功: {to}, 件名: {subject}')
        return True
    except Exception as e:
        app.logger.error(f'メール送信エラー: {str(e)}')
        return False

def send_reservation_notification(user, book):
    """予約した本が利用可能になった通知を送信"""
    if not user.email:
        current_app.logger.warning(f'ユーザー {user.id} にメールアドレスが設定されていません')
        return False
    
    return send_email(
        to=user.email,
        subject=f'【図書管理アプリ】予約した本が利用可能です: {book.title}',
        template='reservation_available',
        user=user,
        book=book
    )

def send_due_date_reminder(loan):
    """返却期限が近づいていることを通知"""
    user = loan.borrower
    book = loan.book
    days_remaining = loan.days_until_due()
    
    if not user or not user.email:
        current_app.logger.warning(f'貸出 {loan.id} のユーザーにメールアドレスが設定されていません')
        return False
    
    return send_email(
        to=user.email,
        subject=f'【図書管理アプリ】返却期限のお知らせ: {book.title}',
        template='due_date_reminder',
        user=user,
        book=book,
        loan=loan,
        days_remaining=days_remaining
    )