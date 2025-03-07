# routes/users.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from models import User, db, OperationLog, Book, Reservation

users_bp = Blueprint('users', __name__, url_prefix='/users')

@users_bp.route('/')
@login_required
def index():
    """ユーザー一覧（管理者のみ）"""
    if not current_user.is_admin:
        flash('この機能は管理者のみ利用できます。', 'danger')
        return redirect(url_for('books.index'))
    
    users = User.query.all()
    return render_template('users/index.html', users=users)

@users_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_user():
    """新規ユーザー作成（管理者のみ）"""
    if not current_user.is_admin:
        flash('この機能は管理者のみ利用できます。', 'danger')
        return redirect(url_for('books.index'))
    
    if request.method == 'POST':
        username = request.form['username']
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        is_admin = 'is_admin' in request.form
        
        # 既存ユーザーチェック
        if User.query.filter_by(username=username).first():
            flash('このユーザー名は既に使用されています。', 'danger')
            return render_template('users/new.html')
            
        if email and User.query.filter_by(email=email).first():
            flash('このメールアドレスは既に使用されています。', 'danger')
            return render_template('users/new.html')
        
        # ユーザー作成
        user = User(username=username, name=name, email=email, is_admin=is_admin)
        user.set_password(password)
        
        db.session.add(user)
        
        # 操作ログの記録
        log = OperationLog(
            user_id=current_user.id,
            action='create_user',
            target=f'User {username}',
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        
        flash('ユーザーが作成されました。', 'success')
        return redirect(url_for('users.index'))
        
    return render_template('users/new.html')

@users_bp.route('/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """ユーザー編集（本人または管理者のみ）"""
    user = User.query.get_or_404(user_id)
    
    # 権限チェック
    if not current_user.is_admin and current_user.id != user_id:
        flash('この機能は本人または管理者のみ利用できます。', 'danger')
        return redirect(url_for('books.index'))
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        
        # メールアドレス重複チェック
        if email != user.email and User.query.filter_by(email=email).first():
            flash('このメールアドレスは既に使用されています。', 'danger')
            return render_template('users/edit.html', user=user)
        
        # ユーザー情報更新
        user.name = name
        user.email = email
        
        # 管理者のみ権限変更可能
        if current_user.is_admin:
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
        
        if current_user.is_admin:
            return redirect(url_for('users.index'))
        else:
            return redirect(url_for('books.index'))
    
    return render_template('users/edit.html', user=user)

@users_bp.route('/delete/<int:user_id>', methods=['POST'])
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
        return redirect(url_for('users.index'))
    
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
    return redirect(url_for('users.index'))

@users_bp.route('/my-page')
@login_required
def my_page():
    """マイページを表示"""
    # 貸出中の書籍
    borrowed_books = Book.query.filter_by(borrower_id=current_user.id).all()
    
    # 予約中の書籍
    reservations = Reservation.query.filter_by(
        user_id=current_user.id,
        status='pending'
    ).order_by(Reservation.reservation_date).all()
    
    return render_template('users/my_page.html',
                         borrowed_books=borrowed_books,
                         reservations=reservations)