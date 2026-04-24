# Bloomy Backend API Guide

This document is written for frontend integration.
It describes the current, working API behavior in this repository.

## 1. Base Info

- Base URL (local): http://localhost:5000
- API prefix: /api
- Content-Type: application/json
- Auth type: Firebase ID Token (Bearer)

Health endpoints:
- GET /
- GET /api/health
- GET /api/docs

## 2. Authentication Model (Important)

Frontend should authenticate users with Firebase client SDK and get an ID token.
Protected backend endpoints require:

Authorization: Bearer <firebase_id_token>

Ownership rule:
- For user-scoped endpoints, token UID must match UID in URL/query.
- If not matched, backend returns 403 Unauthorized.

## 3. Environment and Run

1. Install dependencies

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

2. Configure backend env

- Copy .env.example to .env
- Set at least:
  - FIREBASE_SERVICE_ACCOUNT_KEY
  - FIREBASE_PROJECT_ID
  - CORS_ORIGINS

3. Start server

```bash
python app.py
```

## 4. Endpoint Catalog

### 4.1 Auth

1. POST /api/auth/register
- Purpose: create Firebase Auth user + create Firestore user + create plant
- Auth: No
- Body:
```json
{
  "email": "user@example.com",
  "password": "strongPassword",
  "display_name": "User Name"
}
```
- Success: 201

2. POST /api/auth/login
- Purpose: demo login endpoint
- Auth: No
- Note: disabled in production unless ALLOW_DEMO_LOGIN=true
- Success: 200

3. POST /api/auth/logout
- Purpose: consistency endpoint, real logout is client-side token/session clear
- Auth: No

4. POST /api/auth/verify-token
- Purpose: verify a Firebase ID token sent in request body
- Auth: No
- Body:
```json
{
  "id_token": "..."
}
```

### 4.2 Users

All endpoints below require Authorization header and UID ownership.

1. GET /api/users/<uid>
- Purpose: get user profile
- Auth: Yes

2. PUT /api/users/<uid>
- Purpose: update user profile
- Auth: Yes
- Body fields supported:
  - display_name

3. GET /api/users/<uid>/stats
- Purpose: dashboard stats
- Auth: Yes
- Response fields:
  - total_points
  - plant_health
  - plant_growth_stage

4. DELETE /api/users/<uid>/delete
- Purpose: delete user account and related data
- Auth: Yes

### 4.3 Habits

1. POST /api/habits
- Purpose: create habit
- Auth: Yes
- Body:
```json
{
  "name": "Drink water",
  "frequency": "daily",
  "description": "2L target",
  "icon": "💧"
}
```
- Note: user_id is taken from token UID.

2. GET /api/habits/<habit_id>
- Purpose: get habit detail
- Auth: No (current behavior)

3. PUT /api/habits/<habit_id>
- Purpose: update habit
- Auth: Yes

4. DELETE /api/habits/<habit_id>
- Purpose: delete habit
- Auth: Yes

5. GET /api/habits/user/<uid>
- Purpose: list user habits
- Auth: Yes + UID ownership

6. GET /api/habits/user/<uid>/recommendations?limit=6
- Purpose: habit suggestions based on existing habits
- Auth: Yes + UID ownership
- Note:
  - Uses Gemini when available
  - Falls back to rule-based recommendations on API/quota issues

7. POST /api/habits/<habit_id>/complete
- Purpose: mark habit complete and apply points/streak updates
- Auth: Yes
- Optional body:
```json
{
  "image_url": "https://...",
  "notes": "done in morning"
}
```

8. GET /api/habits/<habit_id>/streak?uid=<uid>
- Purpose: get streak info
- Auth: Yes + UID ownership

9. POST /api/habits/<habit_id>/reset-streak
- Purpose: reset streak (debug/admin style endpoint)
- Auth: Yes

### 4.4 Plants

All user-specific plant endpoints require Authorization and UID ownership.

1. GET /api/plants/<uid>
- Purpose: full plant status
- Auth: Yes

2. GET /api/plants/<uid>/health
- Purpose: plant health summary
- Auth: Yes

3. PUT /api/plants/<uid>/health
- Purpose: update plant health manually
- Auth: Yes
- Body:
```json
{
  "health_change": 5
}
```

4. POST /api/plants/<uid>/decay-check
- Purpose: trigger decay check
- Auth: Yes

5. POST /api/plants/batch-decay
- Purpose: batch decay job endpoint
- Auth: Optional CRON_SECRET guard
- If CRON_SECRET is set, send header:
  - X-Cron-Secret: <secret>

## 5. Frontend Integration Flow

Recommended flow:

1. User signs in with Firebase client SDK.
2. Frontend gets fresh ID token.
3. Frontend stores token and sends Authorization header on protected requests.
4. Frontend calls user-scoped endpoints with same UID as token UID.

Example header:

```http
Authorization: Bearer eyJhbGciOi...
```

## 6. Error Behavior

Common statuses:

- 400: missing or invalid request data
- 401: missing/invalid token
- 403: token UID and requested UID mismatch
- 404: entity or endpoint not found
- 500: unexpected server error

AI recommendation behavior:
- If Gemini returns quota/model/API issues, endpoint still returns 200 with fallback recommendations.

## 7. Frontend Checklist

1. Always send Authorization on protected routes.
2. Do not send arbitrary UID in create habit; backend uses token UID.
3. Ensure token refresh strategy in frontend for expired tokens.
4. Handle 401 by forcing re-auth.
5. Handle 403 as ownership/security mismatch.
6. Keep API base URL configurable by environment.

## 8. Quick Test URLs

- GET http://localhost:5000/api/health
- GET http://localhost:5000/api/docs

## 9. Notes

- This README is backend contract focused.
- If route behavior changes in code, update this file accordingly.
