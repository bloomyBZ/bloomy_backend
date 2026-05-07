"""
Business Logic Services
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
import os
import re
import json
import random
import unicodedata
import requests
from google.cloud import vision
from repositories.repositories import (
    UserRepository, HabitRepository, PlantRepository,
    HabitLogRepository, StreakRepository
)

class ScoringService:
    """Habit completion and points calculation"""

    BASE_POINTS = 10
    STREAK_MULTIPLIER = 1.5
    STREAK_THRESHOLD = 3  # Days in a row
    WATER_GOAL = 7

    def __init__(self):
        self.user_repo = UserRepository()
        self.habit_repo = HabitRepository()
        self.log_repo = HabitLogRepository()
        self.streak_repo = StreakRepository()
        self.plant_repo = PlantRepository()

    def complete_habit(self, user_id: str, habit_id: str, image_url: Optional[str] = None, notes: str = "") -> Tuple[bool, int, dict]:
        """
        Complete a habit and calculate points
        Returns: (success, points_earned, details)
        """
        try:
            habit = self.habit_repo.get_habit(habit_id)
            if not habit or habit.user_id != user_id:
                return False, 0, {"error": "Habit not found"}

            if self._completed_today(habit.last_completed_at):
                return False, 0, {"error": "Habit already completed today"}

            # Update streak
            streak = self.streak_repo.update_streak(user_id, habit_id)
            self.habit_repo.update_habit_streak(habit_id, streak.current_streak)

            # Calculate points with streak bonus
            points = self._calculate_points(streak.current_streak)

            # Create log entry
            log_id = self.log_repo.create_log(
                user_id=user_id,
                habit_id=habit_id,
                points_earned=points,
                image_url=image_url,
                notes=notes
            )

            # Update user points
            self.user_repo.update_user_points(user_id, points)

            # Update plant health
            plant_health_increase = self._calculate_plant_health_bonus(points)
            self.plant_repo.update_plant_health(user_id, plant_health_increase)

            if self.habit_repo.is_hydration_habit(habit.name, habit.description, habit.icon):
                self.habit_repo.update_water_intake(
                    habit_id,
                    self.WATER_GOAL,
                    datetime.utcnow().date().isoformat(),
                )

            return True, points, {
                "log_id": log_id,
                "points_earned": points,
                "current_streak": streak.current_streak,
                "multiplier_applied": streak.current_streak >= self.STREAK_THRESHOLD
            }

        except Exception as e:
            print(f"Error completing habit: {e}")
            return False, 0, {"error": str(e)}

    def uncomplete_habit(self, user_id: str, habit_id: str) -> Tuple[bool, int, dict]:
        """Undo today's completion for a habit."""
        try:
            habit = self.habit_repo.get_habit(habit_id)
            if not habit or habit.user_id != user_id:
                return False, 0, {"error": "Habit not found"}

            if not self._completed_today(habit.last_completed_at):
                return False, 0, {"error": "Habit is not completed today"}

            habit_logs = [
                log
                for log in self.log_repo.get_habit_logs(habit_id, limit=1000)
                if log.user_id == user_id
            ]
            today = datetime.utcnow().date()
            today_logs = [log for log in habit_logs if log.timestamp.date() == today]

            if not today_logs:
                return False, 0, {"error": "No completion log found for today"}

            points_removed = sum(log.points_earned for log in today_logs)
            plant_health_removed = sum(
                self._calculate_plant_health_bonus(log.points_earned)
                for log in today_logs
            )

            for log in today_logs:
                self.log_repo.delete(log.log_id)

            if points_removed:
                self.user_repo.update_user_points(user_id, -points_removed)
            if plant_health_removed:
                self.plant_repo.update_plant_health(user_id, -plant_health_removed)

            streak = self.streak_repo.get_streak(user_id, habit_id)
            next_streak = max(0, (streak.current_streak if streak else 0) - 1)
            if streak:
                self.streak_repo.update(
                    streak.streak_id,
                    {
                        'current_streak': next_streak,
                        'updated_at': datetime.utcnow().isoformat(),
                    }
                )

            remaining_logs = [
                log
                for log in self.log_repo.get_habit_logs(habit_id, limit=1000)
                if log.user_id == user_id
            ]
            latest_remaining_log = (
                max(remaining_logs, key=lambda log: log.timestamp)
                if remaining_logs
                else None
            )
            self.habit_repo.set_completion_metadata(
                habit_id,
                streak_count=next_streak,
                last_completed_at=latest_remaining_log.timestamp if latest_remaining_log else None,
            )

            if self.habit_repo.is_hydration_habit(habit.name, habit.description, habit.icon):
                self.habit_repo.update_water_intake(
                    habit_id,
                    self.habit_repo.DEFAULT_WATER_CUPS,
                    datetime.utcnow().date().isoformat(),
                )

            return True, points_removed, {
                "points_removed": points_removed,
                "current_streak": next_streak,
                "multiplier_reversed": points_removed > self.BASE_POINTS,
            }
        except Exception as e:
            print(f"Error uncompleting habit: {e}")
            return False, 0, {"error": str(e)}

    def remove_habit_progress(self, user_id: str, habit_id: str) -> dict:
        """Reverse points and clean up logs/streak when a habit is deleted."""
        try:
            logs = [
                log
                for log in self.log_repo.get_habit_logs(habit_id, limit=1000)
                if log.user_id == user_id
            ]
            total_points = sum(log.points_earned for log in logs)
            total_health = sum(self._calculate_plant_health_bonus(log.points_earned) for log in logs)

            if total_points:
                self.user_repo.update_user_points(user_id, -total_points)
            if total_health:
                self.plant_repo.update_plant_health(user_id, -total_health)

            deleted_logs = self.log_repo.delete_logs_for_habit(habit_id)
            self.streak_repo.delete_streak(user_id, habit_id)

            return {
                "points_removed": total_points,
                "logs_removed": deleted_logs,
                "plant_health_removed": total_health,
            }
        except Exception as e:
            print(f"Error removing habit progress: {e}")
            return {
                "points_removed": 0,
                "logs_removed": 0,
                "plant_health_removed": 0,
            }

    def _calculate_points(self, current_streak: int) -> int:
        """Calculate points based on streak"""
        base = self.BASE_POINTS
        if current_streak >= self.STREAK_THRESHOLD:
            return int(base * self.STREAK_MULTIPLIER)
        return base

    def _calculate_plant_health_bonus(self, points: int) -> int:
        """Convert points to plant health increase"""
        # 10 points = 5 health points
        return max(1, points // 2)

    def _completed_today(self, completed_at: Optional[datetime]) -> bool:
        """Check whether the habit has already been completed today."""
        if not completed_at:
            return False

        completed_date = completed_at.date()
        return completed_date == datetime.utcnow().date()


class PlantDecayService:
    """Automated plant health decay for inactive users"""

    DECAY_INTERVAL_HOURS = 24
    DECAY_AMOUNT = 5  # Health points lost per interval

    def __init__(self):
        self.plant_repo = PlantRepository()
        self.habit_repo = HabitRepository()
        self.log_repo = HabitLogRepository()

    def check_and_apply_decay(self, user_id: str) -> Tuple[bool, int]:
        """
        Check if user has completed any habit in last 24 hours
        If not, decay plant health
        Returns: (decay_applied, new_health_score)
        """
        try:
            plant = self.plant_repo.get_plant(user_id)
            if not plant:
                return False, 0

            # Check if decay period has passed
            now = datetime.utcnow()
            last_check = plant.last_decay_check

            if (now - last_check).total_seconds() < (self.DECAY_INTERVAL_HOURS * 3600):
                return False, plant.health_score

            # Check if user completed any habit in last 24 hours
            recent_logs = self.log_repo.get_logs_since(user_id, hours=24)

            if not recent_logs:
                # No activity - apply decay
                self.plant_repo.update_plant_health(user_id, -self.DECAY_AMOUNT)
                self.plant_repo.update_decay_check(user_id)
                updated_plant = self.plant_repo.get_plant(user_id)
                return True, updated_plant.health_score if updated_plant else 0
            else:
                # User was active - just update check time
                self.plant_repo.update_decay_check(user_id)
                return False, plant.health_score

        except Exception as e:
            print(f"Error checking plant decay: {e}")
            return False, 0

    def batch_decay_check(self, user_ids: list) -> dict:
        """Run decay check for multiple users"""
        results = {"decayed": 0, "preserved": 0}
        for user_id in user_ids:
            decayed, _ = self.check_and_apply_decay(user_id)
            if decayed:
                results["decayed"] += 1
            else:
                results["preserved"] += 1
        return results


class StreakService:
    """Streak management and reset logic"""

    def __init__(self):
        self.streak_repo = StreakRepository()
        self.log_repo = HabitLogRepository()

    def reset_streak_if_broken(self, user_id: str, habit_id: str) -> bool:
        """
        Check if streak should be reset based on habit frequency
        Daily habits: reset if no completion in 24 hours
        """
        try:
            streak = self.streak_repo.get_streak(user_id, habit_id)
            if not streak or not streak.last_completed_date:
                return False

            now = datetime.utcnow()
            hours_since_last = (now - streak.last_completed_date).total_seconds() / 3600

            # For daily habits, reset if > 24 hours passed
            if hours_since_last > 24:
                self.streak_repo.update(
                    f"{user_id}_{habit_id}",
                    {
                        'current_streak': 0,
                        'updated_at': datetime.utcnow().isoformat()
                    }
                )
                return True
            return False

        except Exception as e:
            print(f"Error resetting streak: {e}")
            return False


class AIService:
    """AI Integration Service (Gemini + Vision with safe fallbacks)"""

    def __init__(self):
        raw_openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        # Backward compatibility: many setups already put Gemini key in OPENAI_API_KEY.
        if not self.gemini_api_key and raw_openai_key.startswith("AIza"):
            self.gemini_api_key = raw_openai_key

        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self._resolved_gemini_model: Optional[str] = None
        self._gemini_backoff_until: Optional[datetime] = None
        self.vision_api_key = os.getenv("GOOGLE_VISION_API_KEY")
        firebase_cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
        if firebase_cred_path and not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = firebase_cred_path
        self.habit_repo = HabitRepository()
        self.log_repo = HabitLogRepository()
        self._recent_recommendation_names: Dict[str, List[str]] = {}

    CATEGORY_KEYWORDS = {
        "wellness": ["su", "water", "uyku", "sleep", "meditasyon", "nefes", "wellness", "saglik", "health"],
        "fitness": ["spor", "yuruyus", "run", "kosu", "egzersiz", "workout", "fitness", "stretch"],
        "learning": ["kitap", "oku", "read", "learning", "study", "dil", "language", "kurs", "yaz"],
        "productivity": ["plan", "agenda", "to-do", "task", "odak", "focus", "calisma", "work", "journal"],
        "mindfulness": ["gratitude", "minnet", "mindful", "farkindalik", "dua", "tesekkur", "mood", "duygu"],
    }

    CATEGORY_RECOMMENDATIONS = {
        "wellness": [
            {"name": "Drink 2L of water", "frequency": "daily", "description": "Track steady water intake across the day.", "icon": "💧", "reason": "Supports a simple and sustainable health routine."},
            {"name": "Turn off screens 30 min before sleep", "frequency": "daily", "description": "Reduce late-night blue light to support better rest.", "icon": "🌙", "reason": "Helps build a calmer sleep routine."},
            {"name": "5 min breathing exercise", "frequency": "daily", "description": "Start the day with a short breathing reset.", "icon": "🫁", "reason": "Can lower stress and improve focus."},
        ],
        "fitness": [
            {"name": "10 min stretch after workouts", "frequency": "daily", "description": "Use a short stretching block to recover more smoothly.", "icon": "🤸", "reason": "Supports recovery and movement quality."},
            {"name": "8,000 steps a day", "frequency": "daily", "description": "Set a simple step target to stay active every day.", "icon": "👟", "reason": "Strengthens a steady movement routine."},
            {"name": "Strength training twice a week", "frequency": "weekly", "description": "Add regular strength sessions for balance and resilience.", "icon": "🏋️", "reason": "Supports long-term physical capacity."},
        ],
        "learning": [
            {"name": "Read 10 pages a day", "frequency": "daily", "description": "Keep learning moving with a small daily reading target.", "icon": "📚", "reason": "Makes learning easier to repeat consistently."},
            {"name": "15 min language practice", "frequency": "daily", "description": "Do a short but regular language session each day.", "icon": "🗣️", "reason": "Builds skill through steady repetition."},
            {"name": "Write a weekly learning recap", "frequency": "weekly", "description": "Summarize what you learned during the week.", "icon": "📝", "reason": "Helps ideas stick more deeply."},
        ],
        "productivity": [
            {"name": "Start the day with 3 priorities", "frequency": "daily", "description": "Define the three tasks that matter most each morning.", "icon": "🎯", "reason": "Reduces scattered attention and decision fatigue."},
            {"name": "25 min focus with Pomodoro", "frequency": "daily", "description": "Use short focus rounds to increase consistent output.", "icon": "⏱️", "reason": "Strengthens focus in manageable sessions."},
            {"name": "5 min next-day plan", "frequency": "daily", "description": "Set up tomorrow with a quick plan in the evening.", "icon": "📅", "reason": "Makes the next day feel clearer and lighter."},
        ],
        "mindfulness": [
            {"name": "3 gratitude notes a day", "frequency": "daily", "description": "Write down three things you appreciate each day.", "icon": "🙏", "reason": "Builds a lighter and more positive mindset."},
            {"name": "5 min evening journal", "frequency": "daily", "description": "Use a short end-of-day note to process your thoughts.", "icon": "💬", "reason": "Supports emotional clarity and reflection."},
            {"name": "1 digital detox hour a week", "frequency": "weekly", "description": "Create one screen-free hour for mental breathing room.", "icon": "📵", "reason": "Helps reduce mental fatigue and noise."},
        ],
    }

    DEFAULT_RECOMMENDATIONS = [
        {"name": "10 min daily walk", "frequency": "daily", "description": "Stay active with a short walk you can repeat easily.", "icon": "🚶", "reason": "A simple habit that is easy to maintain."},
        {"name": "Daily water tracking", "frequency": "daily", "description": "Keep an eye on hydration throughout the day.", "icon": "💧", "reason": "Builds a dependable baseline health routine."},
        {"name": "Read 10 pages a day", "frequency": "daily", "description": "Grow a reading habit through small daily steps.", "icon": "📖", "reason": "Creates steady learning momentum."},
        {"name": "5 min plan before sleep", "frequency": "daily", "description": "Map out tomorrow's first steps before bed.", "icon": "🗂️", "reason": "Makes the next day feel more organized."},
    ]

    def _is_gemini_available(self) -> bool:
        """Check whether Gemini API is configured."""
        if not self.gemini_api_key:
            return False

        if self._gemini_backoff_until and datetime.utcnow() < self._gemini_backoff_until:
            return False

        return True

    def _extract_retry_delay_seconds(self, error_body: Dict[str, Any]) -> int:
        """Extract retry delay in seconds from Gemini error payload."""
        try:
            details = error_body.get("error", {}).get("details", [])
            for detail in details:
                if not isinstance(detail, dict):
                    continue
                if detail.get("@type") != "type.googleapis.com/google.rpc.RetryInfo":
                    continue

                retry_delay = str(detail.get("retryDelay", "")).strip()
                if retry_delay.endswith("s"):
                    return max(5, int(float(retry_delay[:-1])))
        except Exception:
            pass

        return 30

    def _set_gemini_backoff(self, seconds: int) -> None:
        """Temporarily disable Gemini calls to avoid quota hammering."""
        safe_seconds = max(5, min(seconds, 3600))
        self._gemini_backoff_until = datetime.utcnow() + timedelta(seconds=safe_seconds)

    def _normalize_gemini_model_name(self, model_name: str) -> str:
        """Normalize model names to bare form like gemini-2.0-flash."""
        normalized = (model_name or "").strip()
        if normalized.startswith("models/"):
            normalized = normalized[len("models/"):]
        return normalized

    def _candidate_gemini_models(self) -> List[str]:
        """Return a prioritized list of candidate Gemini model names."""
        configured = self._normalize_gemini_model_name(self.gemini_model)
        candidates = [
            configured,
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash-latest",
            "gemini-1.5-pro-latest",
        ]

        seen = set()
        unique_candidates = []
        for model in candidates:
            if model and model not in seen:
                seen.add(model)
                unique_candidates.append(model)
        return unique_candidates

    def _discover_gemini_models(self) -> List[str]:
        """Discover available models that support generateContent."""
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.gemini_api_key}"
        response = requests.get(endpoint, timeout=20)
        if response.status_code >= 400:
            return []

        body = response.json()
        models = body.get("models", [])
        discovered = []
        for model in models:
            if not isinstance(model, dict):
                continue
            supported = model.get("supportedGenerationMethods", [])
            if "generateContent" not in supported:
                continue
            name = self._normalize_gemini_model_name(model.get("name", ""))
            if name:
                discovered.append(name)
        return discovered

    def _generate_with_gemini(self, prompt: str, temperature: float = 0.6, max_output_tokens: int = 512) -> str:
        """Generate text with Gemini REST API."""
        if not self._is_gemini_available():
            return ""

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
            }
        }

        model_candidates = []
        if self._resolved_gemini_model:
            model_candidates.append(self._resolved_gemini_model)
        model_candidates.extend(self._candidate_gemini_models())
        model_candidates.extend(self._discover_gemini_models())

        seen = set()
        ordered_candidates = []
        for model in model_candidates:
            if model and model not in seen:
                seen.add(model)
                ordered_candidates.append(model)

        last_error = "Gemini model resolution failed"
        for model in ordered_candidates:
            endpoint = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent?key={self.gemini_api_key}"
            )
            response = requests.post(endpoint, json=payload, timeout=20)

            if response.status_code == 404:
                last_error = f"Gemini model not found: {model}"
                continue

            if response.status_code == 429:
                error_body = {}
                try:
                    error_body = response.json()
                except Exception:
                    pass

                retry_seconds = self._extract_retry_delay_seconds(error_body)
                self._set_gemini_backoff(retry_seconds)
                return ""

            if response.status_code >= 400:
                raise ValueError(f"Gemini API error: {response.status_code} {response.text}")

            self._resolved_gemini_model = model
            body = response.json()
            candidates = body.get("candidates", [])
            if not candidates:
                return ""

            parts = candidates[0].get("content", {}).get("parts", [])
            text_parts = [part.get("text", "") for part in parts if isinstance(part, dict)]
            return "\n".join([p for p in text_parts if p]).strip()

        raise ValueError(last_error)

    def _extract_json_array(self, text: str) -> List[Dict[str, Any]]:
        """Best-effort JSON array parser for LLM responses."""
        if not text:
            return []

        stripped = text.strip()
        try:
            parsed = json.loads(stripped)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            pass

        start = stripped.find("[")
        end = stripped.rfind("]")
        if start == -1 or end == -1 or end <= start:
            return []

        try:
            parsed = json.loads(stripped[start:end + 1])
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []

    def generate_motivation_message(self, user_name: str, habit_name: str, streak: int) -> str:
        """
        Generate motivation message using Gemini API.
        Falls back to local templates if API is unavailable.
        """
        try:
            if self._is_gemini_available():
                prompt = (
                    "Kisa ve motive edici bir Turkce mesaj uret. 2 cumleyi gecme.\n"
                    f"Kullanici adi: {user_name}\n"
                    f"Tamamlanan aliskanlik: {habit_name}\n"
                    f"Streak: {streak}"
                )
                content = self._generate_with_gemini(prompt, temperature=0.8, max_output_tokens=100)
                if content:
                    return content

            fallback_messages = [
                f"Harika is cikardin {user_name}! {habit_name} icin ritmi koruyorsun.",
                f"{streak} gunluk seri cok guzel! Boyle devam et.",
                "Kucuk ama duzenli adimlar buyuk fark yaratir."
            ]
            return fallback_messages[streak % len(fallback_messages)]

        except Exception as e:
            print(f"Error generating motivation message: {e}")
            return "Devam et, harika gidiyorsun!"

    def verify_image_with_vision(self, image_url: str, habit_name: str) -> Tuple[bool, float]:
        """
        Verify habit completion via Google Vision label detection.

        Returns: (is_valid, confidence_score)
        """
        try:
            if not image_url:
                return False, 0.0

            if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                return False, 0.0

            client = vision.ImageAnnotatorClient()
            image = vision.Image()

            if image_url.startswith("http://") or image_url.startswith("https://"):
                image.source.image_uri = image_url
            else:
                with open(image_url, "rb") as image_file:
                    image.content = image_file.read()

            response = client.label_detection(image=image)
            labels = response.label_annotations or []

            if not labels:
                return False, 0.0

            habit_tokens = set(re.findall(r"[a-z0-9]+", self._normalize_text(habit_name)))
            if not habit_tokens:
                top_score = float(labels[0].score)
                return top_score >= 0.75, top_score

            best_match = 0.0
            for label in labels:
                label_text = self._normalize_text(label.description)
                label_tokens = set(re.findall(r"[a-z0-9]+", label_text))

                overlap = habit_tokens.intersection(label_tokens)
                if overlap:
                    best_match = max(best_match, float(label.score))

            if best_match > 0:
                return best_match >= 0.65, best_match

            top_score = float(labels[0].score)
            return top_score >= 0.85, top_score

        except Exception as e:
            print(f"Error verifying image: {e}")
            return False, 0.0

    def analyze_habit_patterns(self, user_id: str) -> dict:
        """
        Analyze user habit patterns with Gemini using real log data.
        """
        try:
            logs = self.log_repo.get_user_logs(user_id, limit=200)
            if not logs:
                return {
                    "best_time": "unknown",
                    "completion_rate": 0.0,
                    "recommendation": "Once a few habits are completed, I can produce better insights."
                }

            hour_counts: Dict[int, int] = {}
            daily_counts: Dict[str, int] = {}
            for log in logs:
                hour = log.timestamp.hour
                day_key = log.timestamp.strftime("%Y-%m-%d")
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
                daily_counts[day_key] = daily_counts.get(day_key, 0) + 1

            best_hour = max(hour_counts.items(), key=lambda item: item[1])[0]
            avg_per_day = sum(daily_counts.values()) / max(1, len(daily_counts))

            if self._is_gemini_available():
                prompt = (
                    "Aşağıdaki habit özetini analiz et ve SADECE JSON döndür. "
                    "Anahtarlar: best_time (morning|afternoon|evening|night), completion_rate (0..1), recommendation (string).\n"
                    f"best_hour={best_hour}, avg_per_day={avg_per_day:.2f}, total_logs={len(logs)}"
                )
                content = self._generate_with_gemini(prompt, temperature=0.3, max_output_tokens=220)
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    return parsed

            best_time = (
                "morning" if 5 <= best_hour < 12
                else "afternoon" if 12 <= best_hour < 17
                else "evening" if 17 <= best_hour < 22
                else "night"
            )

            completion_rate = min(1.0, avg_per_day / 3.0)
            return {
                "best_time": best_time,
                "completion_rate": round(completion_rate, 2),
                "recommendation": f"You are strongest around {best_time}. Try scheduling key habits in that window."
            }

        except Exception as e:
            print(f"Error analyzing patterns: {e}")
            return {}

    def recommend_habits(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Recommend habits using Gemini, with deterministic fallback."""
        try:
            habits = self.habit_repo.get_user_habits(user_id)
            existing_names = {self._normalize_text(habit.name) for habit in habits}

            ai_candidates: List[Dict[str, Any]] = []

            if self._is_gemini_available():
                prompt = (
                    "Generate new habit recommendations based on the user's current habits. "
                    "Return ONLY a JSON array. Each item must include these keys: "
                    "name, frequency (daily|weekly|custom), description, icon, reason. "
                    "Write every field in English. Do not repeat existing habits. "
                    "Return at most 10 items.\n"
                    f"Existing habits: {json.dumps(existing_names, ensure_ascii=False)}"
                )
                content = self._generate_with_gemini(prompt, temperature=0.6, max_output_tokens=700)
                ai_recommendations = self._extract_json_array(content)
                sanitized = self._sanitize_ai_recommendations(ai_recommendations, habits)
                if sanitized:
                    ai_candidates = sanitized

            fallback_candidates = self._recommend_habits_rule_based(habits, limit=max(10, limit * 4))

            combined_candidates: List[Dict[str, Any]] = []
            seen = set()
            for candidate in ai_candidates + fallback_candidates:
                name = str(candidate.get("name", "")).strip()
                normalized_name = self._normalize_text(name)
                if not name or normalized_name in seen or normalized_name in existing_names:
                    continue
                seen.add(normalized_name)
                combined_candidates.append(candidate)

            diversified = self._diversify_recommendations(user_id, combined_candidates, limit)
            if diversified:
                return diversified

            return self._recommend_habits_rule_based(habits, limit)

        except Exception as e:
            print(f"Error recommending habits: {e}")
            return self._recommend_habits_rule_based([], limit)

    def _sanitize_ai_recommendations(self, ai_items: List[Dict[str, Any]], habits: List[Any]) -> List[Dict[str, Any]]:
        """Validate and deduplicate LLM recommendation payload."""
        existing_names = {self._normalize_text(habit.name) for habit in habits}
        seen_names = set()
        output: List[Dict[str, Any]] = []

        for item in ai_items:
            if not isinstance(item, dict):
                continue

            name = str(item.get("name", "")).strip()
            frequency = str(item.get("frequency", "daily")).strip().lower()
            description = str(item.get("description", "")).strip()
            icon = str(item.get("icon", "📍")).strip() or "📍"
            reason = str(item.get("reason", "")).strip()

            if not name:
                continue

            if frequency not in {"daily", "weekly", "custom"}:
                frequency = "daily"

            normalized_name = self._normalize_text(name)
            if normalized_name in existing_names or normalized_name in seen_names:
                continue

            if self._looks_turkish_text(f"{name} {description} {reason}"):
                continue

            seen_names.add(normalized_name)
            output.append({
                "name": name,
                "frequency": frequency,
                "description": description,
                "icon": icon,
                "reason": reason if reason else "Recommended based on your current habits.",
                "confidence_score": self._estimate_confidence({"frequency": frequency}, ["ai"])
            })

        return output

    def _recommend_habits_rule_based(self, habits: List[Any], limit: int = 5) -> List[Dict[str, Any]]:
        """Rule-based fallback recommender used when AI is unavailable."""
        try:
            existing_names = {self._normalize_text(habit.name) for habit in habits}

            user_text = " ".join([f"{habit.name} {habit.description}" for habit in habits])
            normalized_user_text = self._normalize_text(user_text)

            matched_categories = self._extract_categories(normalized_user_text)

            candidates: List[Dict[str, Any]] = []
            for category in matched_categories:
                candidates.extend(self.CATEGORY_RECOMMENDATIONS.get(category, []))

            # Always keep a broad pool so each refresh can return varied results.
            candidates.extend(self.DEFAULT_RECOMMENDATIONS)
            for category_items in self.CATEGORY_RECOMMENDATIONS.values():
                candidates.extend(category_items)

            unique_recommendations: List[Dict[str, Any]] = []
            seen_names = set()

            for candidate in candidates:
                normalized_name = self._normalize_text(candidate["name"])
                if normalized_name in existing_names or normalized_name in seen_names:
                    continue

                seen_names.add(normalized_name)
                unique_recommendations.append({
                    **candidate,
                    "confidence_score": self._estimate_confidence(candidate, matched_categories)
                })

            random.shuffle(unique_recommendations)
            return unique_recommendations[:max(1, min(limit, 20))]

        except Exception as e:
            print(f"Error in fallback recommendations: {e}")
            return []

    def _diversify_recommendations(self, user_id: str, candidates: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """Rotate recommendations per user to avoid returning the same items on each refresh."""
        if not candidates:
            return []

        safe_limit = max(1, min(limit, 20))
        history = self._recent_recommendation_names.get(user_id, [])
        history_set = set(history)

        fresh_candidates = [
            candidate for candidate in candidates
            if self._normalize_text(str(candidate.get("name", ""))) not in history_set
        ]

        # If pool is exhausted, restart the cycle so we can keep returning results.
        if len(fresh_candidates) < safe_limit:
            history = []
            history_set = set()
            fresh_candidates = candidates[:]

        random.shuffle(fresh_candidates)
        selected = fresh_candidates[:safe_limit]

        for candidate in selected:
            normalized_name = self._normalize_text(str(candidate.get("name", "")))
            if normalized_name and normalized_name not in history_set:
                history.append(normalized_name)
                history_set.add(normalized_name)

        self._recent_recommendation_names[user_id] = history[-100:]
        return selected

    def _extract_categories(self, normalized_user_text: str) -> List[str]:
        """Detect likely categories from normalized habit text."""
        scores = {}
        tokens = set(re.findall(r"[a-z0-9]+", normalized_user_text))

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            keyword_hits = sum(1 for keyword in keywords if keyword in tokens)
            if keyword_hits > 0:
                scores[category] = keyword_hits

        return [cat for cat, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)]

    def _estimate_confidence(self, candidate: Dict[str, Any], matched_categories: List[str]) -> float:
        """Estimate recommendation confidence for UI sorting/display."""
        if not matched_categories:
            return 0.5
        if candidate.get("frequency") == "daily":
            return 0.85
        return 0.75

    def _looks_turkish_text(self, text: str) -> bool:
        """Detect Turkish recommendation text so we can fall back to English-safe items."""
        normalized = self._normalize_text(text)
        if re.search(r"[çğıöşü]", text.lower()):
            return True

        turkish_tokens = {
            "gunde", "gunluk", "haftada", "haftalik", "once", "sonrasi", "aksam",
            "sabah", "su", "uyku", "yuruyus", "esneme", "minnet", "duygu",
            "ertesi", "gun", "plani", "odak", "egzersizi", "aliskanliklarina",
            "onerildi", "takibi",
        }
        tokens = set(re.findall(r"[a-z0-9]+", normalized))
        return bool(tokens.intersection(turkish_tokens))

    def _normalize_text(self, text: str) -> str:
        """Normalize text for robust keyword matching and deduplication."""
        lowered = text.lower().strip()
        decomposed = unicodedata.normalize("NFKD", lowered)
        ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
        return re.sub(r"\s+", " ", ascii_text)
