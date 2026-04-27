"""
Repository Layer - Database Operations for Firestore
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import uuid
from config.firebase_config import get_firestore_client, FIRESTORE_COLLECTIONS
from models.models import User, Habit, Plant, HabitLog, Streak

class BaseRepository:
    """Base repository with common CRUD operations"""

    def __init__(self, collection_name: str):
        self.db = get_firestore_client()
        self.collection = collection_name

    def create(self, doc_id: str, data: Dict[str, Any]) -> bool:
        """Create a new document"""
        try:
            self.db.collection(self.collection).document(doc_id).set(data)
            return True
        except Exception as e:
            print(f"Error creating document: {e}")
            return False

    def get(self, doc_id: str) -> Optional[Dict]:
        """Get a single document"""
        try:
            doc = self.db.collection(self.collection).document(doc_id).get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            print(f"Error getting document: {e}")
            return None

    def update(self, doc_id: str, data: Dict[str, Any]) -> bool:
        """Update a document"""
        try:
            self.db.collection(self.collection).document(doc_id).update(data)
            return True
        except Exception as e:
            print(f"Error updating document: {e}")
            return False

    def delete(self, doc_id: str) -> bool:
        """Delete a document"""
        try:
            self.db.collection(self.collection).document(doc_id).delete()
            return True
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False

    def query_by_field(self, field: str, value: Any) -> List[Dict]:
        """Query documents by field"""
        try:
            docs = self.db.collection(self.collection).where(field, "==", value).stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            print(f"Error querying documents: {e}")
            return []

class UserRepository(BaseRepository):
    """User database operations"""

    def __init__(self):
        super().__init__(FIRESTORE_COLLECTIONS['users'])

    def create_user(self, uid: str, email: str, display_name: str) -> bool:
        """Create a new user"""
        user = User(
            uid=uid,
            email=email,
            display_name=display_name
        )
        return self.create(uid, user.to_dict())

    def get_user(self, uid: str) -> Optional[User]:
        """Get user by UID"""
        data = self.get(uid)
        if data:
            data['created_at'] = datetime.fromisoformat(data['created_at'])
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
            return User(**data)
        return None

    def update_user_points(self, uid: str, points: int) -> bool:
        """Add points to user's total"""
        try:
            user = self.get_user(uid)
            if user:
                new_total = user.total_points + points
                return self.update(uid, {
                    'total_points': new_total,
                    'updated_at': datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"Error updating user points: {e}")
        return False

class HabitRepository(BaseRepository):
    """Habit database operations"""

    def __init__(self):
        super().__init__(FIRESTORE_COLLECTIONS['habits'])

    def create_habit(self, user_id: str, name: str, frequency: str, description: str = "", icon: str = "📍") -> Optional[str]:
        """Create a new habit"""
        habit_id = str(uuid.uuid4())
        habit = Habit(
            habit_id=habit_id,
            user_id=user_id,
            name=name,
            frequency=frequency,
            description=description,
            icon=icon
        )
        if self.create(habit_id, habit.to_dict()):
            return habit_id
        return None

    def get_habit(self, habit_id: str) -> Optional[Habit]:
        """Get habit by ID"""
        data = self.get(habit_id)
        if data:
            data['last_completed_at'] = datetime.fromisoformat(data['last_completed_at']) if data.get('last_completed_at') else None
            data['created_at'] = datetime.fromisoformat(data['created_at'])
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
            return Habit(**data)
        return None

    def get_user_habits(self, user_id: str) -> List[Habit]:
        """Get all habits for a user"""
        habits_data = self.query_by_field('user_id', user_id)
        habits = []
        for data in habits_data:
            data['last_completed_at'] = datetime.fromisoformat(data['last_completed_at']) if data.get('last_completed_at') else None
            data['created_at'] = datetime.fromisoformat(data['created_at'])
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
            habits.append(Habit(**data))
        return habits

    def update_habit_streak(self, habit_id: str, new_streak: int) -> bool:
        """Update habit streak count"""
        return self.update(habit_id, {
            'streak_count': new_streak,
            'last_completed_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        })

class PlantRepository(BaseRepository):
    """Plant (virtual garden) database operations"""

    def __init__(self):
        super().__init__(FIRESTORE_COLLECTIONS['plants'])

    def create_plant(self, user_id: str) -> bool:
        """Create a new plant for user"""
        plant = Plant(user_id=user_id)
        return self.create(user_id, plant.to_dict())

    def get_plant(self, user_id: str) -> Optional[Plant]:
        """Get user's plant"""
        data = self.get(user_id)
        if data:
            data['last_decay_check'] = datetime.fromisoformat(data['last_decay_check'])
            data['created_at'] = datetime.fromisoformat(data['created_at'])
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
            return Plant(**data)
        return None

    def update_plant_health(self, user_id: str, health_points: int) -> bool:
        """Add health points to plant (can be negative for decay)"""
        try:
            plant = self.get_plant(user_id)
            if plant:
                new_health = max(0, min(100, plant.health_score + health_points))
                new_stage = self._calculate_growth_stage(new_health)
                return self.update(user_id, {
                    'health_score': new_health,
                    'growth_stage': new_stage,
                    'updated_at': datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"Error updating plant health: {e}")
        return False

    def update_decay_check(self, user_id: str) -> bool:
        """Update last decay check timestamp"""
        return self.update(user_id, {
            'last_decay_check': datetime.utcnow().isoformat()
        })

    def _calculate_growth_stage(self, health_score: int) -> str:
        """Calculate growth stage based on health score"""
        if health_score < 25:
            return "seed"
        elif health_score < 50:
            return "seedling"
        elif health_score < 100:
            return "plant"
        else:
            return "flower"

class HabitLogRepository(BaseRepository):
    """Habit log (completion records) database operations"""

    def __init__(self):
        super().__init__(FIRESTORE_COLLECTIONS['logs'])

    def create_log(self, user_id: str, habit_id: str, points_earned: int, image_url: Optional[str] = None, notes: str = "") -> Optional[str]:
        """Create a new habit completion log"""
        log_id = str(uuid.uuid4())
        log = HabitLog(
            log_id=log_id,
            user_id=user_id,
            habit_id=habit_id,
            points_earned=points_earned,
            image_url=image_url,
            notes=notes
        )
        if self.create(log_id, log.to_dict()):
            return log_id
        return None

    def get_user_logs(self, user_id: str, limit: int = 100) -> List[HabitLog]:
        """Get user's habit logs with limit"""
        logs_data = self.query_by_field('user_id', user_id)
        logs = []
        for data in logs_data[:limit]:
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
            logs.append(HabitLog(**data))
        return logs

    def get_habit_logs(self, habit_id: str, limit: int = 50) -> List[HabitLog]:
        """Get logs for a specific habit"""
        logs_data = self.query_by_field('habit_id', habit_id)
        logs = []
        for data in logs_data[:limit]:
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
            logs.append(HabitLog(**data))
        return logs

    def get_logs_since(self, user_id: str, hours: int = 24) -> List[HabitLog]:
        """Get logs from the last N hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        all_logs = self.get_user_logs(user_id)
        return [log for log in all_logs if log.timestamp > cutoff_time]

class StreakRepository(BaseRepository):
    """Streak tracking database operations"""

    def __init__(self):
        super().__init__(FIRESTORE_COLLECTIONS['streaks'])

    def create_streak(self, user_id: str, habit_id: str) -> bool:
        """Create a new streak tracker"""
        streak_id = f"{user_id}_{habit_id}"
        streak = Streak(
            streak_id=streak_id,
            user_id=user_id,
            habit_id=habit_id
        )
        return self.create(streak_id, streak.to_dict())

    def get_streak(self, user_id: str, habit_id: str) -> Optional[Streak]:
        """Get streak for a habit"""
        streak_id = f"{user_id}_{habit_id}"
        data = self.get(streak_id)
        if data:
            data['last_completed_date'] = datetime.fromisoformat(data['last_completed_date']) if data.get('last_completed_date') else None
            data['created_at'] = datetime.fromisoformat(data['created_at'])
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
            return Streak(**data)
        return None

    def update_streak(self, user_id: str, habit_id: str, increment: int = 1) -> Optional[Streak]:
        """Increment streak count"""
        streak_id = f"{user_id}_{habit_id}"
        streak = self.get_streak(user_id, habit_id)

        if not streak:
            self.create_streak(user_id, habit_id)
            streak = self.get_streak(user_id, habit_id)

        new_streak = streak.current_streak + increment
        new_longest = max(streak.longest_streak, new_streak)

        self.update(streak_id, {
            'current_streak': new_streak,
            'longest_streak': new_longest,
            'last_completed_date': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        })

        return self.get_streak(user_id, habit_id)


class TrashRepository(BaseRepository):
    """Trash management for deleted items (undo functionality)"""

    def __init__(self):
        super().__init__(FIRESTORE_COLLECTIONS['trash'])

    def trash_habit(self, habit_id: str, habit_data: Dict[str, Any]) -> bool:
        """Move a habit to trash (for undo functionality)"""
        try:
            trash_id = f"habit_{habit_id}"
            trash_entry = {
                'original_id': habit_id,
                'item_type': 'habit',
                'data': habit_data,
                'deleted_at': datetime.utcnow().isoformat(),
                'user_id': habit_data.get('user_id'),
                'expires_at': (datetime.utcnow() + timedelta(hours=24)).isoformat()  # Auto-delete after 24 hours
            }
            return self.create(trash_id, trash_entry)
        except Exception as e:
            print(f"Error trashing habit: {e}")
            return False

    def restore_habit(self, habit_id: str) -> Optional[Dict]:
        """Restore a habit from trash"""
        try:
            trash_id = f"habit_{habit_id}"
            trash_data = self.get(trash_id)
            
            if not trash_data:
                return None

            # Check if trash item has expired
            expires_at = datetime.fromisoformat(trash_data['expires_at'])
            if datetime.utcnow() > expires_at:
                # Delete expired trash
                self.delete(trash_id)
                return None

            # Restore the habit
            habit_data = trash_data['data']
            habit_repo = HabitRepository()
            
            if habit_repo.create(habit_id, habit_data):
                # Remove from trash
                self.delete(trash_id)
                return habit_data
            
            return None
        except Exception as e:
            print(f"Error restoring habit: {e}")
            return None

    def get_user_trash(self, user_id: str) -> List[Dict]:
        """Get all trashed items for a user"""
        try:
            trash_items = self.query_by_field('user_id', user_id)
            # Filter out expired items
            valid_items = []
            for item in trash_items:
                expires_at = datetime.fromisoformat(item['expires_at'])
                if datetime.utcnow() <= expires_at:
                    valid_items.append(item)
                else:
                    # Clean up expired items
                    self.delete(item.get('original_id', ''))
            return valid_items
        except Exception as e:
            print(f"Error getting user trash: {e}")
            return []

    def empty_trash(self, user_id: str) -> bool:
        """Permanently delete all trash for a user"""
        try:
            trash_items = self.query_by_field('user_id', user_id)
            for item in trash_items:
                trash_id = f"habit_{item.get('original_id', '')}"
                self.delete(trash_id)
            return True
        except Exception as e:
            print(f"Error emptying trash: {e}")
            return False
