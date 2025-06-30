from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from argon2.exceptions import VerifyMismatchError
from argon2 import PasswordHasher
from datetime import datetime, timedelta
from enum import Enum
import json
from sqlalchemy.orm import validates
from sqlalchemy import or_, and_

db = SQLAlchemy()
ph = PasswordHasher()

class User(db.Model, UserMixin):
    """ユーザー情報テーブル"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # 氏名
    is_admin = db.Column(db.Boolean, default=False)   # 権限（管理者かどうか）
    slack_user_id = db.Column(db.String(50), nullable=True)  # SlackユーザーIDを保存するカラム
    max_loan_limit = db.Column(db.Integer, default=3, nullable=False)  # 最大同時貸出数
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    loans = db.relationship('LoanHistory', back_populates='borrower', lazy=True)
    reservations = db.relationship('Reservation', back_populates='user', lazy=True, cascade="all, delete-orphan")
    operation_logs = db.relationship('OperationLog', back_populates='user', lazy=True, cascade="all, delete-orphan")
    
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
    
    def current_loan_count(self):
        """現在の貸出数を取得"""
        active_loans = [loan for loan in self.loans if loan.is_active]
        return len(active_loans)
    
    def current_reservation_count(self):
        """現在の予約数を取得"""
        active_reservations = [r for r in self.reservations if r.status == ReservationStatus.PENDING]
        return len(active_reservations)
    
    def can_borrow_more(self):
        """追加で本を借りられるかどうかを確認"""
        total_active = self.current_loan_count() + self.current_reservation_count()
        return total_active < self.max_loan_limit
    
    def has_overdue_books(self):
        """延滞中の本があるかどうかを確認"""
        for loan in self.loans:
            if loan.is_active and loan.is_overdue():
                return True
        return False
    
    def __repr__(self):
        return f'<User {self.email}>'


class BookStatus(Enum):
    """書籍状態の列挙型"""
    AVAILABLE = '利用可能'
    ON_LOAN = '貸出中'
    RESERVED = '予約あり'
    UNAVAILABLE = '利用不可'

class ReservationStatus(Enum):
    """予約状態の列挙型"""
    PENDING = 'pending'     # 予約受付中
    NOTIFIED = 'notified'   # 利用可能（通知済み）
    FULFILLED = 'fulfilled' # 貸出完了
    CANCELLED = 'cancelled' # キャンセル
    EXPIRED = 'expired'     # 期限切れ

class Book(db.Model):
    """書籍情報テーブル"""
    __tablename__ = 'books'
    
    id = db.Column(db.Integer, primary_key=True)  # 番号
    book_number = db.Column(db.String(20), unique=True, nullable=True, index=True)  # 管理番号 (BO-yyyy-001)
    title = db.Column(db.String(200), nullable=False, index=True)  # 書籍名
    status = db.Column(db.Enum(BookStatus), default=BookStatus.AVAILABLE, index=True)  # 状態を追加
    is_available = db.Column(db.Boolean, default=True, index=True)  # 貸出可否
    author = db.Column(db.String(100), index=True)  # 著者
    category1 = db.Column(db.String(50), index=True)  # 第１分類
    category2 = db.Column(db.String(50))  # 第２分類
    keywords = db.Column(db.String(200))  # キーワード
    location = db.Column(db.String(100))  # 場所
    borrower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # 借りた人
    borrower = db.relationship('User', backref=db.backref('borrowed_books', lazy=True))
    registration_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # 登録日
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    loans = db.relationship('LoanHistory', back_populates='book', lazy=True)
    reservations = db.relationship('Reservation', back_populates='book', lazy=True, cascade="all, delete-orphan")
    images = db.relationship('BookImage', back_populates='book', lazy=True, cascade="all, delete-orphan")
    
    @property
    def current_loan(self):
        """現在の貸出情報を取得"""
        if not self.loans:
            return None
        return next((loan for loan in self.loans if loan.return_date is None), None)
    
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
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    book = db.relationship('Book', back_populates='loans')
    book_title = db.Column(db.String(200), nullable=False)  # 書籍名
    borrower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    borrower = db.relationship('User', back_populates='loans')
    loan_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # 貸出日
    due_date = db.Column(db.DateTime, nullable=True, index=True)  # 返却期限日
    return_date = db.Column(db.DateTime, nullable=True, index=True)  # 返却日
    reminder_sent = db.Column(db.Boolean, default=False)  # 期限前リマインダー送信済み
    extension_count = db.Column(db.Integer, default=0, nullable=False)  # 延長回数
    extended_date = db.Column(db.DateTime, nullable=True)  # 延長実施日
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
    
    def can_extend(self):
        """延長可能かどうかを確認"""
        # 既に返却済み
        if self.return_date:
            return False
        # 延長回数が上限に達している
        if self.extension_count >= 1:
            return False
        # 予約者がいる場合は延長不可
        if self.book.reservations:
            active_reservations = [r for r in self.book.reservations if r.status == ReservationStatus.PENDING]
            if active_reservations:
                return False
        return True
    
    def __repr__(self):
        return f'<LoanHistory {self.book_title}>'


class Reservation(db.Model):
    """予約情報テーブル"""
    __tablename__ = 'reservations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    reservation_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # 予約ステータス (pending, notified, fulfilled, cancelled, expired)
    status = db.Column(db.Enum(ReservationStatus), nullable=False, default=ReservationStatus.PENDING, index=True)
    
    # 通知フラグと日時
    notification_sent = db.Column(db.Boolean, default=False)
    notification_sent_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    user = db.relationship('User', back_populates='reservations')
    book = db.relationship('Book', back_populates='reservations')
    
    @property
    def queue_position(self):
        """予約順位を取得"""
        if self.status != ReservationStatus.PENDING:
            return None
        
        # 自分より前に予約された有効な予約の数を数える + 1
        # 同じ時刻の場合はIDの小さい順
        earlier_reservations_count = Reservation.query.filter(
            Reservation.book_id == self.book_id,
            Reservation.status == ReservationStatus.PENDING,
            or_(
                Reservation.reservation_date < self.reservation_date,
                and_(
                    Reservation.reservation_date == self.reservation_date,
                    Reservation.id < self.id
                )
            )
        ).count()
        
        return earlier_reservations_count + 1
    
    def __repr__(self):
        return f'<Reservation {self.id} for Book {self.book_id} by User {self.user_id}>'


class OperationLog(db.Model):
    """操作ログモデル"""
    __tablename__ = 'operation_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    target = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))
    
    # Relationship
    user = db.relationship('User', back_populates='operation_logs')
    
    def __repr__(self):
        return f'<OperationLog {self.action}>'


class Announcement(db.Model):
    """管理者お知らせテーブル"""
    __tablename__ = 'announcements'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)  # お知らせタイトル
    content = db.Column(db.Text, nullable=False)  # お知らせ内容
    is_active = db.Column(db.Boolean, default=True, nullable=False)  # 表示フラグ
    priority = db.Column(db.String(10), default='low', nullable=False)  # 優先度（low/medium/high）
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # 作成者
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    creator = db.relationship('User', backref=db.backref('announcements', lazy=True))
    
    def __repr__(self):
        return f'<Announcement {self.title}>'


class CategoryLocationMapping(db.Model):
    """分類場所マッピングテーブル"""
    __tablename__ = 'category_location_mapping'
    
    id = db.Column(db.Integer, primary_key=True)
    category1 = db.Column(db.String(50), nullable=False, index=True)  # 第１分類
    default_location = db.Column(db.String(100), nullable=False)  # デフォルト場所
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<CategoryLocationMapping {self.category1} -> {self.default_location}>'


class BookImage(db.Model):
    """書籍画像テーブル"""
    __tablename__ = 'book_images'
    
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    image_type = db.Column(db.String(20), nullable=False)  # 画像種類 (cover, contents, etc.)
    file_path = db.Column(db.String(255), nullable=False)  # ファイルパス
    file_name = db.Column(db.String(100), nullable=False)  # ファイル名
    file_size = db.Column(db.Integer, nullable=False)  # ファイルサイズ（バイト）
    mime_type = db.Column(db.String(50), nullable=False)  # MIMEタイプ
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    book = db.relationship('Book', back_populates='images')
    
    def __repr__(self):
        return f'<BookImage {self.book_id}:{self.image_type}>'