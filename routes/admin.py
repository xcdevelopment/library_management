from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import csv
import os
import chardet

from models import User, db, OperationLog
from forms.user import UserForm

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# CSVアップロード用の設定
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}

# アップロードディレクトリの作成
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@admin_bp.route('/users')
@login_required
def user_list():
    """ユーザー一覧（管理者のみ）"""
    if not current_user.is_admin:
        flash('この機能は管理者のみ利用できます。', 'danger')
        return redirect(url_for('books.index'))
    
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
def new_user():
    """新規ユーザー作成（管理者のみ）"""
    if not current_user.is_admin:
        flash('この機能は管理者のみ利用できます。', 'danger')
        return redirect(url_for('books.index'))
    
    form = UserForm()
    if form.validate_on_submit():
        # 既存ユーザーチェック
        if User.query.filter_by(username=form.username.data).first():
            flash('このユーザー名は既に使用されています。', 'danger')
            return render_template('admin/new_user.html', form=form)
            
        if form.email.data and User.query.filter_by(email=form.email.data).first():
            flash('このメールアドレスは既に使用されています。', 'danger')
            return render_template('admin/new_user.html', form=form)
        
        # ユーザー作成
        user = User(
            username=form.username.data,
            name=form.name.data,
            email=form.email.data,
            is_admin=form.is_admin.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        
        # 操作ログの記録
        log = OperationLog(
            user_id=current_user.id,
            action='create_user',
            target=f'User {user.username}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        flash('ユーザーが作成されました。', 'success')
        return redirect(url_for('admin.user_list'))
        
    return render_template('admin/new_user.html', form=form)

@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """ユーザー編集（管理者のみ）"""
    if not current_user.is_admin:
        flash('この機能は管理者のみ利用できます。', 'danger')
        return redirect(url_for('books.index'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        
        # メールアドレス重複チェック
        if email != user.email and User.query.filter_by(email=email).first():
            flash('このメールアドレスは既に使用されています。', 'danger')
            return render_template('admin/edit_user.html', user=user)
        
        # ユーザー情報更新
        user.name = name
        user.email = email
        user.is_admin = 'is_admin' in request.form
        
        # パスワード変更（入力がある場合のみ）
        if request.form['password']:
            user.set_password(request.form['password'])
        
        # 操作ログの記録
        log = OperationLog(
            user_id=current_user.id,
            action='edit_user',
            target=f'User {user.id}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        flash('ユーザー情報が更新されました。', 'success')
        return redirect(url_for('admin.user_list'))
    
    return render_template('admin/edit_user.html', user=user)

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    """ユーザー削除（管理者のみ）"""
    if not current_user.is_admin:
        flash('この機能は管理者のみ利用できます。', 'danger')
        return redirect(url_for('books.index'))
    
    user = User.query.get_or_404(user_id)
    
    # 自分自身は削除できない
    if user.id == current_user.id:
        flash('自分自身を削除することはできません。', 'danger')
        return redirect(url_for('admin.user_list'))
    
    # 操作ログの記録
    log = OperationLog(
        user_id=current_user.id,
        action='delete_user',
        target=f'User {user.id}',
        details=f'Username: {user.username}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    
    # ユーザー削除
    db.session.delete(user)
    db.session.commit()
    
    flash('ユーザーが削除されました。', 'success')
    return redirect(url_for('admin.user_list'))

@admin_bp.route('/users/import', methods=['GET', 'POST'])
@login_required
def import_users():
    """ユーザーの一括インポート（管理者のみ）"""
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
            
            try:
                # ファイルの文字コードを自動判定
                with open(filepath, 'rb') as f:
                    raw_data = f.read()
                    result = chardet.detect(raw_data)
                    encoding = result['encoding']
                
                with open(filepath, 'r', encoding=encoding) as csvfile:
                    reader = csv.DictReader(csvfile)
                    
                    # ヘッダーの存在確認
                    required_headers = ['username', 'password', 'name']
                    missing_headers = [h for h in required_headers if h not in reader.fieldnames]
                    if missing_headers:
                        flash(f'必須列が不足しています: {", ".join(missing_headers)}', 'danger')
                        return redirect(request.url)
                    
                    for row_num, row in enumerate(reader, start=2):
                        try:
                            # 必須フィールドのチェック
                            if not all(key in row and row[key] for key in required_headers):
                                errors.append(f'行 {row_num}: 必須フィールド (username, password, name) が不足しています')
                                error_count += 1
                                continue
                            
                            # ユーザー名重複チェック
                            if User.query.filter_by(username=row['username']).first():
                                errors.append(f'行 {row_num}: ユーザー名 "{row["username"]}" は既に使用されています')
                                error_count += 1
                                continue
                            
                            # メールアドレス重複チェック（存在する場合）
                            if row.get('email') and User.query.filter_by(email=row['email']).first():
                                errors.append(f'行 {row_num}: メールアドレス "{row["email"]}" は既に使用されています')
                                error_count += 1
                                continue
                            
                            # is_adminの変換
                            is_admin = False
                            if 'is_admin' in row:
                                is_admin_str = row['is_admin'].lower()
                                is_admin = is_admin_str in ['true', '1', 'yes', 'はい', 'y', 't']
                            
                            # ユーザー作成
                            user = User(
                                username=row['username'],
                                name=row['name'],
                                email=row.get('email'),
                                is_admin=is_admin
                            )
                            user.set_password(row['password'])
                            db.session.add(user)
                            success_count += 1
                            
                            # 100件ごとにコミット
                            if success_count % 100 == 0:
                                db.session.commit()
                        
                        except Exception as e:
                            error_count += 1
                            errors.append(f'行 {row_num}: {str(e)}')
                    
                    # 残りのデータをコミット
                    db.session.commit()
                    
                    # 操作ログの記録
                    log = OperationLog(
                        user_id=current_user.id,
                        action='import_users',
                        target=f'Imported {success_count} users',
                        details=f'Success: {success_count}, Errors: {error_count}',
                        ip_address=request.remote_addr
                    )
                    db.session.add(log)
                    db.session.commit()
                    
                    if success_count > 0:
                        flash(f'{success_count}件のユーザーを登録しました。', 'success')
                    if error_count > 0:
                        flash(f'{error_count}件の登録に失敗しました。', 'warning')
                        for error in errors[:10]:  # 最初の10件のエラーのみ表示
                            flash(error, 'danger')
                        if len(errors) > 10:
                            flash(f'他 {len(errors) - 10} 件のエラーがあります。', 'warning')
            
            except Exception as e:
                db.session.rollback()
                flash(f'CSVファイルの処理中にエラーが発生しました: {str(e)}', 'danger')
            
            finally:
                # アップロードされたファイルを削除
                if os.path.exists(filepath):
                    os.remove(filepath)
            
            return redirect(url_for('admin.user_list'))
        
        flash('許可されていないファイル形式です。CSVファイルをアップロードしてください。', 'danger')
        return redirect(request.url)
    
    return render_template('admin/import_users.html') 