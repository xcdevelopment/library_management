# services/user_service.py
from models import db, User, Book, LoanHistory
import csv
from werkzeug.security import generate_password_hash

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

def update_user(user, username=None, name=None, is_admin=None, email=None, password=None):
    """ユーザー情報を更新する"""
    # 引数が指定されている場合のみ更新
    if username is not None:
        # ユーザー名の重複チェック（自分以外）
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != user.id:
            raise ValueError(f'ユーザー名"{username}"は既に使用されています。')
        user.username = username
    
    if name is not None:
        user.name = name
    
    if email is not None:
        # メールアドレスの重複チェック（自分以外）
        existing_email = User.query.filter_by(email=email).first()
        if existing_email and existing_email.id != user.id:
            raise ValueError(f'メールアドレス"{email}"は既に使用されています。')
        user.email = email
    
    if is_admin is not None:
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

def import_users_from_csv(file_path):
    """CSVファイルからユーザーをインポート
    
    Args:
        file_path (str): インポートするCSVファイルのパス
        
    Returns:
        tuple: (成功件数, 失敗件数, エラーリスト)
    """
    success_count = 0
    failure_count = 0
    errors = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # 必須フィールドのチェック
                    if not all(key in row and row[key] for key in ['username', 'password', 'name']):
                        failure_count += 1
                        errors.append(f"行 {reader.line_num}: 必須フィールド (username, password, name) が不足しています")
                        continue
                        
                    # ユーザー名重複チェック
                    if User.query.filter_by(username=row['username']).first():
                        failure_count += 1
                        errors.append(f"行 {reader.line_num}: ユーザー名 '{row['username']}' は既に使用されています")
                        continue
                    
                    # メールアドレス重複チェック (存在する場合)
                    if row.get('email') and User.query.filter_by(email=row['email']).first():
                        failure_count += 1
                        errors.append(f"行 {reader.line_num}: メールアドレス '{row['email']}' は既に使用されています")
                        continue
                    
                    # is_adminの変換
                    is_admin = False
                    if 'is_admin' in row:
                        is_admin_str = row['is_admin'].lower()
                        is_admin = is_admin_str in ['true', '1', 'yes', 'はい', 'y', 't']
                    
                    # ユーザーの作成
                    user = User(
                        username=row['username'],
                        name=row['name'],
                        email=row.get('email', ''),
                        is_admin=is_admin
                    )
                    user.set_password(row['password'])
                    
                    db.session.add(user)
                    success_count += 1
                    
                except Exception as e:
                    failure_count += 1
                    errors.append(f"行 {reader.line_num}: エラー - {str(e)}")
            
            # 全て処理したらコミット
            db.session.commit()
    
    except Exception as e:
        db.session.rollback()
        failure_count += 1
        errors.append(f"ファイル処理エラー: {str(e)}")
    
    return (success_count, failure_count, errors)
