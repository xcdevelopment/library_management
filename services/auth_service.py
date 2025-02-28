from models import db, OperationLog
import json
from datetime import datetime

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def create_user_operation_log(user_id, action, target, details, ip_address, additional_data=None):
    """ユーザー操作ログを作成する"""
    if additional_data is None:
        additional_data = {}
    
    if 'timestamp' not in additional_data:
        additional_data['timestamp'] = datetime.utcnow()

    log = OperationLog(
        user_id=user_id,
        action=action,
        target=target,
        details=details,
        ip_address=ip_address,
        additional_data=json.dumps(additional_data, cls=DateTimeEncoder) if additional_data else None
    )
    
    db.session.add(log)
    db.session.commit()
    
    return log