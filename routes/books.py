# routes/books.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_
from werkzeug.utils import secure_filename
import csv
import os
from datetime import datetime, timedelta
import chardet
import requests

from models import Book, LoanHistory, Reservation, OperationLog, db, User, ReservationStatus, BookStatus
from services.book_service import borrow_book, return_book, reserve_book, cancel_reservation, create_book_with_auto_number, update_book_status
from services.loan_service import LoanService
from services.slack_service import send_slack_dm_to_user
from forms.search import SearchForm
from forms.book import BookForm, CATEGORIES
from forms.book_forms import BorrowForm, ExtendLoanForm

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
        status=ReservationStatus.PENDING
    ).order_by(Reservation.reservation_date).all()
    
    # 貸出履歴
    history = LoanHistory.query.filter_by(book_id=book.id).order_by(LoanHistory.loan_date.desc()).all()
    
    # 自分の予約状況
    user_reservation = Reservation.query.filter_by(
        book_id=book.id,
        user_id=current_user.id,
        status=ReservationStatus.PENDING
    ).first()
    
    return render_template(
        'books/detail.html',
        book=book,
        reservations=reservations,
        history=history,
        user_reservation=user_reservation
    )

@books_bp.route('/book/borrow/<int:book_id>', methods=['GET', 'POST'])
@login_required
def borrow(book_id):
    """書籍を借りる処理"""
    book = Book.query.get_or_404(book_id)
    form = BorrowForm()
    
    if form.validate_on_submit():
        # 返却期限を計算
        due_date = None
        if form.due_date_option.data == 'today':
            due_date = datetime.utcnow()
        elif form.due_date_option.data == '1week':
            due_date = datetime.utcnow() + timedelta(weeks=1)
        elif form.due_date_option.data == '2weeks':
            due_date = datetime.utcnow() + timedelta(weeks=2)
        elif form.due_date_option.data == 'custom' and form.custom_due_date.data:
            due_date = datetime.combine(form.custom_due_date.data, datetime.min.time())
        
        success, result = borrow_book(book_id, current_user.id, due_date)
        
        if success:
            flash('本を借りました。', 'success')
            
            # 貸出記録を取得
            loan = LoanHistory.query.filter_by(
                book_id=book_id,
                borrower_id=current_user.id,
                return_date=None
            ).first()
            
            # Slack通知を送信
            if loan and loan.book:
                book_url = f"http://localhost/books/book/{book_id}"
                message = (
                    f"図書管理アプリです！以下の本の貸出がされました。\n"
                    f"書籍：<{book_url}|{loan.book.title}>\n"
                    f"返却期限：{loan.due_date.strftime('%Y-%m-%d')}\n\n"
                    f"返却期限を守り、書籍は元の場所へ返却するようお願いいたします。"
                )
                # 貸し出した本人にDMを送信
                send_slack_dm_to_user(current_user, message)
            
            # 書籍の状態を更新
            book = Book.query.get(book_id)
            update_book_status(book)
            
            # 操作ログの記録
            log = OperationLog(
                user_id=current_user.id,
                action='borrow_book',
                target=f'Book {book_id}',
                ip_address=request.remote_addr
            )
            db.session.add(log)
            db.session.commit()
            
            return redirect(url_for('books.book_detail', book_id=book_id))
        else:
            flash(result, 'danger')
    
    # 貸出可能性チェック
    can_borrow, error_msg = LoanService.can_user_borrow_book(current_user.id, book_id)
    
    return render_template('books/borrow.html', book=book, form=form, can_borrow=can_borrow, error_msg=error_msg)

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
    
    # Slack通知 (返却)
    book_url = f"http://localhost/books/book/{book_id}"
    return_message = (
        f"図書管理アプリです！以下の本が返却されました。\n"
        f"書籍：<{book_url}|{book.title}>\n"
        f"返却者：{current_user.name}\n\n"
        f"ご利用ありがとうございました。"
    )
    # 返却した本人にDMを送信
    send_slack_dm_to_user(current_user, return_message)

    # 返却日時を設定
    loan.return_date = datetime.utcnow()
    db.session.commit()  # まず返却日を保存
    
    # 書籍の状態を適切に更新（予約状況も考慮）
    update_book_status(book)
    
    # 予約者への通知
    next_reservation = Reservation.query.filter_by(
        book_id=book_id,
        status=ReservationStatus.PENDING
    ).order_by(Reservation.reservation_date).first()
    
    if next_reservation:
        # 予約者のステータスを更新
        next_reservation.status = ReservationStatus.NOTIFIED
        next_reservation.notification_sent_at = datetime.utcnow()
        next_reservation.notification_sent = True
        
        # Slack通知 (予約者に利用可能)
        book_url = f"http://localhost/books/book/{book_id}"
        reservation_message = (
            f"図書管理アプリです！ご予約の本がご用意できました。\n"
            f"書籍：<{book_url}|{book.title}>\n"
            f"貸出期限：{(datetime.utcnow() + timedelta(days=7)).strftime('%Y-%m-%d')}\n\n"
            f"期限までに貸出手続きをお願いいたします。"
        )
        # 予約者にDMを送信
        send_slack_dm_to_user(next_reservation.user, reservation_message)
        flash(f'{next_reservation.user.name} さんに予約書籍が利用可能になったことを通知しました。', 'info')
        
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
        book = Book.query.get_or_404(book_id)
        book_url = f"http://localhost/books/book/{book_id}"
        message = (
            f"図書管理アプリです！以下の本を予約しました。\n"
            f"書籍：<{book_url}|{book.title}>\n\n"
            f"貸出可能になりましたら、改めてご連絡します。"
        )
        # 予約した本人にDMを送信
        send_slack_dm_to_user(current_user, message)
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
        book_url = f"http://localhost/books/book/{book_id}"
        message = (
            f"図書管理アプリです！以下の本の予約をキャンセルしました。\n"
            f"書籍：<{book_url}|{reservation.book.title}>"
        )
        # キャンセルした本人にDMを送信
        send_slack_dm_to_user(current_user, message)
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
    form.populate_location_choices()  # 場所の選択肢を設定
    
    # POSTリクエストでフォーム送信時に選択肢を再設定
    if request.method == 'POST':
        if form.category1.data:
            form.populate_category2_choices(form.category1.data)
    
    if form.validate_on_submit():
        # 自動管理番号とカテゴリベース自動ロケーション機能を使用
        book = create_book_with_auto_number(
            title=form.title.data,
            author=form.author.data,
            category1=form.category1.data,
            category2=form.category2.data,
            keywords=form.keywords.data,
            location=form.location.data
        )
        
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
        status=ReservationStatus.PENDING
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
            books_to_add = []
            
            try:
                # ファイルの文字コードを自動判定
                with open(filepath, 'rb') as f:
                    raw_data = f.read()
                    result = chardet.detect(raw_data)
                    encoding = result['encoding'] if result['encoding'] else 'utf-8'
                
                with open(filepath, 'r', encoding=encoding, newline='') as csvfile:
                    reader = csv.DictReader(csvfile)
                    
                    # ヘッダーの正規化と存在確認
                    reader.fieldnames = [h.lower().strip() for h in reader.fieldnames]
                    required_headers = ['title']
                    if not all(h in reader.fieldnames for h in required_headers):
                        missing_headers = [h for h in required_headers if h not in reader.fieldnames]
                        flash(f'必須列が不足しています: {", ".join(missing_headers)}', 'danger')
                        return redirect(request.url)
                    
                    for row_num, row in enumerate(reader, start=2):
                        try:
                            title = row.get('title', '').strip()
                            if not title:
                                errors.append(f'行 {row_num}: title は必須です。')
                                error_count += 1
                                continue
                            
                            # 書籍の重複をチェック（タイトルと著者で簡易的に）
                            author = row.get('author', '').strip()
                            if Book.query.filter_by(title=title, author=author).first():
                                errors.append(f'行 {row_num}: 既に同じ書籍（タイトルと著者が一致）が存在します: {title}')
                                error_count += 1
                                continue

                            # 場所の妥当性チェック
                            location = row.get('location', '').strip()
                            category1 = row.get('category1', '').strip()
                            
                            if location and category1:
                                # 指定されたカテゴリに対して設定されている場所かチェック
                                from models import CategoryLocationMapping
                                valid_location = CategoryLocationMapping.query.filter_by(
                                    category1=category1, 
                                    default_location=location
                                ).first()
                                
                                if not valid_location:
                                    # このカテゴリで使用可能な場所を取得
                                    available_locations = CategoryLocationMapping.query.filter_by(
                                        category1=category1
                                    ).all()
                                    if available_locations:
                                        location_list = [loc.default_location for loc in available_locations]
                                        errors.append(f'行 {row_num}: カテゴリ「{category1}」には場所「{location}」は設定されていません。使用可能な場所: {", ".join(location_list)}')
                                    else:
                                        errors.append(f'行 {row_num}: カテゴリ「{category1}」には場所が設定されていません。')
                                    error_count += 1
                                    continue

                            # CSVインポート用: 書籍オブジェクトを準備（自動番号は後で一括生成）
                            book_data = {
                                'title': title,
                                'author': author,
                                'category1': category1,
                                'category2': row.get('category2', '').strip(),
                                'keywords': row.get('keywords', '').strip(),
                                'location': location
                            }
                            books_to_add.append(book_data)
                            
                        except Exception as e:
                            error_count += 1
                            errors.append(f'行 {row_num} の処理中に予期せぬエラー: {str(e)}')

                # エラーがある場合はインポート処理を中断
                if error_count > 0:
                    flash('CSVファイル内にエラーが検出されたため、インポートを中断しました。', 'danger')
                    for error in errors[:10]:
                        flash(error, 'danger')
                    if len(errors) > 10:
                        flash(f'他 {len(errors) - 10} 件のエラーがあります。', 'warning')
                    return redirect(url_for('books.import_books'))

                # エラーがなければ一括でコミット（自動番号生成付き）
                if books_to_add:
                    created_books = []
                    for book_data in books_to_add:
                        book = create_book_with_auto_number(**book_data)
                        created_books.append(book)
                    success_count = len(created_books)
                    
                    # 操作ログの記録
                    log = OperationLog(
                        user_id=current_user.id,
                        action='import_books',
                        target=f'Imported {success_count} books',
                        ip_address=request.remote_addr
                    )
                    db.session.add(log)
                    db.session.commit()
                    
                    flash(f'{success_count}件の書籍を正常に登録しました。', 'success')

            except Exception as e:
                db.session.rollback()
                flash(f'CSVファイルの処理中に予期せぬエラーが発生しました: {str(e)}', 'danger')
                current_app.logger.error(f'CSV import error: {str(e)}')
            
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)
            
            return redirect(url_for('books.index'))
        
        flash('許可されていないファイル形式です。CSVファイルをアップロードしてください。', 'danger')
        return redirect(request.url)
    
    return render_template('books/import.html')

