from flask import Blueprint, render_template, request
from flask_wtf import FlaskForm
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_
from models import db, LoanHistory, Book, Reservation, User, BookStatus, Announcement, ReservationStatus
from services.book_service import get_popular_books

home_bp = Blueprint('home', __name__)

@home_bp.route('/')
@login_required
def dashboard():
    """ユーザーのパーソナライズされたホームダッシュボード"""
    
    # 現在の貸出状況
    current_loans = LoanHistory.query.filter(
        and_(
            LoanHistory.borrower_id == current_user.id,
            LoanHistory.return_date.is_(None)
        )
    ).join(Book).all()
    
    # 返却期限が近い本（3日以内）
    due_soon = []
    overdue = []
    for loan in current_loans:
        if loan.due_date:
            days_until_due = (loan.due_date.date() - datetime.now().date()).days
            if days_until_due < 0:
                overdue.append(loan)
            elif days_until_due <= 3:
                due_soon.append(loan)
    
    # 現在の予約状況（有効な予約のみ）
    current_reservations = Reservation.query.filter(
        and_(
            Reservation.user_id == current_user.id,
            Reservation.status.in_([ReservationStatus.PENDING, ReservationStatus.NOTIFIED])
        )
    ).join(Book).all()
    
    # 予約している本のうち、貸出可能になったものを特定
    available_reservations = []
    for reservation in current_reservations:
        if (reservation.book.status == BookStatus.AVAILABLE and 
            reservation.queue_position == 1):
            available_reservations.append(reservation)
    
    # 借りられる本の数
    max_loans = current_user.max_loan_limit or 3
    current_loan_count = len(current_loans)
    available_loan_slots = max_loans - current_loan_count
    
    # 人気の本（最近1ヶ月の貸出数）
    one_month_ago = datetime.now() - timedelta(days=30)
    popular_books = get_popular_books(limit=5, since=one_month_ago)
    
    # 最近追加された本
    recent_books = Book.query.filter_by(status=BookStatus.AVAILABLE).order_by(
        desc(Book.created_at)
    ).limit(5).all()
    
    # アラート情報
    alerts = []
    if overdue:
        alerts.append({
            'type': 'danger',
            'message': f'{len(overdue)}冊の本が返却期限を過ぎています'
        })
    if due_soon:
        alerts.append({
            'type': 'warning',
            'message': f'{len(due_soon)}冊の本が3日以内に返却期限です'
        })
    if available_loan_slots <= 0:
        alerts.append({
            'type': 'info',
            'message': '貸出可能な冊数の上限に達しています'
        })
    
    # アクティブなお知らせを取得（優先度順）
    from sqlalchemy import case
    priority_order = case(
        (Announcement.priority == 'high', 3),
        (Announcement.priority == 'medium', 2),
        (Announcement.priority == 'low', 1),
        else_=0
    )
    
    active_announcements = Announcement.query.filter_by(
        is_active=True
    ).order_by(
        priority_order.desc(),
        Announcement.created_at.desc()
    ).limit(5).all()
    
    # CSRFフォームを作成
    csrf_form = FlaskForm()
    
    return render_template('home/dashboard.html',
                         current_loans=current_loans,
                         due_soon=due_soon,
                         overdue=overdue,
                         current_reservations=current_reservations,
                         available_reservations=available_reservations,
                         available_loan_slots=available_loan_slots,
                         max_loans=max_loans,
                         popular_books=popular_books,
                         recent_books=recent_books,
                         alerts=alerts,
                         announcements=active_announcements,
                         csrf_form=csrf_form)