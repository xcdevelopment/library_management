# routes/books.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import or_
from werkzeug.utils import secure_filename
import csv
import os
from datetime import datetime
import chardet

from models import Book, LoanHistory, Reservation, OperationLog, db, User, ReservationStatus, BookStatus
from services.book_service import borrow_book, return_book, reserve_book, cancel_reservation
from forms.search import SearchForm
from forms.book import BookForm, CATEGORIES

books_bp = Blueprint('books', __name__, url_prefix='/books')

# CSVアップロード用の設定
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}

# アップロードディレクトリの作成
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@books_bp.route('/')
@login_required
def index():
    """書籍一覧を表示"""
    form = SearchForm(request.args)  # request.argsからフォームを初期化
    
    # 第2分類の選択肢を動的に更新
    if form.category1.data:
        category2_choices = CATEGORIES.get(form.category1.data, [])
        form.category2.choices = [('', '選択してください')] + category2_choices
    
    query = Book.query
    
    # キーワード検索
    if form.keyword.data:
        query = query.filter(
            or_(
                Book.title.ilike(f'%{form.keyword.data}%'),
                Book.author.ilike(f'%{form.keyword.data}%'),
                Book.keywords.ilike(f'%{form.keyword.data}%')
            )
        )
    
    # 分類での絞り込み
    if form.category1.data and form.category1.data != '':
        query = query.filter(Book.category1 == form.category1.data)
        
        if form.category2.data and form.category2.data != '':
            query = query.filter(Book.category2 == form.category2.data)
    
    # 並び替え
    query = query.order_by(Book.title)
    
    books = query.all()
    return render_template('books/index.html', books=books, form=form, categories=CATEGORIES)

@books_bp.route('/book/<int:book_id>')
@login_required
def book_detail(book_id):
    """書籍の詳細を表示"""
    book = Book.query.get_or_404(book_id)
    
    # 現在の予約状況
    reservations = Reservation.query.filter_by(
        book_id=book.id,
        status='pending'
    ).order_by(Reservation.reservation_date).all()
    
    # 貸出履歴
    history = LoanHistory.query.filter_by(book_id=book.id).order_by(LoanHistory.loan_date.desc()).all()
    
    # 自分の予約状況
    user_reservation = Reservation.query.filter_by(
        book_id=book.id,
        user_id=current_user.id,
        status='pending'
    ).first()
    
    return render_template(
        'books/detail.html',
        book=book,
        reservations=reservations,
        history=history,
        user_reservation=user_reservation
    )

