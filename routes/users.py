# routes/users.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User, Book, LoanHistory, Reservation
from forms.user_forms import EditProfileForm, UserForm
from services.auth_service import create_user_operation_log
from flask_wtf import FlaskForm

users_bp = Blueprint('users', __name__, url_prefix='/users')

@users_bp.route('/mypage')
@login_required
def mypage():
    """マイページを表示"""
    # 現在借りている本を取得
    borrowed_books = Book.query.filter_by(borrower_id=current_user.id).all()
    
    # 予約情報を取得
    reservations = Reservation.query.filter_by(user_id=current_user.id).order_by(Reservation.reservation_date.desc()).all()
    
    # 貸出履歴を取得
    loan_history = LoanHistory.query.filter_by(borrower_id=current_user.id).order_by(LoanHistory.loan_date.desc()).all()
    
    return render_template('users/mypage.html',
                         user=current_user,
                         borrowed_books=borrowed_books,
                         reservations=reservations,
                         loan_history=loan_history)

@users_bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """プロフィール編集"""
    form = EditProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.email = form.email.data
        
        db.session.commit()
        
        # 操作ログを記録
        create_user_operation_log(
            user_id=current_user.id,
            action='edit_profile',
            target='user',
            details=f'Updated profile for user {current_user.username}',
            ip_address=request.remote_addr
        )
        
        flash('プロフィールを更新しました。', 'success')
        return redirect(url_for('users.mypage'))
    
    return render_template('users/edit_profile.html', form=form)

@users_bp.route('/')
@login_required
def index():
    """ユーザー一覧（管理者用）"""
    if not current_user.is_admin:
        flash('この操作には管理者権限が必要です。', 'danger')
        return redirect(url_for('books.index'))
    
    users = User.query.all()
    form = FlaskForm()  # CSRFトークン用の空のフォーム
    return render_template('users/index.html', users=users, form=form)

@users_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """ユーザー追加（管理者用）"""
    if not current_user.is_admin:
        flash('この操作には管理者権限が必要です。', 'danger')
        return redirect(url_for('books.index'))
    
    form = UserForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            name=form.name.data,
            email=form.email.data,
            is_admin=form.is_admin.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        # 操作ログを記録
        create_user_operation_log(
            user_id=current_user.id,
            action='create',
            target='user',
            details=f'Created new user: {user.username}',
            ip_address=request.remote_addr
        )
        
        flash(f'ユーザー "{user.username}" を登録しました。', 'success')
        return redirect(url_for('users.index'))
    
    return render_template('users/add.html', form=form)

@users_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """ユーザー編集（管理者用）"""
    if not current_user.is_admin:
        flash('この操作には管理者権限が必要です。', 'danger')
        return redirect(url_for('books.index'))
    
    user = User.query.get_or_404(id)
    form = UserForm(obj=user)
    
    if form.validate_on_submit():
        user.username = form.username.data
        user.name = form.name.data
        user.email = form.email.data
        user.is_admin = form.is_admin.data
        
        if form.password.data:  # パスワードが入力された場合のみ更新
            user.set_password(form.password.data)
        
        db.session.commit()
        
        # 操作ログを記録
        create_user_operation_log(
            user_id=current_user.id,
            action='update',
            target='user',
            details=f'Updated user: {user.username}',
            ip_address=request.remote_addr
        )
        
        flash(f'ユーザー "{user.username}" を更新しました。', 'success')
        return redirect(url_for('users.index'))
    
    # パスワードフィールドはクリアしておく
    form.password.data = ''
    form.password_confirm.data = ''
    
    return render_template('users/edit.html', form=form, user=user)

@users_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """ユーザー削除（管理者用）"""
    if not current_user.is_admin:
        flash('この操作には管理者権限が必要です。', 'danger')
        return redirect(url_for('books.index'))
    
    user = User.query.get_or_404(id)
    
    # 自分自身は削除できない
    if user.id == current_user.id:
        flash('自分自身は削除できません。', 'danger')
        return redirect(url_for('users.index'))
    
    username = user.username
    
    # ユーザーに関連する貸出履歴と予約を削除
    LoanHistory.query.filter_by(borrower_id=user.id).delete()
    Reservation.query.filter_by(user_id=user.id).delete()
    
    # 借りている本がある場合は、借り手情報をクリア
    Book.query.filter_by(borrower_id=user.id).update({Book.borrower_id: None})
    
    db.session.delete(user)
    db.session.commit()
    
    # 操作ログを記録
    create_user_operation_log(
        user_id=current_user.id,
        action='delete',
        target='user',
        details=f'Deleted user: {username}',
        ip_address=request.remote_addr
    )
    
    flash(f'ユーザー "{username}" を削除しました。', 'success')
    return redirect(url_for('users.index'))