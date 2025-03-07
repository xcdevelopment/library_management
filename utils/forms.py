from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField, EmailField
from wtforms.validators import DataRequired, Length, EqualTo, Email, Optional

class LoginForm(FlaskForm):
    """ログインフォーム"""
    username = StringField('ユーザー名', validators=[DataRequired(message='ユーザー名を入力してください')])
    password = PasswordField('パスワード', validators=[DataRequired(message='パスワードを入力してください')])
    remember_me = BooleanField('ログイン状態を保持する')
    submit = SubmitField('ログイン')

class BookForm(FlaskForm):
    """書籍登録・編集フォーム"""
    title = StringField('書籍名', validators=[
        DataRequired(message='書籍名を入力してください'),
        Length(max=200, message='書籍名は200文字以内で入力してください')
    ])
    author = StringField('著者', validators=[
        Length(max=100, message='著者名は100文字以内で入力してください')
    ])
    category1 = StringField('第1分類', validators=[
        Length(max=50, message='分類は50文字以内で入力してください')
    ])
    category2 = StringField('第2分類', validators=[
        Length(max=50, message='分類は50文字以内で入力してください')
    ])
    keywords = StringField('キーワード', validators=[
        Length(max=200, message='キーワードは200文字以内で入力してください')
    ])
    location = StringField('場所', validators=[
        Length(max=100, message='場所は100文字以内で入力してください')
    ])
    is_available = BooleanField('貸出可能')
    submit = SubmitField('保存')

class BookSearchForm(FlaskForm):
    """書籍検索フォーム"""
    keyword = StringField('キーワード')
    is_available = SelectField('貸出可否', choices=[('', '全て'), ('1', '貸出可能'), ('0', '貸出中')])
    category1 = SelectField('第１分類', choices=[])
    category2 = SelectField('第２分類', choices=[])
    submit = SubmitField('検索')

class BookImportForm(FlaskForm):
    """書籍インポートフォーム"""
    file = FileField('CSVファイル', validators=[
        FileRequired(message='ファイルを選択してください'),
        FileAllowed(['csv'], message='CSVファイルのみアップロード可能です')
    ])
    submit = SubmitField('インポート')

class UserForm(FlaskForm):
    """ユーザー登録・編集フォーム"""
    username = StringField('ユーザー名', validators=[
        DataRequired(message='ユーザー名を入力してください'),
        Length(min=4, max=50, message='ユーザー名は4文字以上50文字以内で入力してください')
    ])
    password = PasswordField('パスワード', validators=[
        DataRequired(message='パスワードを入力してください'),
        Length(min=6, message='パスワードは6文字以上で設定してください')
    ])
    password_confirm = PasswordField('パスワード（確認）', validators=[
        DataRequired(message='確認用パスワードを入力してください'),
        EqualTo('password', message='パスワードが一致しません')
    ])
    name = StringField('氏名', validators=[
        DataRequired(message='氏名を入力してください'),
        Length(max=100, message='氏名は100文字以内で入力してください')
    ])
    email = EmailField('メールアドレス', validators=[
        Optional(),
        Email(message='有効なメールアドレスを入力してください'),
        Length(max=120, message='メールアドレスは120文字以内で入力してください')
    ])
    is_admin = BooleanField('管理者権限')
    submit = SubmitField('保存')

class EditProfileForm(FlaskForm):
    """プロフィール編集フォーム"""
    name = StringField('氏名', validators=[
        DataRequired(message='氏名を入力してください'),
        Length(max=100, message='氏名は100文字以内で入力してください')
    ])
    email = EmailField('メールアドレス', validators=[
        Optional(),
        Email(message='有効なメールアドレスを入力してください'),
        Length(max=120, message='メールアドレスは120文字以内で入力してください')
    ])
    submit = SubmitField('更新')
