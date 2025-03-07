from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from argon2.exceptions import VerifyMismatchError
from argon2 import PasswordHasher
from datetime import datetime, timedelta
from enum import Enum
import json

db = SQLAlchemy()
ph = PasswordHasher()

class User(db.Model, UserMixin):
    """ユーザー情報テーブル"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # 氏名
    email = db.Column(db.String(120), unique=True, index=True)    # メールアドレス
    is_admin = db.Column(db.Boolean, default=False)   # 権限（管理者かどうか）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        """パスワードをArgon2でハッシュ化してセットする"""
        self.password_hash = ph.hash(password)
        
    def check_password(self, password):
        """パスワードをチェックする"""
        try:
            return ph.verify(self.password_hash, password)
        except VerifyMismatchError:
            return False
        except Exception as e:
            print(f"Password verification error: {e}")
            return False
    
    def __repr__(self):
        return f'<User {self.username}>'


class BookStatus(str, Enum):
    """書籍状態の列挙型"""
    AVAILABLE = 'available'      # 利用可能
    BORROWED = 'borrowed'        # 貸出中
    RESERVED = 'reserved'        # 予約済み
    UNAVAILABLE = 'unavailable'  # 利用不可

class ReservationStatus(str, Enum):
    """予約状態の列挙型"""
    PENDING = 'pending'      # 予約中
    NOTIFIED = 'notified'    # 通知済み
    COMPLETED = 'completed'  # 完了
    CANCELLED = 'cancelled'  # キャンセル

class Book(db.Model):
    """書籍情報テーブル"""
    __tablename__ = 'books'
    
    id = db.Column(db.Integer, primary_key=True)  # 番号
    title = db.Column(db.String(200), nullable=False, index=True)  # 書籍名
    status = db.Column(db.String(20), default=BookStatus.AVAILABLE, index=True)  # 状態を追加
    is_available = db.Column(db.Boolean, default=True, index=True)  # 貸出可否
    author = db.Column(db.String(100), index=True)  # 著者
    category1 = db.Column(db.String(50), index=True)  # 第１分類
    category2 = db.Column(db.String(50))  # 第２分類
    keywords = db.Column(db.String(200))  # キーワード
    location = db.Column(db.String(100))  # 場所
    borrower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # 借りた人
    borrower = db.relationship('User', backref=db.backref('borrowed_books', lazy='dynamic'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def current_loan(self):
        """現在の貸出情報を取得"""
        return self.loan_history.filter_by(return_date=None).first()
    
    @property
    def search_vector(self):
        """検索用のベクトルを生成"""
        return ' '.join(filter(None, [
            self.title,
            self.author,
            self.category1,
            self.category2,
            self.keywords
        ])).lower()

    def __repr__(self):
        return f'<Book {self.title}>'


class LoanHistory(db.Model):
    """貸出履歴テーブル"""
    __tablename__ = 'loan_history'
    
    id = db.Column(db.Integer, primary_key=True)  # 履歴ID
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False, index=True)
    book = db.relationship('Book', backref=db.backref('loan_history', lazy='dynamic'))
    book_title = db.Column(db.String(200), nullable=False)  # 書籍名
    borrower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    borrower = db.relationship('User', backref=db.backref('loan_history', lazy='dynamic'))
    loan_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # 貸出日
    due_date = db.Column(db.DateTime, nullable=True, index=True)  # 返却期限日
    return_date = db.Column(db.DateTime, nullable=True, index=True)  # 返却日
    reminder_sent = db.Column(db.Boolean, default=False)  # 期限前リマインダー送信済み
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_active(self):
        """貸出が現在アクティブかどうかを確認"""
        return self.return_date is None

    def is_overdue(self):
        """返却期限切れかどうかを確認"""
        if not self.due_date or self.return_date:
            return False
        now = datetime.utcnow()
        return now > self.due_date
        
    def days_until_due(self):
        """返却期限までの残り日数を計算"""
        if not self.due_date or self.return_date:
            return None
        now = datetime.utcnow()
        delta = self.due_date - now
        return delta.days
    
    def __repr__(self):
        return f'<LoanHistory {self.book_title}>'


class Reservation(db.Model):
    """予約情報テーブル"""
    __tablename__ = 'reservations'
    
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    book = db.relationship('Book', backref=db.backref('reservations', lazy=True))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('reservations', lazy=True))
    reservation_date = db.Column(db.DateTime, default=datetime.utcnow)
    notification_sent = db.Column(db.Boolean, default=False)  # 通知送信済みフラグ
    status = db.Column(db.String(20), default=ReservationStatus.PENDING)
    
    @property
    def queue_position(self):
        """予約順位を取得"""
        if self.status != ReservationStatus.PENDING:
            return None
        
        # 同じ本の有効な予約を予約日順で取得
        reservations = Reservation.query.filter_by(
            book_id=self.book_id,
            status=ReservationStatus.PENDING
        ).order_by(Reservation.reservation_date).all()
        
        # 自分の位置を特定（1から始まる順位）
        for i, reservation in enumerate(reservations, 1):
            if reservation.id == self.id:
                return i
        return None
    
    def __repr__(self):
        return f'<Reservation {self.id} for Book {self.book_id} by User {self.user_id}>'


class OperationLog(db.Model):
    """操作ログモデル"""
    __tablename__ = 'operation_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(50), nullable=False)
    target = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    additional_data = db.Column(db.Text, nullable=True)
    
    # リレーションシップ
    user = db.relationship('User', backref=db.backref('operation_logs', lazy=True))
    
    def __repr__(self):
        return f'<OperationLog {self.action}>'