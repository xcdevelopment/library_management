from flask_mail import Mail, Message

def init_mail(app):
    """メール機能の初期化"""
    mail = Mail(app)
    return mail

def send_reservation_reminder(user_email, book_title):
    """予約リマインダーメールの送信"""
    msg = Message('本の予約リマインダー',
                  sender='noreply@library.com',
                  recipients=[user_email])
    msg.body = f'{book_title}の予約可能期間が近づいています。'
    mail.send(msg)

# グローバル変数として初期化
mail = None
