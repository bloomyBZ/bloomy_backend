"""
API Routes for User Management
"""

import os
from functools import wraps
from flask import Blueprint, request, jsonify
from firebase_admin import auth
from repositories.repositories import UserRepository, PlantRepository

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
user_bp = Blueprint('users', __name__, url_prefix='/api/users')

user_repo = UserRepository()
plant_repo = PlantRepository()


def env_bool(name: str, default: bool = False) -> bool:
    """Parse boolean environment variables safely."""
    return os.getenv(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def require_auth(f):
    """Decorator to verify Firebase bearer token."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization header required'}), 401

        token = auth_header.split(' ', 1)[1].strip()
        if not token:
            return jsonify({'error': 'Invalid token'}), 401

        try:
            decoded_token = auth.verify_id_token(token)
            return f(decoded_token['uid'], *args, **kwargs)
        except Exception:
            return jsonify({'error': 'Invalid token'}), 401

    return decorated_function

# ============== Authentication Routes ==============

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user
    Request body: { email, password, display_name }
    """
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        display_name = data.get('display_name', email.split('@')[0])

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        # Create Firebase Auth user
        user = auth.create_user(
            email=email,
            password=password,
            display_name=display_name
        )

        # Create user in Firestore
        user_repo.create_user(user.uid, email, display_name)

        # Create virtual plant
        plant_repo.create_plant(user.uid)

        return jsonify({
            'message': 'User registered successfully',
            'uid': user.uid,
            'email': email,
            'display_name': display_name
        }), 201

    except auth.EmailAlreadyExistsError:
        return jsonify({'error': 'Email already exists'}), 409
    except Exception as e:
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login a user (for frontend demo purposes)
    Request body: { email, password }
    Returns user info from Firestore
    """
    try:
        is_production = os.getenv('APP_ENV', 'development').strip().lower() == 'production'
        if is_production and not env_bool('ALLOW_DEMO_LOGIN', False):
            return jsonify({
                'error': 'Demo login is disabled in production. Use Firebase client auth and ID tokens.'
            }), 403

        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        # Try to get user by email (search through all users)
        # Note: Firebase doesn't have a direct "get by email" method
        # So we'll use a workaround - attempt to verify if user exists
        # and get their data from Firestore by querying

        try:
            # Get all users and find by email (this is a workaround)
            # In production, you'd want to query Firestore directly
            users_ref = user_repo.db.collection('users')
            query = users_ref.where('email', '==', email).stream()

            user_doc = None
            for doc in query:
                user_doc = doc
                break

            if not user_doc:
                return jsonify({'error': 'User not found'}), 404

            user_data = user_doc.to_dict()
            uid = user_data.get('uid')

            # Note: In a real app, you'd verify password with Firebase
            # For now, we return the user data
            # Password verification should happen on client with Firebase SDK
            # or via Firebase REST API

            return jsonify({
                'message': 'Login successful',
                'uid': uid,
                'email': user_data.get('email'),
                'display_name': user_data.get('display_name'),
                'total_points': user_data.get('total_points', 0)
            }), 200

        except Exception as e:
            return jsonify({'error': f'Login failed: {str(e)}'}), 500

    except Exception as e:
        return jsonify({'error': f'Login error: {str(e)}'}), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Logout endpoint (frontend clears localStorage)
    This is mainly for consistency - actual logout happens on client
    """
    try:
        return jsonify({
            'message': 'Logged out successfully'
        }), 200
    except Exception as e:
        return jsonify({'error': f'Logout failed: {str(e)}'}), 500


@auth_bp.route('/verify-token', methods=['POST'])
def verify_token():
    """
    Verify Firebase ID token
    Request body: { id_token }
    """
    try:
        data = request.get_json()
        id_token = data.get('id_token')

        if not id_token:
            return jsonify({'error': 'ID token is required'}), 400

        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']

        return jsonify({
            'message': 'Token verified',
            'uid': uid,
            'email': decoded_token.get('email')
        }), 200

    except auth.InvalidIdTokenError:
        return jsonify({'error': 'Invalid ID token'}), 401
    except auth.ExpiredIdTokenError:
        return jsonify({'error': 'ID token has expired'}), 401
    except Exception as e:
        return jsonify({'error': f'Verification failed: {str(e)}'}), 500


# ============== User Routes ==============

@user_bp.route('/<uid>', methods=['GET'])
@require_auth
def get_user(auth_uid, uid):
    """Get user profile"""
    try:
        if auth_uid != uid:
            return jsonify({'error': 'Unauthorized'}), 403

        user = user_repo.get_user(uid)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify(user.to_dict()), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch user: {str(e)}'}), 500


@user_bp.route('/<uid>', methods=['PUT'])
@require_auth
def update_user(auth_uid, uid):
    """Update user profile"""
    try:
        if auth_uid != uid:
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()

        allowed_fields = ['display_name']
        update_data = {k: v for k, v in data.items() if k in allowed_fields}

        if user_repo.update(uid, update_data):
            updated_user = user_repo.get_user(uid)
            return jsonify(updated_user.to_dict()), 200
        else:
            return jsonify({'error': 'Failed to update user'}), 500

    except Exception as e:
        return jsonify({'error': f'Update failed: {str(e)}'}), 500


@user_bp.route('/<uid>/stats', methods=['GET'])
@require_auth
def get_user_stats(auth_uid, uid):
    """Get user statistics"""
    try:
        if auth_uid != uid:
            return jsonify({'error': 'Unauthorized'}), 403

        user = user_repo.get_user(uid)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        plant = plant_repo.get_plant(uid)

        return jsonify({
            'total_points': user.total_points,
            'plant_health': plant.health_score if plant else 0,
            'plant_growth_stage': plant.growth_stage if plant else 'seed'
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch stats: {str(e)}'}), 500


@user_bp.route('/<uid>/delete', methods=['DELETE'])
@require_auth
def delete_user(auth_uid, uid):
    """Delete user account (requires authentication)"""
    try:
        if auth_uid != uid:
            return jsonify({'error': 'Unauthorized'}), 403

        # Delete Firebase Auth user
        auth.delete_user(uid)

        # Delete user data from Firestore (collections)
        user_repo.delete(uid)
        plant_repo.delete(uid)

        return jsonify({'message': 'User deleted successfully'}), 200

    except Exception as e:
        return jsonify({'error': f'Deletion failed: {str(e)}'}), 500
