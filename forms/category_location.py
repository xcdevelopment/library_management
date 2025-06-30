from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length

class CategoryLocationForm(FlaskForm):
    """カテゴリ-ロケーション設定フォーム"""
    category1 = StringField('第１分類', validators=[
        DataRequired(message='第１分類は必須です。'),
        Length(max=50, message='第１分類は50文字以内で入力してください。')
    ])
    
    default_location = StringField('デフォルト場所', validators=[
        DataRequired(message='デフォルト場所は必須です。'),
        Length(max=100, message='デフォルト場所は100文字以内で入力してください。')
    ])
    
    submit = SubmitField('保存')