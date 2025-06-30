#!/usr/bin/env python3
"""
既存データの更新スクリプト
- 既存書籍に管理番号を付与
- 基本的な分類場所マッピングを作成
"""

from datetime import datetime
from app import create_app
from models import db, Book, CategoryLocationMapping

def update_existing_books():
    """既存の書籍に管理番号を付与"""
    app = create_app()
    with app.app_context():
        # 管理番号がない書籍を取得
        books_without_number = Book.query.filter(Book.book_number.is_(None)).all()
        
        if not books_without_number:
            print("すべての書籍に管理番号が付与されています。")
            return
        
        # 現在の年を取得
        current_year = datetime.now().year
        
        # 既存の管理番号から最新の連番を取得
        latest_book = Book.query.filter(
            Book.book_number.like(f'BO-{current_year}-%')
        ).order_by(Book.book_number.desc()).first()
        
        if latest_book:
            # 既存の番号から連番を抽出
            last_number = int(latest_book.book_number.split('-')[-1])
            next_number = last_number + 1
        else:
            # 今年の最初の番号
            next_number = 1
        
        print(f"管理番号の付与を開始します。開始番号: BO-{current_year}-{next_number:03d}")
        
        # 書籍に管理番号を付与
        for book in books_without_number:
            book.book_number = f"BO-{current_year}-{next_number:03d}"
            book.registration_date = datetime.now()  # 今日の日付を設定
            next_number += 1
            print(f"書籍「{book.title}」に管理番号 {book.book_number} を付与")
        
        try:
            db.session.commit()
            print(f"完了: {len(books_without_number)}冊の書籍に管理番号を付与しました。")
        except Exception as e:
            db.session.rollback()
            print(f"エラーが発生しました: {e}")

def create_default_category_mappings():
    """基本的な分類場所マッピングを作成"""
    app = create_app()
    with app.app_context():
        # デフォルトマッピング
        default_mappings = [
            ('技術書', 'A棚'),
            ('ビジネス書', 'B棚'),
            ('小説', 'C棚'),
            ('参考書', 'D棚'),
            ('雑誌', 'E棚'),
            ('その他', 'F棚'),
        ]
        
        existing_categories = {m.category1 for m in CategoryLocationMapping.query.all()}
        
        for category, location in default_mappings:
            if category not in existing_categories:
                mapping = CategoryLocationMapping(
                    category1=category,
                    default_location=location
                )
                db.session.add(mapping)
                print(f"分類マッピングを追加: {category} -> {location}")
        
        try:
            db.session.commit()
            print("分類場所マッピングの作成が完了しました。")
        except Exception as e:
            db.session.rollback()
            print(f"エラーが発生しました: {e}")

if __name__ == '__main__':
    print("既存データの更新を開始します...")
    update_existing_books()
    create_default_category_mappings()
    print("すべての更新が完了しました。")