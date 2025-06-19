# services/user_service.py
from models import db, User, Book, LoanHistory
import csv
from werkzeug.security import generate_password_hash
import chardet
from flask import current_app

def get_users():
    """ユーザー一覧を取得する"""
    return User.query.order_by(User.id).all()

def get_user_by_id(user_id):
    """IDでユーザーを取得"""
    return User.query.get(user_id)

def create_user(password, name, email=None, is_admin=False):
    """新規ユーザーを作成"""
    # メールアドレスの重複チェック
    if email and User.query.filter_by(email=email).first():
        raise ValueError(f'メールアドレス"{email}"は既に使用されています。')

    user = User(
        name=name,
        email=email,
        is_admin=is_admin
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user

def update_user(user, name=None, is_admin=None, email=None, password=None):
    """ユーザー情報を更新"""
    if name is not None:
        user.name = name
    if is_admin is not None:
        user.is_admin = is_admin
    
    if email is not None and email != user.email:
        # メールアドレスの重複チェック
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != user.id:
            raise ValueError(f'メールアドレス"{email}"は既に使用されています。')
        user.email = email
        
    if password:
        user.set_password(password)
        
    db.session.commit()
    return user

def delete_user(user_id):
    """ユーザーを削除"""
    user = get_user_by_id(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        return True
    return False

def get_all_users():
    """全ユーザーを取得"""
    return User.query.all()

def import_users_from_csv(file_path):
    """CSVファイルからユーザーを一括インポート"""
    success_count = 0
    error_count = 0
    errors = []
    users_to_add = []

    try:
        # 文字コード判定
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            encoding = chardet.detect(raw_data)['encoding']
            if not encoding:
                encoding = 'utf-8' # デフォルト

        with open(file_path, 'r', encoding=encoding, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # ヘッダーの正規化（小文字化、スペース削除）
            reader.fieldnames = [h.lower().strip() for h in reader.fieldnames]

            required_headers = ['password', 'name', 'email']
            if not all(h in reader.fieldnames for h in required_headers):
                missing = [h for h in required_headers if h not in reader.fieldnames]
                # エラーリストに追加して、処理を中断せずに他のエラーも報告できるようにする
                errors.append(f"必須列が不足しています: {', '.join(missing)}")
                error_count += 1
                # ヘッダーが不正な場合はここで処理を中断するのが望ましい
                return 0, error_count, errors


            for i, row in enumerate(reader):
                line_num = i + 2 # ヘッダー行を考慮
                try:
                    # 必須フィールドのチェック
                    if not all(key in row and row[key] for key in required_headers):
                        errors.append(f"行 {line_num}: 必須フィールド (password, name, email) が不足しています")
                        error_count += 1
                        continue

                    email = row['email'].strip()
                    # 重複チェック (データベース内)
                    if User.query.filter_by(email=email).first():
                        errors.append(f"行 {line_num}: メールアドレス '{email}' は既に使用されています")
                        error_count += 1
                        continue

                    # 重複チェック (今回のCSVファイル内)
                    if any(u.email == email for u in users_to_add):
                        errors.append(f"行 {line_num}: このCSVファイル内でメールアドレス '{email}' が重複しています")
                        error_count += 1
                        continue
                    
                    # is_admin の解釈
                    is_admin_str = row.get('is_admin', 'false').lower().strip()
                    is_admin = is_admin_str in ['true', '1', 'yes', 't']

                    user = User(
                        name=row['name'].strip(),
                        email=email,
                        is_admin=is_admin
                    )
                    # パスワードをセット
                    user.set_password(row['password'].strip())
                    users_to_add.append(user)

                except Exception as e:
                    db.session.rollback()
                    errors.append(f"行 {line_num} の処理中に予期せぬエラー: {e}")
                    error_count += 1
            
            # ループ終了後、エラーがあればインポートを実行しない
            if error_count > 0:
                errors.insert(0, "ファイル内にエラーが検出されたため、インポート処理を中断しました。")
                return 0, error_count, errors

            # エラーがなければ、一括で追加とコミット
            if users_to_add:
                db.session.add_all(users_to_add)
                db.session.commit()
                success_count = len(users_to_add)

    except FileNotFoundError:
        errors.append(f"ファイルが見つかりません: {file_path}")
        error_count = 1
        # raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"CSVインポート処理中に予期せぬエラーが発生しました: {e}", exc_info=True)
        errors.append(f"CSVインポート処理全体で致命的なエラーが発生しました: {e}")
        error_count = len(users_to_add) if error_count == 0 else error_count
        # raise e

    return success_count, error_count, errors
