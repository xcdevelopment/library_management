# services/book_service.py
from datetime import datetime, timedelta
from models import db, Book, LoanHistory, Reservation, OperationLog
from flask import current_app

def borrow_book(book_id, user_id, due_days=14):
    """書籍を貸し出す処理"""
    book = Book.query.get_or_404(book_id)
    
    # 貸出可能かチェック
    if not book.is_available:
        return False, "この書籍は現在貸出できません。"
    
    # 貸出処理
    book.is_available = False
    book.borrower_id = user_id
    
    # 貸出履歴の作成
    due_date = datetime.now() + timedelta(days=due_days)
    loan_history = LoanHistory(
        book_id=book.id,
        book_title=book.title,
        borrower_id=user_id,
        due_date=due_date
    )
    
    db.session.add(loan_history)
    db.session.commit()
    
    current_app.logger.info(f"Book {book.id} borrowed by user {user_id}")
    return True, loan_history

def return_book(book_id, user_id):
    """書籍を返却する処理"""
    book = Book.query.get_or_404(book_id)
    
    # 借りている人が一致するか確認
    if book.borrower_id != user_id:
        return False, "この書籍はあなたが借りたものではありません。"
    
    # 返却処理
    book.is_available = True
    book.borrower_id = None
    
    # 貸出履歴の更新
    loan_history = LoanHistory.query.filter_by(
        book_id=book.id, 
        borrower_id=user_id, 
        return_date=None
    ).order_by(LoanHistory.loan_date.desc()).first()
    
    if loan_history:
        loan_history.return_date = datetime.now()
    
    # 予約があれば、最も古い予約を処理
    reservation = Reservation.query.filter_by(
        book_id=book.id, 
        status='pending'
    ).order_by(Reservation.reservation_date).first()
    
    if reservation:
        reservation.status = 'notified'
        reservation.notification_sent = True
    
    db.session.commit()
    
    current_app.logger.info(f"Book {book.id} returned by user {user_id}")
    return True, "書籍が返却されました。"

def reserve_book(book_id, user_id):
    """書籍を予約する処理"""
    book = Book.query.get_or_404(book_id)
    
    # 既に予約していないかチェック
    existing_reservation = Reservation.query.filter_by(
        book_id=book_id,
        user_id=user_id,
        status='pending'
    ).first()
    
    if existing_reservation:
        return False, "あなたはすでにこの書籍を予約しています。"
    
    # 予約処理
    reservation = Reservation(
        book_id=book_id,
        user_id=user_id
    )
    
    db.session.add(reservation)
    db.session.commit()
    
    current_app.logger.info(f"Book {book_id} reserved by user {user_id}")
    return True, "書籍が予約されました。"

def cancel_reservation(reservation_id, user_id):
    """予約をキャンセルする処理"""
    reservation = Reservation.query.get_or_404(reservation_id)
    
    # 予約者が一致するか確認
    if reservation.user_id != user_id:
        return False, "この予約はあなたのものではありません。"
    
    # 予約キャンセル処理
    reservation.status = 'cancelled'
    
    db.session.commit()
    
    current_app.logger.info(f"Reservation {reservation_id} cancelled by user {user_id}")
    return True, "予約がキャンセルされました。"