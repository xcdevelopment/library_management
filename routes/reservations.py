from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import func

from models import db, Book, User, Reservation, OperationLog
from services.reservation_service import (
    get_reservations, get_reservation_by_id, create_reservation,
    cancel_reservation as cancel_reservation_service,
    get_user_reservation_count, get_active_reservations_for_book
)
from services.auth_service import create_user_operation_log
from utils.decorators import admin_required

reservations_bp = Blueprint('reservations', __name__, url_prefix='/reservations')

@reservations_bp.route('/')
@login_required
def index():
    """ユーザーの予約一覧を表示"""
    # 管理者は全ての予約を表示、一般ユーザーは自分の予約のみ表示
    if current_user.is_admin:
        reservations = get_reservations()
    else:
        reservations = get_reservations(user_id=current_user.id)
    
    return render_template('reservations/index.html', 
                          title='予約一覧', 
                          reservations=reservations,
                          is_admin=current_user.is_admin)

@reservations_bp.route('/admin')
@login_required
@admin_required
def admin():
    """管理者用の予約管理画面（拡張版）"""
    # ページネーション
    page = request.args.get('page', 1, type=int)
    
    # 予約一覧を取得（最新の予約が先頭に来るようにソート）
    pagination = Reservation.query.order_by(Reservation.reservation_date.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    reservations = pagination.items
    
    # 統計情報
    stats = {
        'pending': Reservation.query.filter_by(status='pending').count(),
        'notified': Reservation.query.filter_by(status='notified').count(),
        'completed': Reservation.query.filter_by(status='completed').count(),
        'cancelled': Reservation.query.filter_by(status='cancelled').count()
    }
    
    return render_template('reservations/admin.html', 
                          title='予約管理',
                          reservations=reservations, 
                          pagination=pagination, 
                          stats=stats)

@reservations_bp.route('/book/<int:book_id>')
@login_required
@admin_required
def book_reservations(book_id):
    """書籍の予約一覧を表示"""
    book = Book.query.get_or_404(book_id)
    reservations = get_active_reservations_for_book(book_id)
    
    return render_template('reservations/book.html', 
                          title=f'予約一覧: {book.title}', 
                          book=book,
                          reservations=reservations)

@reservations_bp.route('/create/<int:book_id>', methods=['POST'])
@login_required
def create(book_id):
    """書籍の予約を作成"""
    book = Book.query.get_or_404(book_id)
    
    # 既に貸出可能な場合は予約不要
    if book.is_available:
        flash('この本は現在貸出可能です。予約せずに借りることができます。', 'info')
        return redirect(url_for('books.detail', id=book_id))
    
    # 予約可能かチェック（例: 最大予約数など）
    max_reservations = 5  # 一人あたりの最大予約数
    current_reservations = get_user_reservation_count(current_user.id)
    
    if current_reservations >= max_reservations:
        flash(f'予約は最大{max_reservations}冊までです。他の予約をキャンセルしてください。', 'danger')
        return redirect(url_for('books.detail', id=book_id))
    
    try:
        reservation = create_reservation(book_id, current_user.id)
        
        # 操作ログの記録
        create_user_operation_log(
            current_user.id, 
            'create', 
            '予約', 
            f'"{book.title}"を予約しました', 
            request.remote_addr
        )
        
        flash(f'"{book.title}"を予約しました。利用可能になり次第メールでお知らせします。', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    
    return redirect(url_for('books.detail', id=book_id))

@reservations_bp.route('/notify/<int:reservation_id>', methods=['POST'])
@login_required
@admin_required
def notify_user(reservation_id):
    """予約通知処理"""
    reservation = Reservation.query.get_or_404(reservation_id)
    
    # 予約状態が「予約中」の場合のみ通知可能
    if reservation.status != 'pending':
        flash('この予約は既に処理されています。', 'warning')
        return redirect(url_for('reservations.admin'))
    
    # 通知済みでない場合のみ通知処理
    if not reservation.notification_sent:
        reservation.notification_sent = True
        reservation.status = 'notified'
        
        # ここに実際のメール通知処理を実装
        # ...
        
        # 操作ログを記録
        create_user_operation_log(
            current_user.id,
            'notify',
            '予約',
            f'書籍「{reservation.book.title}」の予約通知をユーザー「{reservation.user.name}」に送信',
            request.remote_addr
        )
        
        db.session.commit()
        flash(f'ユーザー {reservation.user.name} に予約の準備ができた旨を通知しました。', 'success')
    else:
        flash('この予約には既に通知が送信されています。', 'info')
    
    return redirect(url_for('reservations.admin'))

@reservations_bp.route('/complete/<int:reservation_id>', methods=['POST'])
@login_required
@admin_required
def mark_completed(reservation_id):
    """予約完了処理"""
    reservation = Reservation.query.get_or_404(reservation_id)
    
    # 予約状態が「キャンセル」「完了」以外の場合のみ完了処理可能
    if reservation.status in ['cancelled', 'completed']:
        flash('この予約は既に処理されています。', 'warning')
        return redirect(url_for('reservations.admin'))
    
    reservation.status = 'completed'
    
    # 操作ログを記録
    create_user_operation_log(
        current_user.id,
        'complete',
        '予約',
        f'書籍「{reservation.book.title}」の予約をユーザー「{reservation.user.name}」に対して完了処理',
        request.remote_addr
    )
    
    db.session.commit()
    flash('予約を完了としてマークしました。', 'success')
    return redirect(url_for('reservations.admin'))

@reservations_bp.route('/cancel/<int:reservation_id>', methods=['POST'])
@login_required
def cancel(reservation_id):
    """予約キャンセル処理"""
    reservation = get_reservation_by_id(reservation_id)
    if not reservation:
        flash('指定された予約が見つかりません。', 'danger')
        return redirect(url_for('reservations.index'))
    
    # 管理者でない場合、自分の予約のみキャンセル可能
    if not current_user.is_admin and reservation.user_id != current_user.id:
        flash('この予約をキャンセルする権限がありません。', 'danger')
        return redirect(url_for('reservations.index'))
    
    try:
        book = Book.query.get(reservation.book_id)
        cancel_reservation_service(reservation_id, current_user.id)
        
        # 操作ログの記録
        create_user_operation_log(
            current_user.id,
            'cancel',
            '予約',
            f'書籍「{book.title}」の予約をキャンセルしました',
            request.remote_addr
        )
        
        flash('予約をキャンセルしました。', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    
    # 管理者の場合は管理画面に戻る
    if current_user.is_admin and request.args.get('admin'):
        return redirect(url_for('reservations.admin'))
    
    return redirect(url_for('reservations.index'))