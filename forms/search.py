from flask_wtf import FlaskForm
from wtforms import StringField, SelectField
from wtforms.validators import Optional
from forms.book import CATEGORIES

class SearchForm(FlaskForm):
    keyword = StringField('キーワード', validators=[Optional()])
    category1 = SelectField('第１分類', choices=[('', '選択してください')] + [(cat, cat) for cat in CATEGORIES.keys()], validators=[Optional()])
    category2 = SelectField('第２分類', choices=[('', '選択してください')], validators=[Optional()]) 