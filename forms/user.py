from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, Length

class UserForm(FlaskForm):
    username = StringField('ユーザー名', validators=[
        DataRequired(message='ユーザー名は必須です'),
        Length(min=3, max=50, message='ユーザー名は3文字以上50文字以下で入力してください')
    ])
    name = StringField('氏名', validators=[
        DataRequired(message='氏名は必須です'),
        Length(max=100, message='氏名は100文字以下で入力してください')
    ])
    email = StringField('メールアドレス', validators=[
        Email(message='有効なメールアドレスを入力してください'),
        Length(max=120, message='メールアドレスは120文字以下で入力してください')
    ])
    password = PasswordField('パスワード', validators=[
        DataRequired(message='パスワードは必須です'),
        Length(min=6, message='パスワードは6文字以上で入力してください'),
        EqualTo('confirm_password', message='パスワードが一致しません')
    ])
    confirm_password = PasswordField('パスワード（確認）')
    is_admin = BooleanField('管理者権限') 