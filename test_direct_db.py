"""
Test Script: Create All Collections Using Direct Database Access
This bypasses the need for Firebase API key
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.firebase_config import get_firestore_client, FIRESTORE_COLLECTIONS
from models.models import User, Habit, Plant, HabitLog, Streak
from repositories.repositories import (
    UserRepository, HabitRepository, PlantRepository,
    HabitLogRepository, StreakRepository
)

print("=" * 60)
print("Bloomy - Direct Database Test - Create All Collections")
print("=" * 60)

# Initialize repositories
user_repo = UserRepository()
habit_repo = HabitRepository()
plant_repo = PlantRepository()
log_repo = HabitLogRepository()
streak_repo = StreakRepository()

# Test user (use existing or create new)
test_uid = "test_user_direct_access_001"
test_email = "direct_test@example.com"
test_display_name = "Direct Test User"

print("\n" + "="*60)
print("STEP 1: Create User (if not exists)")
print("="*60)

try:
    existing_user = user_repo.get_user(test_uid)
    if existing_user:
        print(f"[OK] User already exists: {existing_user.display_name}")
    else:
        print(f"Creating new user...")
        user_repo.create_user(test_uid, test_email, test_display_name)
        print(f"[OK] User created: {test_display_name}")

    # Ensure plant exists
    existing_plant = plant_repo.get_plant(test_uid)
    if not existing_plant:
        plant_repo.create_plant(test_uid)
        print(f"[OK] Plant created for user")

    print(f"\nCollections created:")
    print(f"   [OK] users/")
    print(f"   [OK] plants/")

except Exception as e:
    print(f"[ERROR] {e}")
    sys.exit(1)

print("\n" + "="*60)
print("STEP 2: Create Habit")
print("="*60)

try:
    habit_name = "Morning Meditation"
    habit_frequency = "daily"

    print(f"Creating habit: {habit_name}")

    habit_id = habit_repo.create_habit(
        user_id=test_uid,
        name=habit_name,
        frequency=habit_frequency,
        description="10 minutes of meditation each morning",
        icon="Meditation"
    )

    if habit_id:
        print(f"[OK] Habit created: {habit_id}")

        # Also create streak entry
        streak_repo.create_streak(test_uid, habit_id)
        print(f"[OK] Streak tracking initialized")

        print(f"\nCollections created:")
        print(f"   [OK] users/")
        print(f"   [OK] plants/")
        print(f"   [OK] habits/      (NEW!)")
    else:
        print(f"[ERROR] Failed to create habit")
        sys.exit(1)

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("STEP 3: Complete Habit")
print("="*60)

try:
    print(f"Completing habit...")

    # Create a log entry
    log_id = log_repo.create_log(
        user_id=test_uid,
        habit_id=habit_id,
        points_earned=10,
        notes="Completed morning meditation session"
    )

    if log_id:
        print(f"[OK] Habit completion logged: {log_id}")

        # Update streak
        streak = streak_repo.update_streak(test_uid, habit_id)
        if streak:
            print(f"[OK] Streak updated: {streak.current_streak} day(s)")

        # Update user points
        user_repo.update_user_points(test_uid, 10)
        print(f"[OK] Points awarded: +10")

        # Update plant health
        plant_repo.update_plant_health(test_uid, 5)
        plant = plant_repo.get_plant(test_uid)
        if plant:
            print(f"[OK] Plant health increased: {plant.health_score}/100")

        print(f"\nCollections created:")
        print(f"   [OK] users/")
        print(f"   [OK] plants/")
        print(f"   [OK] habits/")
        print(f"   [OK] logs/        (NEW!)")
        print(f"   [OK] streaks/     (NEW!)")
    else:
        print(f"[ERROR] Failed to create log")
        sys.exit(1)

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("STEP 4: Retrieve Data")
print("="*60)

try:
    # Get user
    user = user_repo.get_user(test_uid)
    print(f"User: {user.display_name}")
    print(f"   Points: {user.total_points}")
    print(f"   Created: {user.created_at}")

    # Get habit
    habit = habit_repo.get_habit(habit_id)
    print(f"\nHabit: {habit.name}")
    print(f"   Frequency: {habit.frequency}")
    print(f"   Streak: {habit.streak_count}")

    # Get plant
    plant = plant_repo.get_plant(test_uid)
    if plant:
        print(f"\nPlant:")
        print(f"   Health: {plant.health_score}/100")
        print(f"   Stage: {plant.growth_stage}")
    else:
        print(f"\n[WARN] Plant not found, creating...")
        plant_repo.create_plant(test_uid)
        plant = plant_repo.get_plant(test_uid)
        if plant:
            print(f"   Health: {plant.health_score}/100")
            print(f"   Stage: {plant.growth_stage}")

    # Get logs
    logs = log_repo.get_user_logs(test_uid)
    print(f"\nLogs: {len(logs)} completion(s)")
    for i, log in enumerate(logs[:3], 1):
        print(f"   {i}. Habit: {log.habit_id}")
        print(f"      Points: {log.points_earned}")
        print(f"      Time: {log.timestamp}")

    # Get streak
    streak = streak_repo.get_streak(test_uid, habit_id)
    print(f"\nStreak:")
    print(f"   Current: {streak.current_streak}")
    print(f"   Longest: {streak.longest_streak}")

except Exception as e:
    print(f"[ERROR] Error retrieving data: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("TEST COMPLETE!")
print("="*60)

print(f"""
All collections successfully created and populated!

Test Data Created:
  * User: {test_display_name} (UID: {test_uid})
  * Habit: {habit_name} (ID: {habit_id})
  * Habit Log: 1 completion
  * Streak: Active (1 day)

Firestore Collections:
  [OK] users/
  [OK] plants/
  [OK] habits/
  [OK] logs/
  [OK] streaks/

Next Steps:
  1. Check Firestore Console to see the data
  2. Complete the habit again to increase streak
  3. Test API endpoints with curl/Postman
  4. Monitor plant growth as you complete habits
""")
