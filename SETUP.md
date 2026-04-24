# 🚀 Bloomy Backend Setup Guide

## Quick Start (5 minutes)

### Step 1: Install Python Dependencies
```bash
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### Step 2: Configure Firebase

1. **Create Firebase Project**
   - Go to [console.firebase.google.com](https://console.firebase.google.com)
   - Click "Create a new project"
   - Name it "Bloomy" (or similar)
   - Enable the default settings

2. **Set Up Firestore Database**
   - In left menu: Firestore Database
   - Create database
   - Start in test mode (for development)
   - Choose region (e.g., us-central1)

3. **Enable Authentication**
   - In left menu: Authentication
   - Click "Get started"
   - Enable "Email/Password" provider
   - (Optional) Enable "Google" provider

4. **Generate Service Account Key**
   - Project Settings (gear icon) → Service Accounts
   - Click "Generate New Private Key"
   - Download `serviceAccountKey.json`
   - **IMPORTANT**: Save this file securely, keep it private!

### Step 3: Configure Environment

```bash
# Copy the example to .env
cp .env.example .env

# Edit .env and add your Firebase credentials
```

**In `.env`, update these lines:**
```
FIREBASE_SERVICE_ACCOUNT_KEY=./serviceAccountKey.json
FIREBASE_PROJECT_ID=your-firebase-project-id
```

Where to find `FIREBASE_PROJECT_ID`:
- Firebase Console → Project Settings → General tab
- Look for "Project ID" field

### Step 4: Run the Server

**Windows:**
```bash
start.bat
```

**macOS/Linux:**
```bash
bash start.sh
```

**Or manually:**
```bash
python app.py
```

You should see:
```
╔═════════════════════════════════════════╗
║        🌿 Bloomy API Server 🌿          ║
║      Smart Habit Tracking App            ║
╚═════════════════════════════════════════╝

 * Running on http://0.0.0.0:5000
```

## ✅ Verify Installation

### Test 1: Health Check
```bash
curl http://localhost:5000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-04-04T12:00:00"
}
```

### Test 2: API Documentation
```
http://localhost:5000/api/docs
```

### Test 3: Register a User
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123",
    "display_name": "Test User"
  }'
```

## 🔧 Firebase Firestore Setup

After the first registration, your Firestore should auto-create these collections:

```
Firestore Database
├── users/
│   └── {uid}/
│       ├── uid: "..."
│       ├── email: "user@example.com"
│       ├── display_name: "User Name"
│       ├── total_points: 0
│       └── created_at: "2026-04-04T..."
│
├── habits/
│   └── {habit_id}/
│       ├── habit_id: "..."
│       ├── user_id: "{uid}"
│       ├── name: "Drink Water"
│       ├── frequency: "daily"
│       ├── streak_count: 0
│       └── ...
│
├── plants/
│   └── {uid}/
│       ├── user_id: "{uid}"
│       ├── health_score: 100
│       ├── growth_stage: "seed"
│       └── ...
│
├── logs/
│   └── {log_id}/
│       ├── log_id: "..."
│       ├── user_id: "{uid}"
│       ├── habit_id: "{habit_id}"
│       ├── timestamp: "..."
│       └── points_earned: 10
│
└── streaks/
    └── {user_id}_{habit_id}/
        ├── streak_id: "..."
        ├── current_streak: 0
        ├── longest_streak: 0
        └── ...
```

## 🎯 Project Structure Overview

```
bloomy-backend/
├── 📄 app.py                 ← Main Flask app (run this!)
├── 📄 requirements.txt       ← Python dependencies
├── 📄 .env.example           ← Environment template
├── 📄 README.md              ← Full documentation
├── 📄 SETUP.md               ← This file
│
├── 📁 config/
│   └── firebase_config.py    ← Firebase setup & initialization
│
├── 📁 models/
│   └── models.py             ← Data classes (User, Habit, Plant, etc.)
│
├── 📁 repositories/
│   └── repositories.py       ← Database operations (CRUD)
│                             ← Firestore queries
│
├── 📁 services/
│   └── services.py           ← Business logic
│                             ├─ ScoringService (points, streaks)
│                             ├─ PlantDecayService (24h health loss)
│                             ├─ StreakService (streak management)
│                             └─ AIService (OpenAI, Vision mocks)
│
├── 📁 routes/
│   ├── auth_routes.py        ← Authentication endpoints
│   ├── habit_routes.py       ← Habit CRUD + completion
│   └── plant_routes.py       ← Plant status & decay
│
├── 📁 utils/
│   └── helpers.py            ← Utility functions & calculators
│
└── 📁 logs/
    └── (created at runtime)
```

## 📚 Key Files Explained

### `config/firebase_config.py`
- Initializes Firebase Admin SDK
- Loads environment variables
- Provides `get_firestore_client()` function
- Defines configuration classes for dev/prod

**Usage:**
```python
from config.firebase_config import get_firestore_client
db = get_firestore_client()
```

### `models/models.py`
- Defines dataclasses: `User`, `Habit`, `Plant`, `HabitLog`, `Streak`
- Includes conversion to Firestore-compatible format
- Example: `user.to_dict()` for database storage

### `repositories/repositories.py`
- `UserRepository` - User CRUD operations
- `HabitRepository` - Habit management
- `PlantRepository` - Plant health updates
- `HabitLogRepository` - Log completion records
- `StreakRepository` - Streak tracking
- Base class with common CRUD methods

**Usage:**
```python
habit_repo = HabitRepository()
habits = habit_repo.get_user_habits(user_id)
```

