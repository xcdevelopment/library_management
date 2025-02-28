from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

db = SQLAlchemy()

class User(db.Model, UserMixin):
    """ユーザー情報テーブル"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # 氏名
    email = db.Column(db.String(120), unique=True)    # メールアドレス
    is_admin = db.Column(db.Boolean, default=False)   # 権限（管理者かどうか）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        """パスワードをハッシュ化してセットする"""
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """パスワードをチェックする"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Book(db.Model):
    """書籍情報テーブル"""
    __tablename__ = 'books'
    
    id = db.Column(db.Integer, primary_key=True)  # 番号
    title = db.Column(db.String(200), nullable=False)  # 書籍名
    is_available = db.Column(db.Boolean, default=True)  # 貸出可否
    author = db.Column(db.String(100))  # 著者
    category1 = db.Column(db.String(50))  # 第１分類
    category2 = db.Column(db.String(50))  # 第２分類
    keywords = db.Column(db.String(200))  # キーワード
    location = db.Column(db.String(100))  # 場所
    borrower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # 借りた人
    borrower = db.relationship('User', backref=db.backref('borrowed_books', lazy=True))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Book {self.title}>'


class LoanHistory(db.Model):
    """貸出履歴テーブル"""
    __tablename__ = 'loan_history'
    
    id = db.Column(db.Integer, primary_key=True)  # 履歴ID
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)  # 番号
    book = db.relationship('Book', backref=db.backref('loan_history', lazy=True))
    book_title = db.Column(db.String(200), nullable=False)  # 書籍名
    borrower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # 借りた人
    borrower = db.relationship('User', backref=db.backref('loan_history', lazy=True))
    loan_date = db.Column(db.DateTime, default=datetime.utcnow)  # 貸出日
    due_date = db.Column(db.DateTime, nullable=True)  # 返却期限日
    return_date = db.Column(db.DateTime, nullable=True)  # 返却日
    reminder_sent = db.Column(db.Boolean, default=False)  # 期限前リマインダー送信済み
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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
    status = db.Column(db.String(20), default='pending')  # pending, notified, completed, cancelled
    
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