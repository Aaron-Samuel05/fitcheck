# FitCheck Auth Testing Playbook

## Setup

- Backend: FastAPI at `$REACT_APP_BACKEND_URL/api`
- DB: MongoDB via `MONGO_URL`, DB `DB_NAME`
- Auth: bcrypt password hash + JWT (HS256) in httpOnly cookies (`access_token` 15m, `refresh_token` 7d)

## API test sequence (use external URL)

```
API_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2)

# 1. Register
curl -c /tmp/cookies.txt -s -X POST "$API_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"qa.user+1@fitcheck.app","password":"Passw0rd!"}'

# 2. /me with cookies
curl -b /tmp/cookies.txt -s "$API_URL/api/auth/me"

# 3. Logout
curl -b /tmp/cookies.txt -c /tmp/cookies.txt -s -X POST "$API_URL/api/auth/logout"

# 4. /me should now be 401
curl -b /tmp/cookies.txt -s -o /dev/null -w "%{http_code}\n" "$API_URL/api/auth/me"

# 5. Login
curl -c /tmp/cookies.txt -s -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"qa.user+1@fitcheck.app","password":"Passw0rd!"}'

# 6. Login with wrong password -> 401
curl -s -o /dev/null -w "%{http_code}\n" -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"qa.user+1@fitcheck.app","password":"wrong"}'
```

## Frontend test flow

1. Landing page should render at `/` on black background with neon green accents.
2. Hero shows headline, subheadline, and "Get Started Free" CTA.
3. Features section shows 3 cards: Log Workouts, Track Progress, Custom Plans.
4. Footer shows brand + links.
5. Clicking **Get Started Free** or **Sign up** opens the signup modal.
6. Submitting the signup form with valid credentials logs the user in — navbar shows email + Log out.
7. Logout returns the UI to the signed-out state.
8. Clicking **Log in** opens login modal — credentials from previous signup work.
9. Modal closes on Escape and on outside click.

## Expected behaviors / edge cases

- Registering a duplicate email returns `400 Email already registered`.
- Invalid login returns `401 Invalid email or password`.
- Weak passwords (<6 chars) rejected by both frontend and backend validation.
- `/api/auth/me` without cookies returns 401.