### `services/services.py`
- **ScoringService**: Points calculation with streak bonuses
  - `complete_habit()` - Process habit completion
  - `_calculate_points()` - Apply multipliers

- **PlantDecayService**: Health decay for inactive users
  - `check_and_apply_decay()` - 24-hour decay check
  - `batch_decay_check()` - Run for multiple users

- **StreakService**: Streak reset logic

- **AIService**: OpenAI & Vision API mocks
  - `generate_motivation_message()` - Motivational text
  - `verify_image_with_vision()` - Image validation

### `routes/`
Contains Flask blueprints for API endpoints:
- `/api/auth/*` - User authentication
- `/api/users/*` - Profile management
- `/api/habits/*` - Habit operations
- `/api/plants/*` - Plant status

## 🔐 Security Checklist

- [ ] `serviceAccountKey.json` added to `.gitignore`
- [ ] `.env` file added to `.gitignore`
- [ ] Firebase Auth enabled for email/password
- [ ] Firestore rules reviewed (test mode allows all reads/writes)
- [ ] CORS origins configured for your frontend
- [ ] Environment variables set in production

**Production Firestore Rules (Read the README section "Security Features"):**
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{uid} {
      allow read, write: if request.auth.uid == uid;
    }
    match /habits/{doc=**} {
      allow read, write: if request.auth != null;
    }
    match /logs/{doc=**} {
      allow read, write: if request.auth != null;
    }
    match /plants/{uid} {
      allow read, write: if request.auth.uid == uid;
    }
  }
}
```

## 🌐 Frontend Integration

### React Web
```javascript
// Set CORS origin
const API_URL = 'http://localhost:5000';

// Send Firebase ID token
const token = await user.getIdToken();
fetch(`${API_URL}/api/habits`, {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
```

### Flutter/React Native
```dart
// Similar to React, include Authorization header
final token = await FirebaseAuth.instance.currentUser!.getIdToken();
http.get(
  Uri.parse('http://your-api-url/api/habits'),
  headers: {'Authorization': 'Bearer $token'},
);
```

## 🧪 Testing Workflow

### 1. Register User
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"pass123","display_name":"Tester"}'
```
Save the returned `uid`

### 2. Get ID Token
```bash
# Use Firebase Console or SDK to get ID token for the user
# For testing: Use Firebase REST API
curl -X POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=YOUR_API_KEY \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"pass123","returnSecureToken":true}'
```
Save the returned `idToken`

### 3. Create Habit
```bash
curl -X POST http://localhost:5000/api/habits \
  -H "Authorization: Bearer YOUR_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Drink Water","frequency":"daily","icon":"💧"}'
```

### 4. Complete Habit
```bash
curl -X POST http://localhost:5000/api/habits/HABIT_ID/complete \
  -H "Authorization: Bearer YOUR_ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"notes":"Completed!"}'
```

### 5. Check Plant
```bash
curl http://localhost:5000/api/plants/USER_UID
```

## 🚨 Common Issues & Solutions

### Issue: "Firebase initialization error"
**Solution**: Check your `serviceAccountKey.json` path in `.env`
```bash
# Verify file exists
ls -la ./serviceAccountKey.json
```

### Issue: "License not found at FIREBASE_SERVICE_ACCOUNT_KEY"
**Solution**: Escape backslashes in Windows path
```
# Bad:
FIREBASE_SERVICE_ACCOUNT_KEY=C:\path\to\serviceAccountKey.json

# Good:
FIREBASE_SERVICE_ACCOUNT_KEY=./serviceAccountKey.json
# Or:
FIREBASE_SERVICE_ACCOUNT_KEY=C:/path/to/serviceAccountKey.json
```

### Issue: CORS errors from frontend
**Solution**: Add your frontend URL to `cors_config` in `app.py`
```python
"origins": [
    "http://localhost:3000",  # Your React app
    "http://your-deployed-domain.com",
],
```

### Issue: Token verification fails
**Solution**: Ensure token is fresh and from correct Firebase project
- Tokens expire after 1 hour
- Verify `FIREBASE_PROJECT_ID` matches Firebase Console

## 📦 Deployment Options

### Option 1: Heroku (Free tier ended, but still good)
```bash
heroku login
heroku create bloomy-api
git push heroku main
```

### Option 2: Google Cloud Run
```bash
gcloud run deploy bloomy-api --source .
```

### Option 3: AWS Lambda + API Gateway
- Use Zappa framework for deployment

### Option 4: DigitalOcean App Platform
- Connect GitHub repo, auto-deploys on push

## 📞 Support & Next Steps

### Next: AI Integration
To enable real AI features, update `services/services.py`:

1. **Motivation Messages (OpenAI)**
   ```python
   import openai
   openai.api_key = os.getenv('OPENAI_API_KEY')
   response = openai.ChatCompletion.create(
       model="gpt-3.5-turbo",
       messages=[...prompt...]
   )
   ```

2. **Image Verification (Vision API)**
   ```python
   from google.cloud import vision
   client = vision.ImageAnnotatorClient()
   # Analyze image for habit evidence
   ```

### Next: Background Tasks
Set up periodic decay checks:
1. Cloud Scheduler → HTTP request to `/api/plants/batch-decay`
2. Or use APScheduler for local testing

## 📖 Resources

- [Firebase Admin Python Docs](https://firebase.google.com/docs/database/admin/start)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Firestore Data Model](https://firebase.google.com/docs/firestore/data-model)
- [REST API Basics](https://www.restfulapi.net/)

---

**Ready to start?** Run `start.bat` (Windows) or `bash start.sh` (macOS/Linux)! 🌿
