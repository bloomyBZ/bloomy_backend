"""
Data Models for Bloomy Habit Tracking Application
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Optional, List
from enum import Enum

class GrowthStage(Enum):
    """Plant growth stages"""
    SEED = "seed"
    SEEDLING = "seedling"
    PLANT = "plant"
    FLOWER = "flower"

class HabitFrequency(Enum):
    """Habit completion frequencies"""
    DAILY = "daily"
    WEEKLY = "weekly"
    CUSTOM = "custom"

@dataclass
class User:
    """User model"""
    uid: str
    email: str
    display_name: str
    avatar_id: str = "sprout"
    hydration_habit_dismissed: bool = False
    notifications_enabled: bool = True
    notification_time: str = "evening"
    streak_alerts_enabled: bool = True
    evening_reflection_enabled: bool = False
    total_points: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self):
        """Convert to Firestore-compatible dict"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data

@dataclass
class Habit:
    """Habit model"""
    habit_id: str
    user_id: str
    name: str
    frequency: str  # "daily", "weekly", "custom"
    schedule: str = ""
    category: str = ""
    source: str = ""
    streak_count: int = 0
    last_completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    description: str = ""
    icon: str = "📍"
    water_intake: int = 0
    water_date: str = ""

    def to_dict(self):
        """Convert to Firestore-compatible dict"""
        data = asdict(self)
        if self.last_completed_at:
            data['last_completed_at'] = self.last_completed_at.isoformat()
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data

@dataclass
class Plant:
    """Virtual plant model"""
    user_id: str
    health_score: int = 100  # 0-100
    growth_stage: str = GrowthStage.SEED.value
    last_decay_check: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self):
        """Convert to Firestore-compatible dict"""
        data = asdict(self)
        data['last_decay_check'] = self.last_decay_check.isoformat()
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data

@dataclass
class HabitLog:
    """Habit completion log"""
    log_id: str
    user_id: str
    habit_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    image_url: Optional[str] = None
    points_earned: int = 0
    notes: str = ""
    verified: bool = False

    def to_dict(self):
        """Convert to Firestore-compatible dict"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

@dataclass
class Streak:
    """Streak tracking for habits"""
    streak_id: str
    user_id: str
    habit_id: str
    current_streak: int = 0
    longest_streak: int = 0
    last_completed_date: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self):
        """Convert to Firestore-compatible dict"""
        data = asdict(self)
        if self.last_completed_date:
            data['last_completed_date'] = self.last_completed_date.isoformat()
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data
