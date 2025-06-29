from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, BooleanField, SelectField, DateField, RadioField
from wtforms.validators import DataRequired, Length, Optional
from datetime import datetime, timedelta

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
    location = SelectField('場所', choices=[], validators=[
        Length(max=50, message='場所は50文字以内で入力してください')
    ])
    is_available = BooleanField('貸出可能')

class BookSearchForm(FlaskForm):
    """書籍検索フォーム"""
    keyword = StringField('キーワード')
    category1 = SelectField('第1分類', choices=[])
    category2 = SelectField('第2分類', choices=[])
    is_available = SelectField('貸出状況', choices=[
        ('', '全て'),
        ('1', '貸出可'),
        ('0', '貸出中')
    ])

class BookImportForm(FlaskForm):
    """書籍一括インポートフォーム"""
    file = FileField('CSVファイル', validators=[
        FileRequired(message='ファイルを選択してください'),
        FileAllowed(['csv'], message='CSVファイルのみアップロード可能です')
    ])

class BorrowForm(FlaskForm):
    """本の貸出フォーム"""
    due_date_option = RadioField(
        '返却期限',
        choices=[
            ('today', '本日'),
            ('1week', '1週間後'),
            ('2weeks', '2週間後（デフォルト）'),
            ('custom', 'カスタム')
        ],
        default='2weeks',
        validators=[DataRequired()]
    )
    custom_due_date = DateField(
        'カスタム返却期限',
        validators=[Optional()],
        default=lambda: datetime.now() + timedelta(weeks=2)
    )

class ExtendLoanForm(FlaskForm):
    """貸出延長フォーム"""
    extension_period = RadioField(
        '延長期間',
        choices=[
            ('1', '1週間'),
            ('2', '2週間')
        ],
        default='1',
        validators=[DataRequired(message='延長期間を選択してください')]
    ) 