# routes/books.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename

from models import Book, LoanHistory, db, Reservation
from services.book_service import (
    get_books, get_book_by_id, create_book, update_book,
    checkout_book, return_book, import_books_from_csv
)
from services.auth_service import create_user_operation_log
from utils.forms import BookForm, BookSearchForm, BookImportForm
from utils.decorators import admin_required

books_bp = Blueprint('books', __name__, url_prefix='/books')

@books_bp.route('/')
@login_required
def index():
    """書籍一覧表示"""
    form = BookSearchForm(request.args)
    
    # 検索条件の取得
    keyword = request.args.get('keyword', '')
    is_available = request.args.get('is_available', '')
    category1 = request.args.get('category1', '')
    category2 = request.args.get('category2', '')
    
    # 書籍の取得（検索条件付き）
    books = get_books(keyword, is_available, category1, category2)
    
    # カテゴリのリストを取得してフォームに渡す
    categories1 = db.session.query(Book.category1).distinct().all()
    categories2 = db.session.query(Book.category2).distinct().all()
    form.category1.choices = [('', '全て')] + [(c[0], c[0]) for c in categories1 if c[0]]
    form.category2.choices = [('', '全て')] + [(c[0], c[0]) for c in categories2 if c[0]]
    
    return render_template('books/index.html', 
                          title='書籍一覧', 
                          books=books, 
                          form=form,
                          is_admin=current_user.is_admin)

@books_bp.route('/<int:id>')
@login_required
def detail(id):
    """書籍詳細表示"""
    book = get_book_by_id(id)
    if not book:
        flash('指定された書籍が見つかりません。', 'danger')
        return redirect(url_for('books.index'))
    
    # 貸出履歴を取得
    history = LoanHistory.query.filter_by(book_id=id).order_by(LoanHistory.loan_date.desc()).all()
    
    # 予約情報を取得
    reservations = Reservation.query.filter(
        Reservation.book_id == id,
        Reservation.status.in_(['pending', 'notified'])
    ).order_by(Reservation.reservation_date).all()
    
    # ユーザーの予約情報を取得
    user_reservation = Reservation.query.filter(
        Reservation.book_id == id,
        Reservation.user_id == current_user.id,
        Reservation.status.in_(['pending', 'notified'])
    ).first()
    
    return render_template('books/detail.html', 
                          title=book.title, 
                          book=book, 
                          history=history,
                          reservations=reservations,
                          user_reservation=user_reservation,
                          timedelta=timedelta,
                          is_admin=current_user.is_admin)

@books_bp.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add():
    """書籍追加"""
    form = BookForm()
    if form.validate_on_submit():
        book = Book(
            title=form.title.data,
            author=form.author.data,
            category1=form.category1.data,
            category2=form.category2.data,
            keywords=form.keywords.data,
            location=form.location.data,
            is_available=form.is_available.data
        )
        db.session.add(book)
        db.session.commit()
        
        # 操作ログの記録
        create_user_operation_log(
            current_user.id, 
            'create', 
            '書籍', 
            f'"{book.title}"を登録しました', 
            request.remote_addr
        )
        
        flash(f'"{book.title}"を登録しました。', 'success')
        return redirect(url_for('books.index'))
    
    return render_template('books/add.html', title='書籍登録', form=form)

@books_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(id):
    """書籍編集"""
    book = get_book_by_id(id)
    if not book:
        flash('指定された書籍が見つかりません。', 'danger')
        return redirect(url_for('books.index'))
    
    form = BookForm(obj=book)
    if form.validate_on_submit():
        update_book(
            book,
            title=form.title.data,
            author=form.author.data,
            category1=form.category1.data,
            category2=form.category2.data,
            keywords=form.keywords.data,
            location=form.location.data
        )
        
        # 操作ログの記録
        create_user_operation_log(
            current_user.id, 
            'update', 
            '書籍', 
            f'"{book.title}"を更新しました', 
            request.remote_addr
        )
        
        flash(f'"{book.title}"を更新しました。', 'success')
        return redirect(url_for('books.detail', id=book.id))
    
    return render_template('books/edit.html', title=f'編集: {book.title}', form=form, book=book)

@books_bp.route('/checkout/<int:id>', methods=['POST'])
@login_required
def checkout(id):
    """書籍貸出処理"""
    book = get_book_by_id(id)
    if not book:
        flash('指定された書籍が見つかりません。', 'danger')
        return redirect(url_for('books.index'))
    
    if not book.is_available:
        flash('この書籍は現在貸出できません。', 'danger')
        return redirect(url_for('books.detail', id=id))
    
    # 貸出処理
    checkout_book(book, current_user.id)
    
    # 操作ログの記録
    create_user_operation_log(
        current_user.id, 
        'checkout', 
        '書籍', 
        f'"{book.title}"を借りました', 
        request.remote_addr
    )
    
    flash(f'"{book.title}"を借りました。', 'success')
    return redirect(url_for('books.detail', id=id))

