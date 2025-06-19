import os
import requests
import logging
from datetime import date, timedelta
from models import User, Book, LoanHistory, Reservation

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Power AutomateのWebhook URLを環境変数から取得
POWER_AUTOMATE_URL = os.environ.get('POWER_AUTOMATE_WEBHOOK_URL')

def _send_notification(payload: dict):
    """
    Power AutomateにJSONペイロードを送信する共通関数。
    """
    if not POWER_AUTOMATE_URL:
        logging.error("環境変数 'POWER_AUTOMATE_WEBHOOK_URL' が設定されていません。")
        return False

    try:
        response = requests.post(POWER_AUTOMATE_URL, json=payload)
        response.raise_for_status()
        logging.info(f"通知を正常に送信しました。 タイプ: {payload.get('mail_type')}, 宛先: {payload.get('recipient_email')}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Power Automateへの通知送信に失敗しました: {e}")
        return False

def send_borrow_confirmation(loan: LoanHistory):
    """
    【機能1-A】書籍を借りた本人へ確認メールを送信する。
    """
    if not loan or not loan.borrower or not loan.book:
        return

    payload = {
        "mail_type": "borrow_confirmation",
        "recipient_email": loan.borrower.email,
        "recipient_name": loan.borrower.name,
        "book_title": loan.book.title,
        "loan_date": loan.loan_date.strftime('%Y-%m-%d'),
        "due_date": loan.due_date.strftime('%Y-%m-%d')
    }
    _send_notification(payload)

def send_admin_borrow_notification(loan: LoanHistory):
    """
    【機能1-B】管理者に書籍貸出を通知するメールを送信する。
    """
    if not loan or not loan.borrower or not loan.book:
        return

    admins = User.query.filter_by(is_admin=True).all()
    for admin in admins:
        payload = {
            "mail_type": "admin_borrow_notification",
            "recipient_email": admin.email,
            "recipient_name": admin.name,
            "book_title": loan.book.title,
            "loan_date": loan.loan_date.strftime('%Y-%m-%d'),
            "borrower_name": loan.borrower.name
        }
        _send_notification(payload)

def send_reservation_available_notification(reservation: Reservation):
    """
    【機能2】予約していた本が利用可能になったことを本人へ通知する。
    """
    if not reservation or not reservation.user or not reservation.book:
        return

    payload = {
        "mail_type": "reservation_available",
        "recipient_email": reservation.user.email,
        "recipient_name": reservation.user.name,
        "book_title": reservation.book.title
    }
    _send_notification(payload)

def send_due_date_reminder(loan: LoanHistory):
    """
    【機能3】返却期限が近いことを本人へ通知する（リマインダー）。
    """
    if not loan or not loan.borrower or not loan.book:
        return

    payload = {
        "mail_type": "due_date_reminder",
        "recipient_email": loan.borrower.email,
        "recipient_name": loan.borrower.name,
        "book_title": loan.book.title,
        "due_date": loan.due_date.strftime('%Y-%m-%d')
    }
    _send_notification(payload)

def run_due_date_reminder_check():
    """
    返却期限が3日後の貸出記録を全て検索し、リマインダーを送信する。
    PythonAnywhereのScheduled Taskからこの関数を呼び出す。
    """
    logging.info("返却期限リマインダーのチェックを開始します。")
    
    reminder_date = date.today() + timedelta(days=3)
    loans_to_remind = LoanHistory.query.filter(
        LoanHistory.due_date == reminder_date,
        LoanHistory.return_date.is_(None)
    ).all()
    
    if not loans_to_remind:
        logging.info("本日リマインド対象の貸出はありませんでした。")
        return

    logging.info(f"{len(loans_to_remind)}件のリマインドを送信します。")
    for loan in loans_to_remind:
        send_due_date_reminder(loan)
        
    logging.info("返却期限リマインダーの処理が完了しました。")

if __name__ == '__main__':
    run_due_date_reminder_check() 