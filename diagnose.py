#!/usr/bin/env python
"""
Bloomy Backend Diagnostic Script
Tests configuration and module imports
"""

import os
import sys
from pathlib import Path

print("=" * 60)
print("🌿 Bloomy Backend Diagnostics")
print("=" * 60)

# Check Python version
print(f"\n✓ Python: {sys.version}")

# Check working directory
print(f"✓ Working directory: {os.getcwd()}")

# Check .env file
env_path = Path('.env')
if env_path.exists():
    print(f"✓ .env file found")
    with open('.env', 'r') as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith('FIREBASE_'):
                key = line.split('=')[0]
                print(f"  ✓ {key} configured")
else:
    print(f"✗ .env file NOT found")

# Check service account key
firebase_key = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY')
if firebase_key:
    print(f"\n✓ FIREBASE_SERVICE_ACCOUNT_KEY: {firebase_key}")
    key_path = Path(firebase_key)
    if key_path.exists():
        print(f"  ✓ Service account key file exists")
        print(f"  ✓ File size: {key_path.stat().st_size} bytes")
    else:
        print(f"  ✗ Service account key file NOT found")
        print(f"    Expected at: {key_path.absolute()}")
else:
    print(f"\n✗ FIREBASE_SERVICE_ACCOUNT_KEY not set in .env")

# Try importing modules
print("\n" + "=" * 60)
print("Testing Module Imports")
print("=" * 60)

try:
    print("\n1. Importing config.firebase_config...")
    from config.firebase_config import get_firestore_client, FIRESTORE_COLLECTIONS
    print("   ✓ firebase_config imported")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

try:
    print("2. Importing models...")
    from models.models import User, Habit, Plant, HabitLog, Streak
    print("   ✓ All models imported")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

try:
    print("3. Importing repositories...")
    from repositories.repositories import (
        UserRepository, HabitRepository, PlantRepository,
        HabitLogRepository, StreakRepository
    )
    print("   ✓ All repositories imported")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

try:
    print("4. Importing services...")
    from services.services import (
        ScoringService, PlantDecayService, StreakService, AIService
    )
    print("   ✓ All services imported")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

try:
    print("5. Importing routes...")
    from routes.auth_routes import auth_bp, user_bp
    from routes.habit_routes import habit_bp
    from routes.plant_routes import plant_bp
    print("   ✓ All routes imported")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

try:
    print("6. Importing Flask app...")
    from app import app
    print("   ✓ Flask app imported")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ All imports successful!")
print("=" * 60)

print("\n📝 To start the server, run:")
print("   python app.py")
print("\n📚 API available at:")
print("   http://localhost:5000/api/docs")
