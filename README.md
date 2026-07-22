# LegacyGuard

LegacyGuard is a secure personal asset continuity and legacy planning system. It helps a person document assets, beneficiaries, important documents, and instructions so trusted people can locate and manage them if the user becomes incapacitated or dies.

## Project purpose
- Centralize continuity planning information
- Protect sensitive personal and financial data
- Support future trusted-contact and emergency workflows

## Security model overview
The initial security foundation includes:
- password hashing with bcrypt
- JWT-based authentication for protected routes
- user ownership validation for future account-scoped data
- audit logging for auth events such as login success, login failure, and account creation

## Environment setup
Create a backend environment file from the template:

```bash
cd backend
copy .env.example .env
```

Fill in the required placeholders for:
- DATABASE_URL
- SECRET_KEY
- ENCRYPTION_KEY
- JWT_SECRET
- ENVIRONMENT

## Authentication workflow
1. Register a user through the /auth/register endpoint
2. Log in through the /auth/login endpoint
3. Use the returned access token in the Authorization header for protected routes
4. Access the current-user profile through /auth/me

## Installation

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend
```bash
cd frontend
npm install
```

## Development commands

### Backend
```bash
cd backend
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm run dev
```

### Tests
```bash
cd backend
pytest
```

## Security principles
- Use encrypted storage and secure transport
- Apply least-privilege access controls
- Keep audit trails for privileged changes
- Avoid storing secrets in source control
- Plan for future MFA and role-based access