@books_bp.route('/book/borrow/<int:book_id>', methods=['POST'])
@login_required
def borrow(book_id):
    """書籍を借りる処理"""
    success, result = borrow_book(book_id, current_user.id)
    
    if success:
        flash('書籍を借りました。', 'success')
        
        # 操作ログの記録
        log = OperationLog(
            user_id=current_user.id,
            action='borrow_book',
            target=f'Book {book_id}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
    else:
        flash(result, 'danger')
    
    return redirect(url_for('books.book_detail', book_id=book_id))

@books_bp.route('/book/return/<int:book_id>', methods=['POST'])
@login_required
def return_book_route(book_id):
    """書籍を返却する処理"""
    book = Book.query.get_or_404(book_id)
    
    # 返却処理
    if book.borrower_id != current_user.id and not current_user.is_admin:
        flash('この本を返却する権限がありません。', 'danger')
        return redirect(url_for('books.book_detail', book_id=book_id))
    
    # 現在の貸出記録を取得
    loan = book.current_loan
    if not loan:
        flash('この本は既に返却されています。', 'warning')
        return redirect(url_for('books.book_detail', book_id=book_id))
    
    # 返却日時を設定
    loan.return_date = datetime.utcnow()
    
    # 書籍の状態を更新
    book.status = BookStatus.AVAILABLE
    book.is_available = True
    book.borrower_id = None
    
    # 予約者への通知
    next_reservation = Reservation.query.filter_by(
        book_id=book_id,
        status=ReservationStatus.PENDING
    ).order_by(Reservation.reservation_date).first()
    
    if next_reservation:
        # 予約者のステータスを更新
        next_reservation.status = ReservationStatus.NOTIFIED
        next_reservation.notification_sent = True
        
        # メール通知を一時的に無効化
        # send_book_available_notification(next_reservation.user, book)
        
        # 書籍の状態を予約済みに更新
        book.status = BookStatus.RESERVED
    
    # 操作ログの記録
    log = OperationLog(
        user_id=current_user.id,
        action='return_book',
        target=f'Book {book_id}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    flash('書籍を返却しました。', 'success')
    return redirect(url_for('books.book_detail', book_id=book_id))

@books_bp.route('/book/reserve/<int:book_id>', methods=['POST'])
@login_required
def reserve(book_id):
    """書籍を予約する処理"""
    success, result = reserve_book(book_id, current_user.id)
    
    if success:
        flash(result, 'success')
        
        # 操作ログの記録
        log = OperationLog(
            user_id=current_user.id,
            action='reserve_book',
            target=f'Book {book_id}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
    else:
        flash(result, 'danger')
    
    return redirect(url_for('books.book_detail', book_id=book_id))

@books_bp.route('/reservation/cancel/<int:reservation_id>', methods=['POST'])
@login_required
def cancel(reservation_id):
    """予約をキャンセルする処理"""
    reservation = Reservation.query.get_or_404(reservation_id)
    book_id = reservation.book_id
    
    success, result = cancel_reservation(reservation_id, current_user.id)
    
    if success:
        flash(result, 'success')
        
        # 操作ログの記録
        log = OperationLog(
            user_id=current_user.id,
            action='cancel_reservation',
            target=f'Reservation {reservation_id}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
    else:
        flash(result, 'danger')
    
    return redirect(url_for('books.book_detail', book_id=book_id))

@books_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """新規書籍を追加（管理者のみ）"""
    if not current_user.is_admin:
        flash('この機能は管理者のみ利用できます。', 'danger')
        return redirect(url_for('books.index'))
    
    form = BookForm()
    if form.validate_on_submit():
        book = Book(
            title=form.title.data,
            author=form.author.data,
            category1=form.category1.data,
            category2=form.category2.data,
            keywords=form.keywords.data,
            location=form.location.data
        )
        
        db.session.add(book)
        
        # 操作ログの記録
        log = OperationLog(
            user_id=current_user.id,
            action='add_book',
            target=f'Book: {book.title}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        flash('書籍が追加されました。', 'success')
        return redirect(url_for('books.index'))
        
    return render_template('books/add.html', form=form, categories=CATEGORIES)

@books_bp.route('/my/books')
@login_required
def my_books():
    """自分が借りている書籍一覧"""
    borrowed_books = Book.query.filter_by(borrower_id=current_user.id).all()
    
    # 自分の予約一覧
    reservations = Reservation.query.filter_by(
        user_id=current_user.id,
        status='pending'
    ).order_by(Reservation.reservation_date).all()
    
    return render_template('books/my_books.html', borrowed_books=borrowed_books, reservations=reservations)

@books_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_books():
    """書籍の一括インポート（管理者のみ）"""
    if not current_user.is_admin:
        flash('この機能は管理者のみ利用できます。', 'danger')
        return redirect(url_for('books.index'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('ファイルがアップロードされていません。', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('ファイルが選択されていません。', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            success_count = 0
            error_count = 0
            errors = []
            
            try:
                # ファイルの文字コードを自動判定
                with open(filepath, 'rb') as f:
                    raw_data = f.read()
                    result = chardet.detect(raw_data)
                    encoding = result['encoding']
                
                with open(filepath, 'r', encoding=encoding) as csvfile:
                    # 1行目を読んでヘッダーをチェック
                    first_line = csvfile.readline().strip()
                    if 'title' not in first_line.lower():
                        flash('CSVファイルに「title」列が含まれていません。', 'danger')
                        return redirect(request.url)
                    
                    # ファイルポインタを先頭に戻す
                    csvfile.seek(0)
                    reader = csv.DictReader(csvfile)
                    
                    # ヘッダーの存在確認
                    required_headers = ['title']
                    missing_headers = [h for h in required_headers if h not in reader.fieldnames]
                    if missing_headers:
                        flash(f'必須列が不足しています: {", ".join(missing_headers)}', 'danger')
                        return redirect(request.url)
                    
                    for row_num, row in enumerate(reader, start=2):  # ヘッダー行を除くため2から開始
                        try:
                            # 必須フィールドのチェック
                            if not row.get('title'):
                                errors.append(f'行 {row_num}: タイトルが入力されていません')
                                error_count += 1
                                continue
                            
                            # データの作成
                            book = Book(
                                title=row['title'].strip(),
                                author=row.get('author', '').strip(),
                                category1=row.get('category1', '').strip(),
                                category2=row.get('category2', '').strip(),
                                keywords=row.get('keywords', '').strip(),
                                location=row.get('location', '').strip()
                            )
                            db.session.add(book)
                            success_count += 1
                            
                            # 100件ごとにコミット
                            if success_count % 100 == 0:
                                db.session.commit()
                                
                        except Exception as e:
                            error_count += 1
                            errors.append(f'行 {row_num}: {str(e)}')
                    
                    # 残りのデータをコミット
                    db.session.commit()
                    
                    # 操作ログの記録
                    log = OperationLog(
                        user_id=current_user.id,
                        action='import_books',
                        target=f'Imported {success_count} books',
                        details=f'Success: {success_count}, Errors: {error_count}',
                        ip_address=request.remote_addr
                    )
                    db.session.add(log)
                    db.session.commit()
                    
                    if success_count > 0:
                        flash(f'{success_count}件の書籍を登録しました。', 'success')
                    if error_count > 0:
                        flash(f'{error_count}件の登録に失敗しました。', 'warning')
                        for error in errors[:10]:  # 最初の10件のエラーのみ表示
                            flash(error, 'danger')
                        if len(errors) > 10:
                            flash(f'他 {len(errors) - 10} 件のエラーがあります。', 'warning')
            
            except Exception as e:
                db.session.rollback()
                flash(f'CSVファイルの処理中にエラーが発生しました: {str(e)}', 'danger')
                app.logger.error(f'CSV import error: {str(e)}')
            
            finally:
                # アップロードされたファイルを削除
                if os.path.exists(filepath):
                    os.remove(filepath)
            
            return redirect(url_for('books.index'))
        
        flash('許可されていないファイル形式です。CSVファイルをアップロードしてください。', 'danger')
        return redirect(request.url)
    
    return render_template('books/import.html')