from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SubmitField

class UserImportForm(FlaskForm):
    """ユーザー一括インポートフォーム"""
    file = FileField('CSVファイル', validators=[
        FileRequired(message='ファイルを選択してください'),
        FileAllowed(['csv'], message='CSVファイルのみアップロード可能です')
    ])
    submit = SubmitField('インポート')
