# routes/api.py
from flask import Blueprint, jsonify, request, current_app
from models import db, LoanHistory, User
from utils.decorators import api_key_required
from datetime import datetime, timedelta

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/loans', methods=['GET'])
@api_key_required
def get_loans():
    """貸出中の書籍情報を取得する"""
    query = LoanHistory.query.filter(LoanHistory.return_date.is_(None))

    # ?overdue=true パラメータの処理
    if request.args.get('overdue') == 'true':
        query = query.filter(LoanHistory.due_date < datetime.utcnow())

    # ?due_soon_days=N パラメータの処理
    due_soon_days = request.args.get('due_soon_days', type=int)
    if due_soon_days:
        due_date_limit = datetime.utcnow() + timedelta(days=due_soon_days)
        query = query.filter(LoanHistory.due_date <= due_date_limit)

    loans = query.all()

    output = []
    for loan in loans:
        borrower_info = {
            'id': loan.borrower.id,
            'name': loan.borrower.name,
            'email': loan.borrower.email
        }
        output.append({
            'id': loan.id,
            'book_title': loan.book_title,
            'borrower': borrower_info,
            'loan_date': loan.loan_date.isoformat() + 'Z',
            'due_date': loan.due_date.isoformat() + 'Z' if loan.due_date else None,
            'is_overdue': loan.is_overdue()
        })

    return jsonify(output)

@api_bp.route('/categories/<category1>', methods=['GET'])
def get_category2_options(category1):
    """第1分類に基づいて第2分類の選択肢を取得"""
    from forms.book import CATEGORIES
    
    if category1 in CATEGORIES:
        category2_options = [{'value': option[0], 'text': option[1]} for option in CATEGORIES[category1]]
        return jsonify(category2_options)
    else:
        return jsonify([]) 