"""
API Routes for Push Notifications
"""

import os
from datetime import datetime
from functools import wraps

import requests
from flask import Blueprint, jsonify, request
from firebase_admin import auth

from repositories.repositories import HabitRepository, UserRepository

notification_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

user_repo = UserRepository()
habit_repo = HabitRepository()

EXPO_PUSH_ENDPOINT = 'https://exp.host/--/api/v2/push/send'
NOTIFICATION_TIME_OPTIONS = {'morning', 'afternoon', 'evening'}


def verify_token(f):
    """Decorator to verify Firebase token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization header required'}), 401

        try:
            token = auth_header.split(' ', 1)[1].strip()
            if not token:
                return jsonify({'error': 'Invalid token'}), 401
            decoded_token = auth.verify_id_token(token)
            return f(decoded_token['uid'], *args, **kwargs)
        except Exception:
            return jsonify({'error': 'Invalid token'}), 401

    return decorated_function


def require_cron_secret(f):
    """Optionally protect scheduler endpoints with a shared secret."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        expected_secret = os.getenv('CRON_SECRET', '').strip()
        if not expected_secret:
            return f(*args, **kwargs)

        provided_secret = request.headers.get('X-Cron-Secret', '').strip()
        if provided_secret != expected_secret:
            return jsonify({'error': 'Unauthorized'}), 401

        return f(*args, **kwargs)

    return decorated_function


def is_habit_open_today(habit) -> bool:
    """Determine whether a habit still needs attention today."""
    today_key = datetime.utcnow().date().isoformat()

    if habit_repo.is_hydration_habit(habit.name, habit.description, habit.icon):
        return getattr(habit, 'water_date', '') != today_key or getattr(habit, 'water_intake', 0) < HabitRepository.WATER_GOAL

    last_completed_at = getattr(habit, 'last_completed_at', None)
    return not last_completed_at or last_completed_at.date().isoformat() != today_key


def build_reminder_payload(user, habits, slot: str):
    """Build a push notification payload for a user."""
    pending_habits = [habit for habit in habits if is_habit_open_today(habit)]
    label = slot.capitalize()

    if pending_habits:
        first_habit = pending_habits[0].name
        title = f'Bloomy {label} reminder'
        body = f'You still have {len(pending_habits)} habit(s) open today. Start with {first_habit}.'
    else:
        title = f'Bloomy {label} check-in'
        body = 'Your habits are clear for now, but a quick check-in keeps your momentum going.'

    return {
        'to': None,
        'title': title,
        'body': body,
        'sound': 'default',
        'data': {
            'type': 'habit-reminder',
            'uid': user.uid,
            'slot': slot,
        },
    }


def send_expo_push_messages(messages):
    """Send a batch of Expo push messages."""
    if not messages:
        return {'data': []}

    response = requests.post(
        EXPO_PUSH_ENDPOINT,
        json=messages,
        headers={'Content-Type': 'application/json'},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def chunk_list(items, chunk_size):
    for index in range(0, len(items), chunk_size):
        yield items[index:index + chunk_size]


@notification_bp.route('/reminders/send', methods=['POST'])
@require_cron_secret
def send_reminders():
    """Send scheduled habit reminders to users with saved Expo push tokens."""
    try:
        data = request.get_json(silent=True) or {}
        slot = str(data.get('notification_time') or request.args.get('notification_time') or 'evening').strip().lower()

        if slot not in NOTIFICATION_TIME_OPTIONS:
            return jsonify({'error': 'notification_time must be morning, afternoon, or evening'}), 400

        eligible_users = [
            user_data
            for user_data in user_repo.query_by_field('notifications_enabled', True)
            if user_data.get('notification_time', 'evening') == slot and user_data.get('expo_push_tokens')
        ]

        messages = []
        for user_data in eligible_users:
            uid = user_data.get('uid')
            if not uid:
                continue

            user = user_repo.get_user(uid)
            if not user:
                continue

            habits = habit_repo.get_user_habits(uid)
            payload = build_reminder_payload(user, habits, slot)

            for expo_push_token in getattr(user, 'expo_push_tokens', []) or []:
                messages.append({
                    **payload,
                    'to': expo_push_token,
                })

        sent_count = 0
        for batch in chunk_list(messages, 100):
            send_expo_push_messages(batch)
            sent_count += len(batch)

        return jsonify({
            'message': 'Reminder notifications sent',
            'notification_time': slot,
            'users_targeted': len(eligible_users),
            'messages_sent': sent_count,
        }), 200

    except requests.RequestException as e:
        return jsonify({'error': f'Expo push delivery failed: {str(e)}'}), 502
    except Exception as e:
        return jsonify({'error': f'Failed to send reminders: {str(e)}'}), 500