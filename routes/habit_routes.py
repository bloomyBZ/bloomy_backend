"""
API Routes for Habit Management
"""

from functools import wraps
from flask import Blueprint, request, jsonify
from firebase_admin import auth
from repositories.repositories import HabitRepository, StreakRepository
from services.services import ScoringService, StreakService, AIService

habit_bp = Blueprint('habits', __name__, url_prefix='/api/habits')

habit_repo = HabitRepository()
streak_repo = StreakRepository()
scoring_service = ScoringService()
streak_service = StreakService()
ai_service = AIService()

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


# ============== Habit CRUD Routes ==============

@habit_bp.route('', methods=['POST'])
@verify_token
def create_habit(uid):
    """Create a new habit"""
    try:
        data = request.get_json()
        name = data.get('name')
        frequency = data.get('frequency', 'daily')
        description = data.get('description', '')
        icon = data.get('icon', '📍')

        if not name:
            return jsonify({'error': 'Habit name is required'}), 400

        habit_id = habit_repo.create_habit(
            user_id=uid,
            name=name,
            frequency=frequency,
            description=description,
            icon=icon
        )

        if habit_id:
            # Initialize streak for new habit
            streak_repo.create_streak(uid, habit_id)

            return jsonify({
                'message': 'Habit created successfully',
                'habit_id': habit_id
            }), 201
        else:
            return jsonify({'error': 'Failed to create habit'}), 500

    except Exception as e:
        return jsonify({'error': f'Creation failed: {str(e)}'}), 500


@habit_bp.route('/<habit_id>', methods=['GET'])
def get_habit(habit_id):
    """Get habit details"""
    try:
        habit = habit_repo.get_habit(habit_id)
        if not habit:
            return jsonify({'error': 'Habit not found'}), 404

        return jsonify(habit.to_dict()), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch habit: {str(e)}'}), 500


@habit_bp.route('/user/<uid>', methods=['GET'])
@verify_token
def get_user_habits(auth_uid, uid):
    """Get all habits for a user"""
    try:
        if auth_uid != uid:
            return jsonify({'error': 'Unauthorized'}), 403

        habits = habit_repo.get_user_habits(uid)
        habits_data = [habit.to_dict() for habit in habits]

        return jsonify({
            'habits': habits_data,
            'count': len(habits_data)
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch habits: {str(e)}'}), 500


@habit_bp.route('/user/<uid>/recommendations', methods=['GET'])
@verify_token
def get_habit_recommendations(auth_uid, uid):
    """Get personalized habit recommendations based on existing habits"""
    try:
        if auth_uid != uid:
            return jsonify({'error': 'Unauthorized'}), 403

        limit = request.args.get('limit', default=5, type=int)
        recommendations = ai_service.recommend_habits(uid, limit=limit)

        return jsonify({
            'recommendations': recommendations,
            'count': len(recommendations)
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch recommendations: {str(e)}'}), 500


@habit_bp.route('/<habit_id>', methods=['PUT'])
@verify_token
def update_habit(uid, habit_id):
    """Update habit"""
    try:
        habit = habit_repo.get_habit(habit_id)
        if not habit or habit.user_id != uid:
            return jsonify({'error': 'Habit not found'}), 404

        data = request.get_json()
        allowed_fields = ['name', 'frequency', 'description', 'icon']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}

        if habit_repo.update(habit_id, update_data):
            updated_habit = habit_repo.get_habit(habit_id)
            return jsonify(updated_habit.to_dict()), 200
        else:
            return jsonify({'error': 'Failed to update habit'}), 500

    except Exception as e:
        return jsonify({'error': f'Update failed: {str(e)}'}), 500


@habit_bp.route('/<habit_id>', methods=['DELETE'])
@verify_token
def delete_habit(uid, habit_id):
    """Delete a habit"""
    try:
        habit = habit_repo.get_habit(habit_id)
        if not habit or habit.user_id != uid:
            return jsonify({'error': 'Habit not found'}), 404

        if habit_repo.delete(habit_id):
            return jsonify({'message': 'Habit deleted successfully'}), 200
        else:
            return jsonify({'error': 'Failed to delete habit'}), 500

    except Exception as e:
        return jsonify({'error': f'Deletion failed: {str(e)}'}), 500


# ============== Habit Completion Routes ==============

@habit_bp.route('/<habit_id>/complete', methods=['POST'])
@verify_token
def complete_habit(uid, habit_id):
    """Complete a habit and earn points"""
    try:
        data = request.get_json() or {}
        image_url = data.get('image_url')
        notes = data.get('notes', '')

        success, points, details = scoring_service.complete_habit(
            user_id=uid,
            habit_id=habit_id,
            image_url=image_url,
            notes=notes
        )

        if success:
            return jsonify({
                'message': 'Habit completed successfully',
                'points_earned': points,
                **details
            }), 200
        else:
            return jsonify({'error': details.get('error', 'Failed to complete habit')}), 400

    except Exception as e:
        return jsonify({'error': f'Completion failed: {str(e)}'}), 500


@habit_bp.route('/<habit_id>/streak', methods=['GET'])
@verify_token
def get_habit_streak(auth_uid, habit_id):
    """Get streak information for a habit"""
    try:
        # This requires knowing the user_id - might need adjustment
        # In a real app, you'd validate the user from token

        # For now, we'll need the user to pass uid as query param or in token
        uid = request.args.get('uid')
        if not uid:
            return jsonify({'error': 'User ID required'}), 400

        if auth_uid != uid:
            return jsonify({'error': 'Unauthorized'}), 403

        streak = streak_repo.get_streak(uid, habit_id)
        if not streak:
            return jsonify({'error': 'Streak not found'}), 404

        return jsonify(streak.to_dict()), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch streak: {str(e)}'}), 500


@habit_bp.route('/<habit_id>/reset-streak', methods=['POST'])
@verify_token
def reset_habit_streak(uid, habit_id):
    """Reset streak for a habit (admin/debug only)"""
    try:
        streak_repo.update(f"{uid}_{habit_id}", {'current_streak': 0})
        return jsonify({'message': 'Streak reset successfully'}), 200

    except Exception as e:
        return jsonify({'error': f'Reset failed: {str(e)}'}), 500
