from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length

class AnnouncementForm(FlaskForm):
    """お知らせ作成・編集フォーム"""
    title = StringField('タイトル', validators=[
        DataRequired(message='タイトルは必須です。'),
        Length(max=200, message='タイトルは200文字以内で入力してください。')
    ])
    
    content = TextAreaField('内容', validators=[
        DataRequired(message='内容は必須です。')
    ])
    
    priority = SelectField('優先度', choices=[
        ('low', '低'),
        ('medium', '中'),
        ('high', '高')
    ], default='low', validators=[DataRequired()])
    
    is_active = BooleanField('表示する', default=True)
    
    submit = SubmitField('保存')