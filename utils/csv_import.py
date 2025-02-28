import pandas as pd
import io
import csv

def validate_csv(file_path):
    """CSVファイルの形式を検証する"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            
            # 必須カラムの確認
            required_columns = ['title']  # 書籍名は必須
            for col in required_columns:
                if col not in header:
                    return False, f'必須カラム"{col}"がCSVに含まれていません。'
            
            return True, None
    except Exception as e:
        return False, f'CSVファイルの検証中にエラーが発生しました: {str(e)}'

def read_csv(file_path):
    """CSVファイルを読み込んでデータフレームを返す"""
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        return df
    except Exception as e:
        raise ValueError(f'CSVファイルの読み込み中にエラーが発生しました: {str(e)}')

def preview_csv(file_path, rows=5):
    """CSVファイルのプレビューデータを返す"""
    try:
        df = pd.read_csv(file_path, encoding='utf-8', nrows=rows)
        return df
    except Exception as e:
        raise ValueError(f'CSVファイルのプレビュー中にエラーが発生しました: {str(e)}')

def export_books_to_csv(books, file_path=None):
    """書籍データをCSVにエクスポートする"""
    # データフレームの作成
    data = []
    for book in books:
        data.append({
            'id': book.id,
            'title': book.title,
            'author': book.author,
            'category1': book.category1,
            'category2': book.category2,
            'keywords': book.keywords,
            'location': book.location,
            'is_available': 'はい' if book.is_available else 'いいえ',
            'borrower': book.borrower.name if book.borrower else ''
        })
    
    df = pd.DataFrame(data)
    
    # ファイルパスが指定されている場合はCSV出力
    if file_path:
        df.to_csv(file_path, index=False, encoding='utf-8')
        return file_path
    
    # そうでない場合はCSV文字列を返す
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, encoding='utf-8')
    return csv_buffer.getvalue()