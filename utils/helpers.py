"""
Utility Functions and Helpers
"""

from datetime import datetime, timedelta
from typing import Optional

def get_today_start() -> datetime:
    """Get start of today (midnight UTC)"""
    now = datetime.utcnow()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)

def get_today_end() -> datetime:
    """Get end of today (23:59:59 UTC)"""
    start = get_today_start()
    return start + timedelta(days=1) - timedelta(seconds=1)

def hours_since(dt: datetime) -> float:
    """Get hours elapsed since datetime"""
    return (datetime.utcnow() - dt).total_seconds() / 3600

def days_since(dt: datetime) -> int:
    """Get days elapsed since datetime"""
    return (datetime.utcnow() - dt).days

def format_timestamp(dt: datetime) -> str:
    """Format datetime to ISO format"""
    return dt.isoformat()

def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO format timestamp"""
    return datetime.fromisoformat(timestamp_str)

def is_same_day(dt1: datetime, dt2: datetime) -> bool:
    """Check if two datetimes are on the same day"""
    return dt1.date() == dt2.date()

def is_consecutive_day(prev_date: datetime, current_date: datetime) -> bool:
    """Check if current_date is exactly one day after prev_date"""
    delta = current_date.date() - prev_date.date()
    return delta.days == 1

class PointsCalculator:
    """Calculate points based on various factors"""

    BASE_POINTS = 10
    STREAK_BASE_MULTIPLIER = 1.5
    STREAK_THRESHOLD = 3
    MAX_STREAK_BONUS = 3.0

    @classmethod
    def calculate(cls, streak_count: int = 0, difficulty_multiplier: float = 1.0) -> int:
        """
        Calculate points with streak bonus

        Args:
            streak_count: Number of consecutive completions
            difficulty_multiplier: Habit difficulty (1.0 = normal, 1.5 = hard)

        Returns:
            Points earned
        """
        base = cls.BASE_POINTS * difficulty_multiplier

        if streak_count >= cls.STREAK_THRESHOLD:
            # Calculate multiplier: 1.5x at 3 days, up to 3.0x at very high streaks
            days_bonus = min(streak_count - cls.STREAK_THRESHOLD, 10)
            multiplier = cls.STREAK_BASE_MULTIPLIER + (days_bonus * 0.15)
            multiplier = min(multiplier, cls.MAX_STREAK_BONUS)
            return int(base * multiplier)

        return int(base)

    @classmethod
    def get_next_milestone(cls, current_streak: int) -> int:
        """Get next streak milestone"""
        milestones = [3, 7, 14, 30, 60, 100]
        for milestone in milestones:
            if current_streak < milestone:
                return milestone
        return current_streak + 30

class HealthCalculator:
    """Calculate plant health changes"""

    @staticmethod
    def points_to_health(points: int) -> int:
        """Convert points to plant health"""
        return max(1, points // 2)

    @staticmethod
    def get_stage_threshold(stage: str) -> tuple:
        """Get health range for growth stage"""
        stages = {
            'seed': (0, 25),
            'seedling': (25, 50),
            'plant': (50, 80),
            'flower': (80, 100)
        }
        return stages.get(stage, (0, 100))

class ValidationHelpers:
    """Input validation helpers"""

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    @staticmethod
    def is_valid_habit_name(name: str) -> bool:
        """Validate habit name"""
        return 1 <= len(name) <= 100

    @staticmethod
    def is_valid_frequency(frequency: str) -> bool:
        """Validate habit frequency"""
        return frequency in ['daily', 'weekly', 'custom']