def send_webhook_notification(loan_info):
    """Power AutomateのWebhookに通知を送信する"""
    webhook_url = current_app.config.get('POWER_AUTOMATE_WEBHOOK_URL')
    if not webhook_url:
        current_app.logger.error("環境変数 'POWER_AUTOMATE_WEBHOOK_URL' が設定されていません。")
        return

    headers = {'Content-Type': 'application/json'}
    payload = {
        'book_title': loan_info.book.title,
        'borrower_name': loan_info.borrower.name,
        'borrower_email': loan_info.borrower.email,
        'loan_date': loan_info.loan_date.isoformat() + 'Z',
        'due_date': loan_info.due_date.isoformat() + 'Z' if loan_info.due_date else None,
    }

    try:
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()  # 2xx以外はエラーを発生させる
        current_app.logger.info(f"Webhook通知を送信しました: {response.status_code}")
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Webhookの送信に失敗しました: {e}")

@books_bp.route('/edit/<int:book_id>', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    """書籍情報を編集する (管理者のみ)"""
    if not current_user.is_admin:
        flash('この操作は管理者のみ許可されています。', 'danger')
        return redirect(url_for('books.index'))

    book = Book.query.get_or_404(book_id)
    form = BookForm(obj=book)
    
    # 既存データに基づいて選択肢を設定
    form.populate_location_choices()
    if book.category1:
        form.populate_category2_choices(book.category1)
    
    # POSTリクエストでフォーム送信時に選択肢を再設定
    if request.method == 'POST':
        if form.category1.data:
            form.populate_category2_choices(form.category1.data)

    if form.validate_on_submit():
        form.populate_obj(book)
        db.session.commit()
        
        log = OperationLog(
            user_id=current_user.id,
            action='edit_book',
            target=f'Book {book.id}: {book.title}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        flash('書籍情報が更新されました。', 'success')
        return redirect(url_for('books.book_detail', book_id=book.id))

    return render_template('books/edit.html', form=form, book=book)

@books_bp.route('/loan/extend/<int:loan_id>', methods=['GET', 'POST'])
@login_required
def extend_loan(loan_id):
    """貸出期間を延長する"""
    loan = LoanHistory.query.get_or_404(loan_id)
    
    # 権限チェック
    if loan.borrower_id != current_user.id and not current_user.is_admin:
        flash('この貸出記録を延長する権限がありません。', 'danger')
        return redirect(url_for('books.my_books'))
    
    # 既に返却済みかチェック
    if loan.return_date:
        flash('この本は既に返却されています。', 'warning')
        return redirect(url_for('books.my_books'))
    
    form = ExtendLoanForm()
    
    if form.validate_on_submit():
        extension_weeks = int(form.extension_period.data)
        success, message = LoanService.extend_loan(loan_id, extension_weeks)
        
        if success:
            flash(message, 'success')
            
            # Slack通知
            book_url = f"http://localhost/books/book/{loan.book_id}"
            slack_message = (
                f"図書管理アプリです！貸出期間が延長されました。\n"
                f"書籍：<{book_url}|{loan.book.title}>\n"
                f"新しい返却期限：{loan.due_date.strftime('%Y-%m-%d')}\n\n"
                f"返却期限を守り、返却の際、本は自分で戻してください。"
            )
            send_slack_dm_to_user(current_user, slack_message)
            
            # 操作ログの記録
            log = OperationLog(
                user_id=current_user.id,
                action='extend_loan',
                target=f'Loan {loan_id}',
                ip_address=request.remote_addr
            )
            db.session.add(log)
            db.session.commit()
            
            return redirect(url_for('books.my_books'))
        else:
            flash(message, 'danger')
    
    # 延長可能性チェック
    can_extend = loan.can_extend()
    error_msg = ""
    if not can_extend:
        if loan.extension_count >= 1:
            error_msg = "既に延長回数の上限(1回)に達しています。"
        else:
            active_reservations = [r for r in loan.book.reservations if r.status == ReservationStatus.PENDING]
            if active_reservations:
                error_msg = "この本には予約者がいるため延長できません。"
    
    return render_template('books/extend_loan.html', 
                         loan=loan, 
                         form=form, 
                         can_extend=can_extend, 
                         error_msg=error_msg)

@books_bp.route('/loans/due-soon')
@login_required
def loans_due_soon():
    """返却期限が近い貸出一覧（管理者用）"""
    if not current_user.is_admin:
        flash('この機能は管理者のみ利用できます。', 'danger')
        return redirect(url_for('books.index'))
    
    due_soon_loans = LoanService.get_due_soon_loans(days=3)
    overdue_loans = LoanService.get_overdue_loans()
    
    return render_template('admin/loans_status.html', 
                         due_soon_loans=due_soon_loans, 
                         overdue_loans=overdue_loans)