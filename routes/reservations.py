# routes/reservations.py
from flask import Blueprint, request, redirect, url_for, flash, render_template
from flask_login import login_required, current_user
from models import db, Reservation, Book, OperationLog, ReservationStatus, LoanHistory
from services.slack_service import send_slack_dm_to_user
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
    
    # 現在この本を借りているユーザーに通知
    current_loan = LoanHistory.query.filter_by(
        book_id=book_id,
        return_date=None
    ).first()
    
    if current_loan and current_loan.borrower_id != current_user.id:
        borrower = current_loan.borrower
        book_url = f"http://localhost/books/book/{book_id}"
        message = (
            f":bell: *予約通知*\n\n"
            f"あなたが現在借りている本に新しい予約が入りました：\n"
            f"*書籍：* <{book_url}|{book.title}>\n"
            f"*予約者：* {current_user.name}\n\n"
            f":warning: この本は延長ができなくなります。返却期限までにご返却をお願いいたします。"
        )
        send_slack_dm_to_user(borrower, message)
    
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

@reservations_bp.route('/borrow/<int:reservation_id>', methods=['POST'])
@login_required
def borrow_from_reservation(reservation_id):
    """予約から直接借りる"""
    reservation = Reservation.query.get_or_404(reservation_id)
    
    # 自分の予約かどうかチェック
    if reservation.user_id != current_user.id:
        flash('この予約から借りる権限がありません。', 'danger')
        return redirect(url_for('home.dashboard'))
    
    # 予約状況をチェック
    if reservation.status != ReservationStatus.PENDING:
        flash('この予約は無効です。', 'danger')
        return redirect(url_for('home.dashboard'))
    
    # 本が利用可能または予約ありかチェック（1番目の予約なら借りられる）
    if reservation.book.status.value not in ['利用可能', '予約あり']:
        flash('この本は現在貸出中です。', 'warning')
        return redirect(url_for('home.dashboard'))
    
    # 予約順位をチェック（1番目でない場合は借りられない）
    if reservation.queue_position != 1:
        flash('まだあなたの順番ではありません。', 'warning')
        return redirect(url_for('home.dashboard'))
    
    # 貸出制限をチェック
    current_loans = LoanHistory.query.filter_by(
        borrower_id=current_user.id, 
        return_date=None
    ).count()
    
    if current_loans >= current_user.max_loan_limit:
        flash('貸出可能な上限に達しています。', 'warning')
        return redirect(url_for('home.dashboard'))
    
    # 貸出処理
    from services.book_service import borrow_book
    result = borrow_book(reservation.book_id, current_user.id)
    
    if "成功" in result:
        # 予約を完了状態に更新
        reservation.status = ReservationStatus.COMPLETED
        
        # 操作ログの記録
        log = OperationLog(
            user_id=current_user.id,
            action='borrow_from_reservation',
            target=f'Book {reservation.book_id} from Reservation {reservation_id}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        flash('予約していた本を借りました。', 'success')
    else:
        flash(f'貸出に失敗しました: {result}', 'danger')
    
    return redirect(url_for('home.dashboard'))

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