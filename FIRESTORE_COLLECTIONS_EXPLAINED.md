# 🌿 Bloomy - Why Only users/ and plants/ Collections Exist

## The Answer: Firestore Lazy Collection Creation

**Firestore doesn't pre-create collections.** Collections are created automatically when you add the **first document** to them.

### Current State After Registration
```
✅ users/       → Created during user registration
✅ plants/      → Created during user registration
⏳ habits/       → Will be created when you create your first habit
⏳ logs/         → Will be created when you complete your first habit
⏳ streaks/      → Will be created when you complete your first habit
```

## How to Create All Collections

### Option 1: Direct Database Access (No API Key Needed) ⭐ RECOMMENDED

This script directly accesses Firestore without needing an API key:

```powershell
python test_direct_db.py
```

**What it does:**
- ✅ Creates a test user
- ✅ Creates a test habit
- ✅ Completes the habit (logs it)
- ✅ Updates streaks, points, and plant health
- ✅ Creates ALL 5 collections

**No configuration needed!** Just run it.

---

### Option 2: Complete API Workflow (Needs Firebase API Key)

Requires setting up Firebase API authentication:

1. **Get your Firebase API Key:**
   - Go to [Firebase Console](https://console.firebase.google.com)
   - Select your project
   - ⚙️ Project Settings → General tab
   - Copy the **Web API Key**

2. **Update `.env`:**
   ```
   FIREBASE_API_KEY=your_web_api_key_here
   ```

3. **Restart the server:**
   ```
   python app.py
   ```

4. **Run the test:**
   ```
   python test_complete_workflow.py
   ```

---

### Option 3: Manual Testing with PowerShell

Test individual endpoints:

```powershell
.\test_api.ps1
```

Or manually:

```powershell
# Health check
Invoke-WebRequest "http://localhost:5000/api/health" -Method GET

# Register user
$body = @{
    email = "test@example.com"
    password = "password123"
    display_name = "Test User"
} | ConvertTo-Json

Invoke-WebRequest "http://localhost:5000/api/auth/register" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

---

## 🚀 Recommended Workflow

### For Testing Right Now:
```powershell
# Run this - it creates everything
python test_direct_db.py

# Then check Firestore Console to see all collections
```

### For Production/API Testing:
1. Get Firebase API Key
2. Set it in `.env`
3. Use `test_complete_workflow.py` or call API endpoints

---

## What Each Test Script Does

| Script | Requires | Creates | Use Case |
|--------|----------|---------|----------|
| `test_direct_db.py` | Nothing | All 5 collections | Quick test, no config |
| `test_complete_workflow.py` | API Key | All 5 collections | Full workflow demo |
| `test_api.ps1` | Nothing | users, plants | Basic endpoint tests |
| `test_api.py` | Nothing | users, plants | Python version of above |

---

## Firestore Collections: What Gets Created When

```
┌─────────────────────────────────────────┐
│ User Registration                       │
├─────────────────────────────────────────┤
│ ✅ users/ (document created)            │
│ ✅ plants/ (document created)           │
│ ⏳ habits/ (waiting for first habit)    │
│ ⏳ logs/ (waiting for completion)      │
│ ⏳ streaks/ (waiting for streaks data) │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ Create Habit                            │
├─────────────────────────────────────────┤
│ ✅ users/                               │
│ ✅ plants/                              │
│ ✅ habits/ (collection created now)     │
│ ⏳ logs/                                │
│ ⏳ streaks/                             │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ Complete Habit                          │
├─────────────────────────────────────────┤
│ ✅ users/                               │
│ ✅ plants/                              │
│ ✅ habits/                              │
│ ✅ logs/ (collection created now)       │
│ ✅ streaks/ (collection created now)    │
└─────────────────────────────────────────┘
```

---

## 📝 Summary

**Your Firestore is working correctly!** Only `users/` and `plants/` exist because that's all that was created so far.

**To create all 5 collections:**
```powershell
python test_direct_db.py
```

This is normal Firestore behavior and not an error. 🎉

---

**Questions?**
- Check `SETUP.md` for Firebase configuration
- Check `README.md` for API details
- Run `test_direct_db.py` to see everything in action
