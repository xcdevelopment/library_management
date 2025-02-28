# services/user_service.py
from models import db, User, Book, LoanHistory

def get_users():
    """ユーザー一覧を取得する"""
    return User.query.order_by(User.id).all()

def get_user_by_id(id):
    """IDでユーザーを取得する"""
    return User.query.get(id)

def create_user(username, password, name, email=None, is_admin=False):
    """ユーザーを新規作成する"""
    # ユーザー名の重複チェック
    if User.query.filter_by(username=username).first():
        raise ValueError(f'ユーザー名"{username}"は既に使用されています。')
    
    # メールアドレスの重複チェック
    if email and User.query.filter_by(email=email).first():
        raise ValueError(f'メールアドレス"{email}"は既に使用されています。')
    
    user = User(
        username=username,
        name=name,
        email=email,
        is_admin=is_admin
    )
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    return user

def update_user(user, username, name, is_admin=False, email=None, password=None):
    """ユーザー情報を更新する"""
    # ユーザー名の重複チェック（自分以外）
    existing_user = User.query.filter_by(username=username).first()
    if existing_user and existing_user.id != user.id:
        raise ValueError(f'ユーザー名"{username}"は既に使用されています。')
    
    # メールアドレスの重複チェック（自分以外）
    if email:
        existing_email = User.query.filter_by(email=email).first()
        if existing_email and existing_email.id != user.id:
            raise ValueError(f'メールアドレス"{email}"は既に使用されています。')
    
    user.username = username
    user.name = name
    user.email = email
    user.is_admin = is_admin
    
    # パスワードが設定されている場合のみ更新
    if password:
        user.set_password(password)
    
    db.session.commit()
    
    return user

def delete_user(user):
    """ユーザーを削除する"""
    # 貸出中の書籍があるかチェック
    borrowed_books = Book.query.filter_by(borrower_id=user.id).all()
    if borrowed_books:
        book_titles = ', '.join([book.title for book in borrowed_books])
        raise ValueError(f'このユーザーは以下の書籍を借りているため削除できません: {book_titles}')
    
    # 貸出履歴は残す（参照整合性のためborrowrはNULLに）
    history_records = LoanHistory.query.filter_by(borrower_id=user.id).all()
    for record in history_records:
        record.borrower_id = None
    
    db.session.delete(user)
    db.session.commit()
    
    return True