from flask_wtf import FlaskForm
from wtforms import StringField, SelectField
from wtforms.validators import DataRequired
from models import CategoryLocationMapping

# 分類の定義
CATEGORIES = {
    '経営・マネジメント': [
        ('経営戦略・リーダーシップ', '経営戦略・リーダーシップ'),
        ('マーケティング・セールス', 'マーケティング・セールス'),
        ('オペレーション・生産管理・物流', 'オペレーション・生産管理・物流'),
        ('プロジェクトマネジメント', 'プロジェクトマネジメント'),
        ('コーポレートガバナンス・コンプライアンス', 'コーポレートガバナンス・コンプライアンス'),
        ('経営事例・ケーススタディ', '経営事例・ケーススタディ')
    ],
    '会計・ファイナンス': [
        ('会計基礎・簿記', '会計基礎・簿記'),
        ('財務・投資・ファイナンス', '財務・投資・ファイナンス'),
        ('資金調達・M&A・IPO', '資金調達・M&A・IPO'),
        ('税務・節税', '税務・節税')
    ],
    '起業・スタートアップ': [
        ('起業基礎・事業計画', '起業基礎・事業計画'),
        ('スタートアップ事例・VC', 'スタートアップ事例・VC')
    ],
    'ビジネススキル': [
        ('コミュニケーション・交渉術', 'コミュニケーション・交渉術'),
        ('ロジカルシンキング・問題解決', 'ロジカルシンキング・問題解決'),
        ('リサーチ・資料作成', 'リサーチ・資料作成')
    ],
    'キャリア・働き方': [
        ('キャリアデザイン・転職', 'キャリアデザイン・転職'),
        ('自己啓発・モチベーション', '自己啓発・モチベーション')
    ],
    '人事・組織': [
        ('採用・育成・評価制度', '採用・育成・評価制度'),
        ('労務管理・就業規則', '労務管理・就業規則'),
        ('組織行動・風土改革', '組織行動・風土改革')
    ],
    'IT・DX': [
        ('デジタルトランスフォーメーション（DX）', 'デジタルトランスフォーメーション（DX）'),
        ('ITマネジメント・セキュリティ', 'ITマネジメント・セキュリティ'),
        ('コンピュータ・IT技術', 'コンピュータ・IT技術')
    ],
    '経済学・経済情勢': [
        ('マクロ経済・経済政策', 'マクロ経済・経済政策'),
        ('ミクロ経済学・企業行動', 'ミクロ経済学・企業行動'),
        ('時事解説・ビジネス動向', '時事解説・ビジネス動向')
    ],
    '経営思想・ビジネス哲学': [
        ('経営学の巨人・古典', '経営学の巨人・古典'),
        ('経営者（リーダー）の思考・経営哲学', '経営者（リーダー）の思考・経営哲学')
    ],
    '業界・企業研究': [
        ('業界', '業界'),
        ('企業', '企業')
    ],
    '歴史・教養': [
        ('歴史', '歴史'),
        ('哲学', '哲学'),
        ('その他教養', 'その他教養')
    ]
}

class BookForm(FlaskForm):
    title = StringField('書籍名', validators=[DataRequired()])
    author = StringField('著者', validators=[DataRequired()])
    category1 = SelectField('第１分類', choices=[
        (cat, cat) for cat in CATEGORIES.keys()
    ], validators=[DataRequired()])
    category2 = SelectField('第２分類', choices=[('', '選択してください')])
    keywords = StringField('キーワード')
    location = SelectField('配置場所', choices=[])
    
    def populate_location_choices(self):
        """場所の選択肢を設定"""
        try:
            mappings = CategoryLocationMapping.query.all()
            locations = set()
            for mapping in mappings:
                if mapping.default_location:
                    locations.add(mapping.default_location)
            
            # デフォルトの場所も追加
            default_locations = ['A棚-1', 'A棚-2', 'B棚-1', 'B棚-2', 'C棚-1', 'C棚-2']
            locations.update(default_locations)
            
            self.location.choices = [('', '選択してください')] + [(loc, loc) for loc in sorted(locations)]
        except Exception:
            # エラーが発生した場合はデフォルトの選択肢を使用
            self.location.choices = [('', '選択してください'), ('A棚-1', 'A棚-1'), ('A棚-2', 'A棚-2')]
    
    def populate_category2_choices(self, category1):
        """第2分類の選択肢を設定"""
        try:
            if category1 and category1 in CATEGORIES:
                self.category2.choices = [('', '選択してください')] + CATEGORIES[category1]
            else:
                self.category2.choices = [('', '選択してください')]
        except Exception:
            self.category2.choices = [('', '選択してください')] 