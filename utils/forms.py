from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Length, EqualTo, Email, Optional

class LoginForm(FlaskForm):
    """ログインフォーム"""
    username = StringField('ユーザー名', validators=[DataRequired()])
    password = PasswordField('パスワード', validators=[DataRequired()])
    remember_me = BooleanField('ログイン状態を保持する')
    submit = SubmitField('ログイン')

class BookForm(FlaskForm):
    """書籍登録・編集フォーム"""
    title = StringField('書籍名', validators=[DataRequired()])
    author = StringField('著者')
    category1 = SelectField('第1分類', choices=[
        ('', '選択してください'),
        ('技術書', '技術書'),
        ('ビジネス', 'ビジネス'),
        ('文学', '文学'),
        # 他のカテゴリーを追加
    ])
    category2 = SelectField('第2分類', choices=[
        ('', '選択してください'),
        ('プログラミング', 'プログラミング'),
        ('データベース', 'データベース'),
        ('マネジメント', 'マネジメント'),
        # 他のカテゴリーを追加
    ])
    keywords = StringField('キーワード')
    location = StringField('場所')
    is_available = BooleanField('貸出可能', default=True)
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
        FileRequired(),
        FileAllowed(['csv'], 'CSVファイルのみアップロードできます')
    ])
    submit = SubmitField('インポート')

class UserForm(FlaskForm):
    """ユーザー登録・編集フォーム"""
    username = StringField('ユーザー名', validators=[DataRequired(), Length(min=4, max=50)])
    password = PasswordField('パスワード', validators=[
        DataRequired(), 
        Length(min=6, message='パスワードは6文字以上で設定してください。')
    ])
    password_confirm = PasswordField('パスワード（確認）', validators=[
        DataRequired(),
        EqualTo('password', message='パスワードが一致しません。')
    ])
    name = StringField('氏名', validators=[DataRequired()])
    email = StringField('メールアドレス', validators=[
        Optional(),
        Email(message='有効なメールアドレスを入力してください。')
    ])
    is_admin = BooleanField('管理者権限')
    submit = SubmitField('保存')