# services/book_service.py
import pandas as pd
from sqlalchemy import or_
from datetime import datetime, timedelta
import csv
import io

from models import db, Book, LoanHistory

def get_books(keyword=None, is_available=None, category1=None, category2=None):
    """書籍を検索して取得"""
    query = Book.query
    
    if keyword:
        query = query.filter(
            db.or_(
                Book.title.ilike(f'%{keyword}%'),
                Book.author.ilike(f'%{keyword}%'),
                Book.keywords.ilike(f'%{keyword}%')
            )
        )
    
    if is_available:
        if is_available == '1':
            query = query.filter_by(is_available=True)
        elif is_available == '0':
            query = query.filter_by(is_available=False)
    
    if category1:
        query = query.filter_by(category1=category1)
    
    if category2:
        query = query.filter_by(category2=category2)
    
    return query.all()

def get_book_by_id(book_id):
    """IDで書籍を取得"""
    return Book.query.get(book_id)

def create_book(title, author=None, category1=None, category2=None, keywords=None, location=None, is_available=True):
    """書籍を作成"""
    book = Book(
        title=title,
        author=author,
        category1=category1,
        category2=category2,
        keywords=keywords,
        location=location,
        is_available=is_available
    )
    db.session.add(book)
    db.session.commit()
    return book

def update_book(book, title=None, author=None, category1=None, category2=None, keywords=None, location=None, is_available=None):
    """書籍を更新"""
    if title is not None:
        book.title = title
    if author is not None:
        book.author = author
    if category1 is not None:
        book.category1 = category1
    if category2 is not None:
        book.category2 = category2
    if keywords is not None:
        book.keywords = keywords
    if location is not None:
        book.location = location
    if is_available is not None:
        book.is_available = is_available
    
    db.session.commit()
    return book

def checkout_book(book, user_id, loan_days=14):
    """書籍を貸し出す"""
    if not book.is_available:
        raise ValueError("この書籍は既に貸し出されています。")
    
    # 書籍の状態を更新
    book.is_available = False
    book.borrower_id = user_id
    
    # 貸出日と返却期限の設定
    loan_date = datetime.now()
    due_date = loan_date + timedelta(days=loan_days)
    
    # 貸出履歴を作成
    history = LoanHistory(
        book_id=book.id,
        book_title=book.title,
        borrower_id=user_id,
        loan_date=loan_date,
        due_date=due_date,
        reminder_sent=False
    )
    
    db.session.add(history)
    db.session.commit()
    
    return book, history

def return_book(book):
    """書籍を返却する"""
    from services.reservation_service import process_book_return
    
    if book.is_available:
        raise ValueError("この書籍は既に返却されています。")
    
    # 書籍の状態を更新
    book.is_available = True
    
    # 最新の貸出履歴を更新
    history = LoanHistory.query.filter_by(
        book_id=book.id, 
        return_date=None
    ).order_by(LoanHistory.loan_date.desc()).first()
    
    if history:
        history.return_date = datetime.now()
    
    # 借りた人の情報をクリア
    borrowed_user_id = book.borrower_id
    book.borrower_id = None
    
    db.session.commit()
    
    # 予約者への通知処理
    reservation = process_book_return(book.id)
    
    return book, history, borrowed_user_id, reservation

def import_books_from_csv(file_path):
    """CSVファイルから書籍をインポート"""
    imported_count = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 必須フィールドのチェック
            if not row.get('title'):
                continue
            
            # is_availableの変換
            is_available = True
            if 'is_available' in row:
                is_available = row['is_available'].lower() in ['true', '1', 'yes']
            
            # 書籍の作成
            book = Book(
                title=row['title'],
                author=row.get('author', ''),
                category1=row.get('category1', ''),
                category2=row.get('category2', ''),
                keywords=row.get('keywords', ''),
                location=row.get('location', ''),
                is_available=is_available
            )
            db.session.add(book)
            imported_count += 1
    
    db.session.commit()
    return imported_count