# routes/reservations.py
from flask import Blueprint, request, redirect, url_for, flash, render_template
from flask_login import login_required, current_user
from models import db, Reservation, Book, OperationLog, ReservationStatus
from datetime import datetime

# Blueprintの設定 - 'reservations'という名前で登録
reservations_bp = Blueprint('reservations', __name__, url_prefix='/reservations')

@reservations_bp.route('/create/<int:book_id>', methods=['POST'])
@login_required
def create(book_id):
    """書籍の予約を作成"""
    book = Book.query.get_or_404(book_id)
    
    # 既に予約済みかチェック
    existing_reservation = Reservation.query.filter_by(
        book_id=book_id,
        user_id=current_user.id,
        status=ReservationStatus.PENDING
    ).first()
    
    if existing_reservation:
        flash('この書籍は既に予約済みです。', 'warning')
        return redirect(url_for('books.book_detail', book_id=book_id))
    
    # 予約作成
    reservation = Reservation(
        book_id=book_id,
        user_id=current_user.id,
        status=ReservationStatus.PENDING,
        reservation_date=datetime.utcnow()
    )
    db.session.add(reservation)
    
    # 操作ログの記録
    log = OperationLog(
        user_id=current_user.id,
        action='create_reservation',
        target=f'Book {book_id}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    flash('書籍を予約しました。', 'success')
    return redirect(url_for('books.book_detail', book_id=book_id))

@reservations_bp.route('/cancel/<int:id>', methods=['POST'])
@login_required
def cancel(id):
    """予約をキャンセル"""
    reservation = Reservation.query.get_or_404(id)
    
    # 自分の予約かどうかチェック
    if reservation.user_id != current_user.id and not current_user.is_admin:
        flash('この予約をキャンセルする権限がありません。', 'danger')
        return redirect(url_for('books.book_detail', book_id=reservation.book_id))
    
    # 予約のステータスを更新
    reservation.status = ReservationStatus.CANCELLED
    
    # 操作ログの記録
    log = OperationLog(
        user_id=current_user.id,
        action='cancel_reservation',
        target=f'Reservation {id}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    flash('予約をキャンセルしました。', 'success')
    return redirect(url_for('books.book_detail', book_id=reservation.book_id))

@reservations_bp.route('/book/<int:book_id>')
@login_required
def book_reservations(book_id):
    """書籍の予約一覧（管理者用）"""
    if not current_user.is_admin:
        flash('この機能は管理者のみ利用できます。', 'danger')
        return redirect(url_for('books.book_detail', book_id=book_id))
    
    book = Book.query.get_or_404(book_id)
    reservations = Reservation.query.filter_by(
        book_id=book_id,
        status=ReservationStatus.PENDING
    ).order_by(Reservation.reservation_date).all()
    
    return render_template(
        'reservations/book_reservations.html',
        book=book,
        reservations=reservations
    )