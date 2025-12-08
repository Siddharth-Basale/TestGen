# Test Case Generation System

A full-stack application for generating hierarchical test cases (L1, L2, L3) based on business requirements using LangGraph and AI.

## Features

- 🔐 User authentication (Signup/Login)
- 📝 Create multiple test case generation sessions
- 🤖 AI-powered test case generation
- 🌳 Interactive tree visualization of test cases
- 📊 Session history and management
- 💾 Persistent storage of all sessions

## Tech Stack

### Backend
- FastAPI
- SQLAlchemy (SQLite/PostgreSQL)
- JWT Authentication
- LangGraph for workflow management
- OpenAI API

### Frontend
- React 18
- Vite
- Tailwind CSS
- React Router
- Axios

## Setup Instructions

### Prerequisites
- Python 3.8+
- Node.js 18+
- OpenAI API Key

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file in the root directory:
```
OPENAI_API_KEY=your-openai-api-key-here
DATABASE_URL=sqlite:///./testcasegen.db
SECRET_KEY=your-secret-key-change-this-in-production
```

5. Run the backend server:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Usage

1. **Sign Up**: Create a new account
2. **Login**: Sign in with your credentials
3. **Create Session**: Click "New Session" and enter your business description
4. **Answer Questions**: Answer optional clarification questions
5. **Select Test Cases**: Click on L1/L2 test cases to explore further
6. **View Tree**: See the complete hierarchical tree of test cases

## Project Structure

```
.
├── backend/
│   ├── main.py              # FastAPI application
│   ├── database.py          # Database configuration
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── auth.py              # Authentication utilities
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── pages/           # Page components
│   │   ├── components/      # Reusable components
│   │   ├── contexts/        # React contexts
│   │   └── services/        # API services
│   └── package.json         # Node dependencies
├── testcasegen.py           # Core test case generation logic
└── README.md
```

## API Endpoints

### Authentication
- `POST /api/auth/signup` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Get current user

### Sessions
- `GET /api/sessions` - Get all user sessions
- `POST /api/sessions` - Create new session
- `GET /api/sessions/{id}` - Get session details
- `DELETE /api/sessions/{id}` - Delete session

### Test Case Generation
- `POST /api/sessions/{id}/start` - Start test case generation
- `POST /api/sessions/{id}/l1/answers` - Submit L1 answers
- `POST /api/sessions/{id}/l1/select` - Select L1 case
- `POST /api/sessions/{id}/l2/answers` - Submit L2 answers
- `POST /api/sessions/{id}/l2/select` - Select L2 case
- `POST /api/sessions/{id}/l3/answers` - Submit L3 answers
- `GET /api/sessions/{id}/state` - Get session state

## Development

### Backend Development
```bash
cd backend
uvicorn main:app --reload
```

### Frontend Development
```bash
cd frontend
npm run dev
```

## Notes

- Make sure to set your OpenAI API key in the `.env` file
- The backend uses SQLite by default. For production, consider PostgreSQL
- Change the SECRET_KEY in `backend/auth.py` for production use
- CORS is configured for localhost:3000 and localhost:5173
