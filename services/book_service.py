# services/book_service.py
from datetime import datetime, timedelta
from models import db, Book, LoanHistory, Reservation, OperationLog, User, CategoryLocationMapping, BookStatus
from flask import current_app
from sqlalchemy import func, desc
from .loan_service import LoanService

def borrow_book(book_id, user_id, due_date=None):
    """書籍を貸し出す処理（新しい制限ロジック使用）"""
    # 新しいLoanServiceを使用
    success, message, loan_history_id = LoanService.borrow_book(user_id, book_id, due_date)
    
    if success:
        loan_history = LoanHistory.query.get(loan_history_id)
        return True, loan_history
    else:
        return False, message

def return_book(book_id, user_id):
    """書籍を返却する処理（新しいロジック使用）"""
    # 該当する貸出履歴を取得
    loan_history = LoanHistory.query.filter_by(
        book_id=book_id, 
        borrower_id=user_id, 
        return_date=None
    ).order_by(LoanHistory.loan_date.desc()).first()
    
    if not loan_history:
        return False, "この書籍の貸出履歴が見つかりません。"
    
    # 新しいLoanServiceを使用
    success, message = LoanService.return_book(loan_history.id)
    return success, message

def reserve_book(book_id, user_id):
    """書籍を予約する処理"""
    book = Book.query.get_or_404(book_id)
    user = User.query.get_or_404(user_id)
    
    # 貸出制限チェック（予約も貸出数に含まれる）
    can_borrow, error_msg = LoanService.can_user_borrow_book(user_id)
    if not can_borrow:
        return False, error_msg
    
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

def get_popular_books(limit=5, since=None):
    """人気の本を取得する（貸出回数順）"""
    if since is None:
        since = datetime.now() - timedelta(days=30)  # デフォルトは過去30日
    
    # 貸出回数でグループ化して人気順に並べる
    popular_books_query = db.session.query(
        Book,
        func.count(LoanHistory.id).label('loan_count')
    ).join(
        LoanHistory, Book.id == LoanHistory.book_id
    ).filter(
        LoanHistory.loan_date >= since
    ).group_by(
        Book.id
    ).order_by(
        desc('loan_count')
    ).limit(limit)
    
    result = []
    for book, loan_count in popular_books_query:
        book.loan_count = loan_count  # 動的にloan_countを追加
        result.append(book)
    
    return result

def generate_book_number(year=None):
    """自動管理番号を生成する（BO-yyyy-001形式）"""
    if year is None:
        year = datetime.now().year
    
    # 該当年の最大連番を取得
    prefix = f"BO-{year}-"
    last_book = Book.query.filter(
        Book.book_number.like(f"{prefix}%")
    ).order_by(
        Book.book_number.desc()
    ).first()
    
    if last_book and last_book.book_number:
        try:
            # 最後の3桁の番号を抽出
            last_number = int(last_book.book_number.split('-')[-1])
            next_number = last_number + 1
        except (ValueError, IndexError):
            next_number = 1
    else:
        next_number = 1
    
    return f"BO-{year}-{next_number:03d}"

def create_book_with_auto_number(title, author, category1=None, category2=None, 
                                keywords=None, location=None, **kwargs):
    """自動管理番号付きで書籍を作成する"""
    book_number = generate_book_number()
    
    book = Book(
        book_number=book_number,
        title=title,
        author=author,
        category1=category1,
        category2=category2,
        keywords=keywords,
        location=location,
        **kwargs
    )
    
    # カテゴリベースの自動ロケーション割り当て
    if not location and category1:
        book.location = get_location_for_category(category1)
    
    db.session.add(book)
    db.session.commit()
    
    current_app.logger.info(f"Book created with auto number: {book_number}")
    return book

def get_location_for_category(category):
    """カテゴリに基づいて自動的にロケーションを決定する"""
    # CategoryLocationMappingテーブルから自動割り当て設定を取得
    mapping = CategoryLocationMapping.query.filter_by(category1=category).first()
    if mapping:
        return mapping.default_location
    
    # デフォルトのマッピング
    category_mapping = {
        'プログラミング': 'A棚-1',
        'データベース': 'A棚-2', 
        'ネットワーク': 'A棚-3',
        'AI・機械学習': 'B棚-1',
        'ビジネス': 'C棚-1',
        '経営': 'C棚-2',
        'マーケティング': 'C棚-3',
        '自己啓発': 'D棚-1',
        '小説': 'E棚-1',
        'エッセイ': 'E棚-2',
        '歴史': 'F棚-1',
        '哲学': 'F棚-2',
        '科学': 'G棚-1',
        '数学': 'G棚-2',
    }
    
    return category_mapping.get(category, '未分類')

def release_book_from_reservation(book):
    """予約から本をリリースする（返却時やキャンセル時）"""
    # 次の予約待ちユーザーがいる場合の処理
    next_reservation = Reservation.query.filter_by(
        book_id=book.id,
        status='pending'
    ).order_by(Reservation.reservation_date).first()
    
    if next_reservation:
        # 予約待ちの最初のユーザーに通知
        next_reservation.status = 'notified'
        next_reservation.notification_sent_at = datetime.utcnow()
        book.status = BookStatus.RESERVED
    else:
        # 予約がない場合は利用可能にする
        book.status = BookStatus.AVAILABLE
    
    db.session.commit()
    return next_reservation

def update_book_status(book):
    """書籍の状態を現在の貸出・予約状況に基づいて更新"""
    from models import ReservationStatus
    
    # 現在の貸出状況をチェック
    current_loan = LoanHistory.query.filter_by(
        book_id=book.id,
        return_date=None
    ).first()
    
    if current_loan:
        # 貸出中
        book.status = BookStatus.ON_LOAN
        book.borrower_id = current_loan.borrower_id
    else:
        # 貸出されていない場合、予約状況をチェック
        book.borrower_id = None
        
        pending_reservations = Reservation.query.filter_by(
            book_id=book.id,
            status=ReservationStatus.PENDING
        ).count()
        
        notified_reservations = Reservation.query.filter_by(
            book_id=book.id,
            status=ReservationStatus.NOTIFIED
        ).count()
        
        if notified_reservations > 0 or pending_reservations > 0:
            book.status = BookStatus.RESERVED
        else:
            book.status = BookStatus.AVAILABLE
    
    db.session.commit()
    current_app.logger.info(f"Updated book {book.id} status to {book.status}")
    return book