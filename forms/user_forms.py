from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo

class EditProfileForm(FlaskForm):
    """プロフィール編集フォーム"""
    name = StringField('氏名', validators=[
        DataRequired(message='氏名を入力してください'),
        Length(max=100, message='氏名は100文字以内で入力してください')
    ])
    email = EmailField('メールアドレス', validators=[
        Email(message='有効なメールアドレスを入力してください'),
        Length(max=120, message='メールアドレスは120文字以内で入力してください')
    ])
    submit = SubmitField('更新')

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
        Email(message='有効なメールアドレスを入力してください'),
        Length(max=120, message='メールアドレスは120文字以内で入力してください')
    ])
    is_admin = BooleanField('管理者権限')
    submit = SubmitField('保存') 