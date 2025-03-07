from datetime import datetime
from flask import current_app
from sqlalchemy import and_, or_

from models import db, Book, User, Reservation, LoanHistory
from services.email_service import send_reservation_notification, send_due_date_reminder

def get_reservations(user_id=None, book_id=None, status=None):
    """予約一覧を取得する（フィルタ条件付き）"""
    query = Reservation.query

    if user_id:
        query = query.filter(Reservation.user_id == user_id)

    if book_id:
        query = query.filter(Reservation.book_id == book_id)

    if status:
        query = query.filter(Reservation.status == status)

    # 予約日の降順で取得
    return query.order_by(Reservation.reservation_date.desc()).all()

def get_active_reservations_for_book(book_id):
    """書籍のアクティブな予約一覧を取得する"""
    return Reservation.query.filter(
        and_(
            Reservation.book_id == book_id,
            Reservation.status.in_(['pending', 'notified'])
        )
    ).order_by(Reservation.reservation_date).all()

def get_reservation_by_id(reservation_id):
    """IDで予約を取得する"""
    return Reservation.query.get(reservation_id)

def create_reservation(book_id, user_id):
    """予約を新規作成する"""
    # 既に予約済みかチェック
    existing_reservation = Reservation.query.filter(
        and_(
            Reservation.book_id == book_id,
            Reservation.user_id == user_id,
            Reservation.status.in_(['pending', 'notified'])
        )
    ).first()

    if existing_reservation:
        raise ValueError('この本は既に予約されています')

    # 書籍の存在確認
    book = Book.query.get(book_id)
    if not book:
        raise ValueError('指定された書籍が見つかりません')

    # ユーザーの存在確認
    user = User.query.get(user_id)
    if not user:
        raise ValueError('指定されたユーザーが見つかりません')

    # 予約の作成
    reservation = Reservation(
        book_id=book_id,
        user_id=user_id,
        status='pending'
    )

    db.session.add(reservation)
    db.session.commit()

    current_app.logger.info(f'予約作成: User {user_id} - Book {book_id}')
    return reservation

def cancel_reservation(reservation_id, user_id=None):
    """予約をキャンセルする"""
    reservation = get_reservation_by_id(reservation_id)
    if not reservation:
        raise ValueError('指定された予約が見つかりません')

    # 管理者でない場合、自分の予約のみキャンセル可能
    if user_id is not None and reservation.user_id != user_id:
        user = User.query.get(user_id)
        if not user or not user.is_admin:
            raise ValueError('この予約をキャンセルする権限がありません')

    reservation.status = 'cancelled'
    db.session.commit()

    current_app.logger.info(f'予約キャンセル: Reservation {reservation_id}')
    return reservation

def process_book_return(book_id):
    """本が返却された時の処理（予約通知）"""
    # 最も古い予約を取得
    oldest_reservation = Reservation.query.filter(
        and_(
            Reservation.book_id == book_id,
            Reservation.status == 'pending'
        )
    ).order_by(Reservation.reservation_date).first()

    if not oldest_reservation:
        return None

    book = Book.query.get(book_id)
    user = User.query.get(oldest_reservation.user_id)

    # 予約状態を更新
    oldest_reservation.status = 'notified'
    oldest_reservation.notification_sent = True
    db.session.commit()

    # メール通知
    if user.email:
        send_reservation_notification(user, book)
        current_app.logger.info(f'予約通知送信: User {user.id} - Book {book.id}')

    return oldest_reservation

def check_due_date_reminders():
    """返却期限が近い貸出のリマインダーを送信"""
    # 期限3日前で、まだリマインドメールを送っていない貸出を検索
    loans = LoanHistory.query.filter(
        and_(
            LoanHistory.return_date.is_(None),
            LoanHistory.reminder_sent.is_(False),
            LoanHistory.due_date.isnot(None),
        )
    ).all()

    reminder_count = 0
    for loan in loans:
        days_left = loan.days_until_due()
        # 残り3日以内かつリマインダー未送信の場合
        if days_left is not None and days_left <= 3 and not loan.reminder_sent:
            user = loan.borrower
            book = loan.book

            # メール送信
            if user and user.email:
                success = send_due_date_reminder(loan)
                if success:
                    loan.reminder_sent = True
                    reminder_count += 1

    # 変更を保存
    if reminder_count > 0:
        db.session.commit()
        current_app.logger.info(f'{reminder_count}件の返却期限リマインダーを送信しました')

    return reminder_count

def get_user_reservation_count(user_id):
    """ユーザーのアクティブな予約数を取得"""
    return Reservation.query.filter(
        and_(
            Reservation.user_id == user_id,
            Reservation.status.in_(['pending', 'notified'])
        )
    ).count()

def get_next_in_reservation_queue(book_id):
    """予約待ちキューの次のユーザーを取得"""
    next_reservation = Reservation.query.filter(
        and_(
            Reservation.book_id == book_id,
            Reservation.status == 'pending'
        )
    ).order_by(Reservation.reservation_date).first()

    if next_reservation:
        return next_reservation.user
    return None