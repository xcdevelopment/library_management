from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from models import User

class LoginForm(FlaskForm):
    """ログインフォーム"""
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    password = PasswordField('パスワード', validators=[DataRequired()])
    remember_me = BooleanField('ログイン状態を保持する')
    submit = SubmitField('ログイン')

class SignupForm(FlaskForm):
    """サインアップフォーム"""
    name = StringField('氏名', validators=[DataRequired(), Length(max=100, message='氏名は100文字以下で入力してください。')])
    email = StringField('メールアドレス', validators=[DataRequired(), Email(message='有効なメールアドレスを入力してください。'), Length(max=120)])
    password = PasswordField('パスワード', validators=[
        DataRequired(),
        Length(min=8, message='パスワードは8文字以上で入力してください。')
    ])
    confirm_password = PasswordField('パスワード（確認用）', validators=[
        DataRequired(),
        EqualTo('password', message='パスワードが一致しません。')
    ])
    submit = SubmitField('登録')

    def validate_email(self, email):
        """メールアドレスの重複チェック"""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('このメールアドレスは既に使用されています。') 