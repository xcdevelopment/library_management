from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import csv
import os
import chardet

from services.user_service import create_user, get_user_by_id, update_user, delete_user, import_users_from_csv
from utils.decorators import admin_required
from models import User, db, OperationLog, Announcement, CategoryLocationMapping
from forms.user import NewUserForm, EditUserForm
from forms.announcement import AnnouncementForm
from forms.category_location import CategoryLocationForm

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
            user = create_user(
                password=form.password.data,
                name=form.name.data,
                email=form.email.data,
                is_admin=form.is_admin.data
            )
            # 最大貸出数を設定
            user.max_loan_limit = form.max_loan_limit.data
            db.session.commit()
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
            # 最大貸出数の更新
            user.max_loan_limit = form.max_loan_limit.data
            
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

@admin_bp.route('/announcements')
@login_required
@admin_required
def announcements():
    """お知らせ一覧（管理者用）"""
    announcements = Announcement.query.order_by(
        Announcement.priority.desc(),
        Announcement.created_at.desc()
    ).all()
    return render_template('admin/announcements.html', announcements=announcements)

@admin_bp.route('/announcements/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_announcement():
    """新規お知らせ作成"""
    form = AnnouncementForm()
    if form.validate_on_submit():
        announcement = Announcement(
            title=form.title.data,
            content=form.content.data,
            priority=form.priority.data,
            is_active=form.is_active.data,
            created_by=current_user.id
        )
        db.session.add(announcement)
        
        # 操作ログの記録
        log = OperationLog(
            user_id=current_user.id,
            action='create_announcement',
            target=f'Announcement: {announcement.title}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        flash('お知らせが作成されました。', 'success')
        return redirect(url_for('admin.announcements'))
    
    return render_template('admin/new_announcement.html', form=form)

@admin_bp.route('/announcements/edit/<int:announcement_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_announcement(announcement_id):
    """お知らせ編集"""
    announcement = Announcement.query.get_or_404(announcement_id)
    form = AnnouncementForm(obj=announcement)
    
    if form.validate_on_submit():
        announcement.title = form.title.data
        announcement.content = form.content.data
        announcement.priority = form.priority.data
        announcement.is_active = form.is_active.data
        
        # 操作ログの記録
        log = OperationLog(
            user_id=current_user.id,
            action='edit_announcement',
            target=f'Announcement {announcement_id}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        flash('お知らせが更新されました。', 'success')
        return redirect(url_for('admin.announcements'))
    
    return render_template('admin/edit_announcement.html', form=form, announcement=announcement)

@admin_bp.route('/announcements/delete/<int:announcement_id>', methods=['POST'])
@login_required
@admin_required
def delete_announcement(announcement_id):
    """お知らせ削除"""
    announcement = Announcement.query.get_or_404(announcement_id)
    
    # 操作ログの記録
    log = OperationLog(
        user_id=current_user.id,
        action='delete_announcement',
        target=f'Announcement {announcement_id}: {announcement.title}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    
    db.session.delete(announcement)
    db.session.commit()
    
    flash('お知らせが削除されました。', 'success')
    return redirect(url_for('admin.announcements'))

@admin_bp.route('/announcements/toggle/<int:announcement_id>', methods=['POST'])
@login_required
@admin_required
def toggle_announcement(announcement_id):
    """お知らせの表示/非表示を切り替え"""
    announcement = Announcement.query.get_or_404(announcement_id)
    announcement.is_active = not announcement.is_active
    
    # 操作ログの記録
    status = "activated" if announcement.is_active else "deactivated"
    log = OperationLog(
        user_id=current_user.id,
        action=f'toggle_announcement_{status}',
        target=f'Announcement {announcement_id}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    status_msg = "表示" if announcement.is_active else "非表示"
    flash(f'お知らせを{status_msg}に設定しました。', 'success')
    return redirect(url_for('admin.announcements'))

@admin_bp.route('/category-locations')
@login_required
@admin_required
def category_locations():
    """カテゴリ-ロケーション設定一覧"""
    mappings = CategoryLocationMapping.query.order_by(CategoryLocationMapping.category1).all()
    return render_template('admin/category_locations.html', mappings=mappings)

@admin_bp.route('/category-locations/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_category_location():
    """新規カテゴリ-ロケーション設定"""
    form = CategoryLocationForm()
    if form.validate_on_submit():
        mapping = CategoryLocationMapping(
            category1=form.category1.data,
            default_location=form.default_location.data
        )
        db.session.add(mapping)
        
        # 操作ログの記録
        log = OperationLog(
            user_id=current_user.id,
            action='create_category_location',
            target=f'Category: {mapping.category1} -> {mapping.default_location}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        flash('カテゴリ-ロケーション設定が作成されました。', 'success')
        return redirect(url_for('admin.category_locations'))
    
    return render_template('admin/new_category_location.html', form=form)

@admin_bp.route('/category-locations/edit/<int:mapping_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_category_location(mapping_id):
    """カテゴリ-ロケーション設定編集"""
    mapping = CategoryLocationMapping.query.get_or_404(mapping_id)
    form = CategoryLocationForm(obj=mapping)
    
    if form.validate_on_submit():
        mapping.category1 = form.category1.data
        mapping.default_location = form.default_location.data
        
        # 操作ログの記録
        log = OperationLog(
            user_id=current_user.id,
            action='edit_category_location',
            target=f'Category Location {mapping_id}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        flash('カテゴリ-ロケーション設定が更新されました。', 'success')
        return redirect(url_for('admin.category_locations'))
    
    return render_template('admin/edit_category_location.html', form=form, mapping=mapping)

@admin_bp.route('/category-locations/delete/<int:mapping_id>', methods=['POST'])
@login_required
@admin_required
def delete_category_location(mapping_id):
    """カテゴリ-ロケーション設定削除"""
    mapping = CategoryLocationMapping.query.get_or_404(mapping_id)
    
    # 操作ログの記録
    log = OperationLog(
        user_id=current_user.id,
        action='delete_category_location',
        target=f'Category Location {mapping_id}: {mapping.category1}',
        ip_address=request.remote_addr
    )
    db.session.add(log)
    
    db.session.delete(mapping)
    db.session.commit()
    
    flash('カテゴリ-ロケーション設定が削除されました。', 'success')
    return redirect(url_for('admin.category_locations')) 