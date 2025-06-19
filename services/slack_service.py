import os
import requests
import logging
from functools import lru_cache

from models import db, User

logger = logging.getLogger(__name__)

SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_ENABLED = os.environ.get('SLACK_ENABLED', 'false').lower() in ['true', '1', 'yes']

SLACK_API_URL = 'https://slack.com/api/'

@lru_cache(maxsize=128)
def _get_slack_user_id(email):
    """メールアドレスからSlackのユーザーIDを取得する（キャッシュ付き）"""
    if not SLACK_BOT_TOKEN:
        logger.error("SLACK_BOT_TOKEN is not set.")
        return None
    
    headers = {'Authorization': f'Bearer {SLACK_BOT_TOKEN}'}
    params = {'email': email}
    
    try:
        response = requests.get(f'{SLACK_API_URL}users.lookupByEmail', headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if data.get('ok'):
            return data['user']['id']
        else:
            logger.error(f"Slack API error (users.lookupByEmail): {data.get('error')}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to call Slack API (users.lookupByEmail): {e}")
        return None

def _send_dm(user_id, message):
    """指定されたユーザーIDにDMを送信する"""
    if not SLACK_BOT_TOKEN:
        logger.error("SLACK_BOT_TOKEN is not set for sending DM.")
        return False
        
    headers = {'Authorization': f'Bearer {SLACK_BOT_TOKEN}', 'Content-Type': 'application/json'}
    payload = {
        'channel': user_id,
        'text': message,
        'username': '図書管理システム',
        'icon_emoji': ':books:'
    }
    
    try:
        response = requests.post(f'{SLACK_API_URL}chat.postMessage', headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        if data.get('ok'):
            logger.info(f"Successfully sent DM to user {user_id}")
            return True
        else:
            logger.error(f"Slack API error (chat.postMessage): {data.get('error')}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to call Slack API (chat.postMessage): {e}")
        return False

def send_slack_dm_to_user(user, message):
    """
    図書館ユーザーにSlackのDMで通知を送信する。
    SlackユーザーIDがDBになければAPIで検索し、DBに保存する。
    """
    if not SLACK_ENABLED:
        logger.info(f"Slack notifications are disabled. Would have sent DM to {user.name}: {message}")
        return True

    slack_id = user.slack_user_id
    
    if not slack_id:
        logger.info(f"Slack user ID for {user.email} not found in DB, looking up via API.")
        slack_id = _get_slack_user_id(user.email)
        
        if slack_id:
            logger.info(f"Found Slack ID {slack_id} for {user.email}. Storing it in DB.")
            user.slack_user_id = slack_id
            db.session.commit()
        else:
            logger.warning(f"Could not find Slack user ID for email: {user.email}")
            return False
            
    return _send_dm(slack_id, message)

def send_error_notification(error_message):
    """システム管理者にエラー通知を送信する"""
    if not SLACK_ENABLED:
        logger.info("Slack notifications are disabled. Skipping error notification.")
        return

    admin_email = os.environ.get('ADMIN_SLACK_EMAIL')
    if not admin_email:
        logger.warning("ADMIN_SLACK_EMAIL is not set. Cannot send error notification.")
        return

    admin_slack_id = _get_slack_user_id(admin_email)
    if not admin_slack_id:
        logger.error(f"Could not find Slack user ID for admin email: {admin_email}")
        return

    formatted_message = (
        f":rotating_light: *アプリケーションエラーが発生しました* :rotating_light:\n\n"
        f"```\n{error_message}\n```"
    )
    
    _send_dm(admin_slack_id, formatted_message) 