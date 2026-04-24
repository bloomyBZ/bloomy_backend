"""
API Routes for Virtual Plant/Garden
"""

import os
from functools import wraps
from flask import Blueprint, request, jsonify
from firebase_admin import auth
from repositories.repositories import PlantRepository
from services.services import PlantDecayService

plant_bp = Blueprint('plants', __name__, url_prefix='/api/plants')

plant_repo = PlantRepository()
decay_service = PlantDecayService()

def verify_token(f):
    """Decorator to verify Firebase token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Authorization header required'}), 401

        try:
            token = auth_header.split(' ')[1]
            decoded_token = auth.verify_id_token(token)
            return f(decoded_token['uid'], *args, **kwargs)
        except Exception as e:
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


# ============== Plant Routes ==============

@plant_bp.route('/<uid>', methods=['GET'])
@verify_token
def get_plant(auth_uid, uid):
    """Get user's virtual plant status"""
    try:
        if auth_uid != uid:
            return jsonify({'error': 'Unauthorized'}), 403

        plant = plant_repo.get_plant(uid)
        if not plant:
            return jsonify({'error': 'Plant not found'}), 404

        return jsonify(plant.to_dict()), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch plant: {str(e)}'}), 500


@plant_bp.route('/<uid>/health', methods=['GET'])
@verify_token
def get_plant_health(auth_uid, uid):
    """Get plant health status"""
    try:
        if auth_uid != uid:
            return jsonify({'error': 'Unauthorized'}), 403

        plant = plant_repo.get_plant(uid)
        if not plant:
            return jsonify({'error': 'Plant not found'}), 404

        return jsonify({
            'health_score': plant.health_score,
            'growth_stage': plant.growth_stage,
            'last_decay_check': plant.last_decay_check.isoformat()
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch health: {str(e)}'}), 500


@plant_bp.route('/<uid>/health', methods=['PUT'])
@verify_token
def update_plant_health(auth_uid, uid):
    """Update plant health (typically called after habit completion)"""
    try:
        if auth_uid != uid:
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()
        health_change = data.get('health_change', 0)

        if plant_repo.update_plant_health(uid, health_change):
            updated_plant = plant_repo.get_plant(uid)
            return jsonify({
                'message': 'Plant health updated',
                'health_score': updated_plant.health_score,
                'growth_stage': updated_plant.growth_stage
            }), 200
        else:
            return jsonify({'error': 'Failed to update plant health'}), 500

    except Exception as e:
        return jsonify({'error': f'Update failed: {str(e)}'}), 500


@plant_bp.route('/<uid>/decay-check', methods=['POST'])
@verify_token
def check_plant_decay(auth_uid, uid):
    """Manually trigger decay check"""
    try:
        if auth_uid != uid:
            return jsonify({'error': 'Unauthorized'}), 403

        decayed, new_health = decay_service.check_and_apply_decay(uid)

        return jsonify({
            'message': 'Decay check completed',
            'decay_applied': decayed,
            'current_health': new_health
        }), 200

    except Exception as e:
        return jsonify({'error': f'Decay check failed: {str(e)}'}), 500


@plant_bp.route('/batch-decay', methods=['POST'])
@require_cron_secret
def batch_decay_check():
    """
    Run decay check for multiple users
    Request body: { user_ids: [uid1, uid2, ...] }
    (Usually called by background job/scheduler)
    """
    try:
        data = request.get_json()
        user_ids = data.get('user_ids', [])

        if not user_ids:
            return jsonify({'error': 'User IDs required'}), 400

        results = decay_service.batch_decay_check(user_ids)

        return jsonify({
            'message': 'Batch decay check completed',
            **results
        }), 200

    except Exception as e:
        return jsonify({'error': f'Batch check failed: {str(e)}'}), 500