@books_bp.route('/return/<int:id>', methods=['POST'])
@login_required
def return_book_route(id):
    """書籍返却処理"""
    book = get_book_by_id(id)
    if not book:
        flash('指定された書籍が見つかりません。', 'danger')
        return redirect(url_for('books.index'))
    
    if book.is_available:
        flash('この書籍は既に返却されています。', 'warning')
        return redirect(url_for('books.detail', id=id))
    
    # 現在のユーザーが借りていない場合（管理者以外）
    if not current_user.is_admin and book.borrower_id != current_user.id:
        flash('あなたが借りていない書籍は返却できません。', 'danger')
        return redirect(url_for('books.detail', id=id))
    
    # 返却処理
    return_book(book)
    
    # 操作ログの記録
    create_user_operation_log(
        current_user.id, 
        'return', 
        '書籍', 
        f'"{book.title}"を返却しました', 
        request.remote_addr
    )
    
    flash(f'"{book.title}"を返却しました。', 'success')
    return redirect(url_for('books.detail', id=id))

@books_bp.route('/import', methods=['GET', 'POST'])
@login_required
@admin_required
def import_books():
    """書籍一括インポート"""
    form = BookImportForm()
    if form.validate_on_submit():
        if not form.file.data:
            flash('ファイルが選択されていません', 'error')
            return redirect(request.url)
        
        file = form.file.data
        if not file.filename.endswith('.csv'):
            flash('CSVファイルを選択してください', 'error')
            return redirect(request.url)
        
        # ファイルを一時保存
        filename = secure_filename(f'import_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        file.save(filepath)
        
        try:
            # CSVからインポート
            imported_count = import_books_from_csv(filepath)
            flash(f'{imported_count}件の書籍をインポートしました', 'success')
            
        except Exception as e:
            flash(f'インポート中にエラーが発生しました: {str(e)}', 'error')
            
        finally:
            # 一時ファイルを削除
            if os.path.exists(filepath):
                os.remove(filepath)
        
        return redirect(url_for('books.index'))
    
    return render_template('books/import.html', title='書籍一括インポート', form=form)

@books_bp.route('/cancel_reservation/<int:reservation_id>', methods=['POST'])
@login_required
def cancel_reservation(reservation_id):
    """予約をキャンセル"""
    reservation = Reservation.query.get_or_404(reservation_id)
    
    if reservation.user_id != current_user.id:
        flash('この予約はキャンセルできません。', 'danger')
        return redirect(url_for('users.mypage'))
    
    if reservation.status not in ['pending', 'notified']:
        flash('この予約はキャンセルできません。', 'danger')
        return redirect(url_for('users.mypage'))
    
    reservation.status = 'cancelled'
    db.session.commit()
    
    # 操作ログを記録
    create_user_operation_log(
        user_id=current_user.id,
        action='cancel_reservation',
        target='reservation',
        details=f'Cancelled reservation for book: {reservation.book.title}',
        ip_address=request.remote_addr
    )
    
    flash('予約をキャンセルしました。', 'success')
    return redirect(url_for('users.mypage'))

@books_bp.route('/borrow_reserved/<int:reservation_id>', methods=['POST'])
@login_required
def borrow_reserved(reservation_id):
    """予約した本を借りる"""
    reservation = Reservation.query.get_or_404(reservation_id)
    
    if reservation.user_id != current_user.id:
        flash('この予約の本は借りられません。', 'danger')
        return redirect(url_for('users.mypage'))
    
    if reservation.status != 'notified':
        flash('この本はまだ借りられません。', 'danger')
        return redirect(url_for('users.mypage'))
    
    book = reservation.book
    if not book.is_available:
        flash('この本は現在貸出できません。', 'danger')
        return redirect(url_for('users.mypage'))
    
    # 本を借りる
    book.is_available = False
    book.borrower_id = current_user.id
    
    # 貸出履歴を作成
    loan_history = LoanHistory(
        book_id=book.id,
        book_title=book.title,
        borrower_id=current_user.id,
        loan_date=datetime.utcnow(),
        due_date=datetime.utcnow() + timedelta(days=14)
    )
    db.session.add(loan_history)
    
    # 予約を完了状態に
    reservation.status = 'completed'
    
    db.session.commit()
    
    # 操作ログを記録
    create_user_operation_log(
        user_id=current_user.id,
        action='borrow_reserved',
        target='book',
        details=f'Borrowed reserved book: {book.title}',
        ip_address=request.remote_addr
    )
    
    flash('本を借りました。', 'success')
    return redirect(url_for('users.mypage'))