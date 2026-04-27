"""
Firebase Configuration and Initialization
"""

import os
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore, auth
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path, override=True)

# Firebase Configuration
FIREBASE_SERVICE_ACCOUNT_KEY = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY')
FIREBASE_API_KEY = os.getenv('FIREBASE_API_KEY')
FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID')

# Initialize Firebase Admin SDK
try:
    if FIREBASE_SERVICE_ACCOUNT_KEY:
        # Initialize with service account key (for server-to-server operations)
        cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_KEY)
        firebase_admin.initialize_app(cred)
        print("[OK] Firebase Admin SDK initialized successfully")
    else:
        print("[WARN] FIREBASE_SERVICE_ACCOUNT_KEY not found in environment")
except Exception as e:
    print(f"[ERROR] Firebase initialization error: {type(e).__name__}: {e}")

# Get Firestore client
def get_firestore_client():
    """Get Firestore database client"""
    try:
        return firestore.client()
    except Exception as e:
        print(f"Error getting Firestore client: {e}")
        return None

# Firebase collections structure
FIRESTORE_COLLECTIONS = {
    'users': 'users',
    'habits': 'habits',
    'plants': 'plants',
    'logs': 'logs',
    'streaks': 'streaks',
    'trash': 'trash',  # For tracking deleted habits for undo functionality
}

# Application configuration
class Config:
    """Base configuration"""
    DEBUG = False
    TESTING = False

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    ENV = 'development'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    ENV = 'production'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    ENV = 'testing'

# Select config based on environment
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on APP_ENV"""
    env = os.getenv('APP_ENV', 'development')
    return config.get(env, config['default'])
