"""
Bloomy - Smart Habit Tracking Application
Main Flask Application
"""

import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime

# Import blueprints
from routes.auth_routes import auth_bp, user_bp
from routes.habit_routes import habit_bp
from routes.plant_routes import plant_bp

# Initialize Flask app
app = Flask(__name__)


def env_bool(name: str, default: bool = False) -> bool:
    """Parse boolean environment variables safely."""
    return os.getenv(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def parse_cors_origins(raw_value: str):
    """Convert comma-separated origins to a list."""
    return [origin.strip() for origin in raw_value.split(',') if origin.strip()]

# ============== Configuration ==============
app_env = os.getenv('APP_ENV', 'development').strip().lower()
default_cors_origins = (
    'http://localhost:3000,'
    'http://localhost:3001,'
    'http://localhost:5173,'
    'http://127.0.0.1:3000,'
    'http://127.0.0.1:5000,'
    'http://127.0.0.1:5173'
)
cors_origins = parse_cors_origins(os.getenv('CORS_ORIGINS', default_cors_origins))

app.config['ENV'] = app_env
app.config['DEBUG'] = env_bool('DEBUG', False)
app.config['JSON_SORT_KEYS'] = False

# ============== CORS Configuration ==============
# Allow requests from mobile apps (Flutter/React Native) and web (React)
cors_config = {
    "origins": cors_origins,
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"],
    "supports_credentials": True,
    "max_age": 3600
}

# Enable CORS
CORS(app, resources={
    r"/api/*": cors_config
})

# ============== Register Blueprints ==============
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(habit_bp)
app.register_blueprint(plant_bp)

# ============== Global Routes ==============

@app.route('/', methods=['GET'])
def index():
    """Health check and API info"""
    return jsonify({
        'message': 'Bloomy API',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'status': 'running'
    }), 200


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


# ============== Error Handlers ==============

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Endpoint not found',
        'path': request.path
    }), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors"""
    return jsonify({
        'error': 'Method not allowed',
        'path': request.path
    }), 405


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        'error': 'Internal server error',
        'message': str(error)
    }), 500


# ============== Request/Response Logging ==============

@app.before_request
def log_request():
    """Log incoming request"""
    if app.debug:
        from flask import request
        print(f"[{datetime.utcnow().isoformat()}] {request.method} {request.path}")


@app.after_request
def after_request(response):
    """Add security headers"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response


# ============== API Documentation ==============

@app.route('/api/docs', methods=['GET'])
def api_docs():
    """API documentation"""
    docs = {
        'title': 'Bloomy API Documentation',
        'version': '1.0.0',
        'endpoints': {
            'Authentication': {
                'POST /api/auth/register': 'Register new user',
                'POST /api/auth/verify-token': 'Verify Firebase token'
            },
            'Users': {
                'GET /api/users/<uid>': 'Get user profile',
                'PUT /api/users/<uid>': 'Update user profile',
                'GET /api/users/<uid>/stats': 'Get user statistics',
                'DELETE /api/users/<uid>/delete': 'Delete user account'
            },
            'Habits': {
                'POST /api/habits': 'Create new habit',
                'GET /api/habits/<habit_id>': 'Get habit details',
                'GET /api/habits/user/<uid>': 'Get all user habits',
                'GET /api/habits/user/<uid>/recommendations': 'Get AI-backed habit recommendations',
                'PUT /api/habits/<habit_id>': 'Update habit',
                'DELETE /api/habits/<habit_id>': 'Delete habit',
                'POST /api/habits/<habit_id>/complete': 'Complete habit',
                'GET /api/habits/<habit_id>/streak': 'Get streak info'
            },
            'Plants': {
                'GET /api/plants/<uid>': 'Get plant status',
                'GET /api/plants/<uid>/health': 'Get plant health',
                'PUT /api/plants/<uid>/health': 'Update plant health',
                'POST /api/plants/<uid>/decay-check': 'Check plant decay',
                'POST /api/plants/batch-decay': 'Batch decay check'
            }
        }
    }
    return jsonify(docs), 200


# ============== Main Entry Point ==============

if __name__ == '__main__':
    debug_mode = env_bool('DEBUG', False)
    port = int(os.getenv('PORT', 5000))

    print("""
    ╔═════════════════════════════════════════╗
    ║        🌿 Bloomy API Server 🌿          ║
    ║      Smart Habit Tracking App            ║
    ╚═════════════════════════════════════════╝
    """)

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode,
        use_reloader=debug_mode
    )
