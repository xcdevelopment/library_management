from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional, ValidationError, NumberRange
from models import User

class ProfileForm(FlaskForm):
    """プロフィール編集フォーム"""
    name = StringField('氏名', validators=[DataRequired(message='氏名を入力してください')])
    email = StringField('メールアドレス', validators=[DataRequired(message='メールアドレスを入力してください'), Email(message='有効なメールアドレスを入力してください')])
    password = PasswordField('新しいパスワード', validators=[
        Optional(),
        Length(min=6, message='パスワードは6文字以上で設定してください')
    ])
    password_confirm = PasswordField('新しいパスワード（確認）', validators=[
        EqualTo('password', message='パスワードが一致しません')
    ])
    submit = SubmitField('更新')

    def validate_email(self, field):
        # 自分のメールアドレスは除外してチェック
        user = User.query.filter(User.email == field.data, User.id != self.user_id).first()
        if user:
            raise ValidationError('このメールアドレスは既に使用されています。')

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.user_id = kwargs.get('obj').id if kwargs.get('obj') else None

class NewUserForm(FlaskForm):
    """管理者用 - 新規ユーザー作成フォーム"""
    name = StringField('氏名', validators=[DataRequired(), Length(max=100)])
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    password = PasswordField('パスワード', validators=[DataRequired(), Length(min=8, message='パスワードは8文字以上で入力してください。')])
    max_loan_limit = IntegerField('最大貸出数', validators=[
        DataRequired(message='最大貸出数を入力してください'),
        NumberRange(min=1, max=10, message='最大貸出数は1冊以上10冊以下で設定してください')
    ], default=3)
    is_admin = BooleanField('管理者権限')
    submit = SubmitField('作成する')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('このメールアドレスは既に使用されています。')
            
class EditUserForm(FlaskForm):
    """管理者用 - ユーザー編集フォーム"""
    name = StringField('氏名', validators=[DataRequired(), Length(max=100)])
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    max_loan_limit = IntegerField('最大貸出数', validators=[
        DataRequired(message='最大貸出数を入力してください'),
        NumberRange(min=1, max=10, message='最大貸出数は1冊以上10冊以下で設定してください')
    ], default=3)
    is_admin = BooleanField('管理者権限')
    password = PasswordField('新しいパスワード', validators=[Optional(), Length(min=8, message='パスワードは8文字以上で入力してください。')])
    submit = SubmitField('更新する')

    def __init__(self, *args, **kwargs):
        super(EditUserForm, self).__init__(*args, **kwargs)
        # フォームの初期化時に元のユーザーオブジェクトを保存
        self.original_user = kwargs.get('obj')

    def validate_email(self, field):
        if self.original_user and self.original_user.email != field.data:
            if User.query.filter_by(email=field.data).first():
                raise ValidationError('このメールアドレスは既に使用されています。') 