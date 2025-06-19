from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import csv
import os
import chardet

from services.user_service import create_user, get_user_by_id, update_user, delete_user, import_users_from_csv
from utils.decorators import admin_required
from models import User, db, OperationLog
from forms.user import NewUserForm, EditUserForm

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
def users():
    """ユーザー一覧（管理者のみ）"""
    if not current_user.is_admin:
        flash('この機能は管理者のみ利用できます。', 'danger')
        return redirect(url_for('books.index'))
    
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_user():
    """新規ユーザー作成（管理者用）"""
    form = NewUserForm()
    if form.validate_on_submit():
        try:
            create_user(
                password=form.password.data,
                name=form.name.data,
                email=form.email.data,
                is_admin=form.is_admin.data
            )
            flash('新規ユーザーが作成されました。', 'success')
            return redirect(url_for('admin.users'))
        except ValueError as e:
            flash(str(e), 'danger')
            
    return render_template('admin/new_user.html', form=form)

@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """ユーザー情報編集（管理者用）"""
    user = get_user_by_id(user_id)
    if not user:
        flash('指定されたユーザーが見つかりません。', 'danger')
        return redirect(url_for('admin.users'))
        
    form = EditUserForm(obj=user)
    
    if form.validate_on_submit():
        try:
            update_user(
                user=user,
                name=form.name.data,
                email=form.email.data,
                is_admin=form.is_admin.data,
                password=form.password.data if form.password.data else None
            )
            flash('ユーザー情報が更新されました。', 'success')
            return redirect(url_for('admin.users'))
        except ValueError as e:
            flash(str(e), 'danger')

    return render_template('admin/edit_user.html', form=form, user=user)

@admin_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user_route(user_id):
    """ユーザー削除（管理者用）"""
    if current_user.id == user_id:
        flash('自分自身を削除することはできません。', 'danger')
        return redirect(url_for('admin.users'))
    
    try:
        if delete_user(user_id):
            flash('ユーザーが削除されました。', 'success')
        else:
            flash('ユーザーが見つかりません。', 'warning')
    except ValueError as e:
        flash(str(e), 'danger')
        
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/import', methods=['GET', 'POST'])
@login_required
def import_users():
    """CSVによるユーザー一括登録"""
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
            
            try:
                success_count, error_count, errors = import_users_from_csv(filepath)

                if success_count > 0:
                    flash(f'{success_count}件のユーザーを登録しました。', 'success')
                if error_count > 0:
                    flash(f'{error_count}件の登録に失敗しました。詳細は以下の通りです。', 'danger')
                    for error in errors[:10]:
                        flash(error, 'danger')
                    if len(errors) > 10:
                        flash(f'他 {len(errors) - 10}件のエラーがあります。', 'warning')

            except Exception as e:
                db.session.rollback()
                flash(f'CSVファイルの処理中にエラーが発生しました: {str(e)}', 'danger')
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)
            
            return redirect(url_for('admin.users'))
        
        flash('許可されていないファイル形式です。CSVファイルをアップロードしてください。', 'danger')
        return redirect(request.url)
    
    return render_template('admin/import_users.html') 