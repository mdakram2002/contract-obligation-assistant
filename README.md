# Contract Obligation Assistant

An AI-powered application for extracting, tracking, and managing contract obligations, renewal deadlines, and key terms with human review workflows.

## Overview

The Contract Obligation Assistant helps organizations:
- Extract key contract terms (parties, dates, obligations, clauses)
- Track renewal and notice deadlines
- Identify ambiguous or conflicting terms
- Maintain version history of contract changes
- Require human approval before AI-generated information becomes trusted

This is an information-management tool, NOT legal advice. All extracted information should be reviewed by qualified legal professionals.

## Features

- **Document Upload**: Support for PDF, DOCX, and pasted text
- **AI-Powered Analysis**: Automatic extraction of contract terms using LLM
- **Idempotent Analysis**: Extracted records are stored once per contract version; loading an existing version reuses saved results
- **Source Evidence**: Every extracted item cites its exact source section, page, and quote
- **Human Review Workflow**: Approve, edit, or reject extracted items
- **Deterministic Deadline Calculation**: Application code calculates reminder dates (not AI)
- **Version Management**: Track contract versions and detect stale information
- **Dashboard**: View all contracts and their status
- **Review Workspace**: Comprehensive interface for reviewing extracted data
- **Deadline Tracking**: View upcoming obligations and renewal deadlines with certainty and review status

## Architecture

```
Frontend (React + TypeScript + Vite)
    |
    | REST API
    v
FastAPI Backend
    |
    +---- Document Extraction (PDF/DOCX/text)
    |
    +---- Contract Analysis (AI/LLM)
    |
    +---- AI Validation (Pydantic schemas)
    |
    +---- Review Workflow (approve/edit/reject)
    |
    +---- Deterministic Date Calculator
    |
    +---- Summary Generator
    |
    +---- Version Management
    |
    +---- Stale Detection
    |
    v
PostgreSQL Database
```

## Tech Stack

### Frontend
- React 18.3.1
- TypeScript 5.6.2
- Vite 5.4.8
- Tailwind CSS 3.4.14
- React Router 6.26.2

### Backend
- Python 3.14.5
- FastAPI 0.115.0
- Pydantic 2.9.2 on Python below 3.14; 2.13.5 on Python 3.14+
- SQLAlchemy 2.0.35 with its asyncio extra (including greenlet)
- AsyncPG 0.29.0 on Python below 3.14; 0.31.0 on Python 3.14+
- Alembic 1.13.3 (migrations)

### Document Processing
- PyMuPDF 1.24.12 (PDF)
- python-docx 1.1.2 (DOCX)

### AI/LLM
- OpenAI 1.51.2 (compatible with OpenAI-style APIs)

### Testing
- pytest 8.3.3
- pytest-asyncio 0.24.0
- httpx 0.27.2

## Project Structure

```
contract-obligation-assistant/
├── backend/
│   ├── app/
│   │   ├── api/              # API endpoints
│   │   │   ├── analysis.py
│   │   │   ├── contracts.py
│   │   │   ├── deadlines.py
│   │   │   ├── review.py
│   │   │   ├── upload.py
│   │   │   └── versions.py
│   │   ├── ai/               # AI integration
│   │   │   ├── client.py
│   │   │   ├── prompts.py
│   │   │   └── schemas.py
│   │   ├── logging/          # Structured logging
│   │   │   ├── config.py
│   │   │   └── service.py
│   │   ├── models/           # SQLAlchemy models
│   │   │   ├── contract.py
│   │   │   ├── contract_version.py
│   │   │   ├── party.py
│   │   │   ├── extracted_item.py
│   │   │   ├── obligation.py
│   │   │   ├── review_action.py
│   │   │   ├── ambiguity.py
│   │   │   ├── clarification_question.py
│   │   │   ├── ai_run.py
│   │   │   └── application_log.py
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   │   ├── document_parser.py
│   │   │   ├── contract_analyzer.py
│   │   │   ├── date_calculator.py
│   │   │   ├── analysis_service.py
│   │   ├── clarification_detection.py
│   │   ├── obligation_detection.py
│   │   │   ├── summary_service.py
│   │   │   ├── version_service.py
│   │   │   └── stale_detection.py
│   │   ├── config.py         # Configuration
│   │   ├── database.py       # Database connection
│   │   └── main.py           # FastAPI app
│   ├── alembic/              # Database migrations
│   ├── tests/                # Backend tests
│   ├── requirements.txt
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/            # Page components
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Upload.tsx
│   │   │   ├── Review.tsx
│   │   │   └── Deadlines.tsx
│   │   ├── services/        # API service
│   │   │   └── api.ts
│   │   ├── types/            # TypeScript types
│   │   │   └── index.ts
│   │   ├── utils/            # Utility functions
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
├── sample-data/              # Sample contract for testing
│   └── sample_contract.txt
├── .env.example              # Environment variables template
├── .gitignore
├── README.md
└── AGENT_USAGE.md
```

## AI Workflow

1. **Document Upload**: User uploads PDF, DOCX, or pastes text
2. **Text Extraction**: Document parser extracts raw text
3. **AI Analysis**: LLM analyzes contract and extracts structured data
4. **Validation**: Pydantic schemas validate AI output; an evidence-backed backend pass also detects extracted conflicts and explicit missing-information statements
5. **Storage**: Extracted data stored with review_status=PENDING
6. **Human Review**: User reviews and approves/edits/rejects items
7. **Date Calculation**: Deterministic code calculates deadlines from approved items
8. **Dashboard**: Users view approved obligations and upcoming deadlines

The AI never approves its own output. Human approval is required for important information. A backend evidence pass also persists clarification records for conflicting extracted terms and explicit missing-information statements, even when the model omits them.

## Document Processing

### Supported Formats
- **PDF**: Extracts text with page information (PyMuPDF)
- **DOCX**: Extracts paragraphs and headings (python-docx)
- **Text**: Accepts pasted text directly

### Validation
- File type validation (extension + signature check)
- File size limit (10MB)
- Empty document detection
- Unsupported format rejection

**Note**: OCR is not implemented. Documents must contain extractable text.

## Human Review Workflow

Each extracted item displays:
- Type (expiry, renewal, termination, notice, obligation)
- Value/description
- Responsible party (for obligations)
- Deadline (for obligations)
- Status (pending, approved, rejected)
- Confidence/certainty level
- Source section
- Source page
- Exact source quote

Actions:
- **Approve**: Mark item as approved for use in calculations
- **Reject**: Mark item as rejected
- **Edit**: Modify item values (stores previous values for audit trail)

## Versioning

When a new contract version is uploaded:
1. Previous version is preserved
2. New version is created
3. AI analyzes new version
4. Stale detection compares versions
5. Changed items from previous version are marked as stale
6. Historical record is maintained

Users can view version history and see what changed between versions.

## Deadline Calculation

**Important**: Deadline calculations use deterministic application code, not AI.

Formulas:
- Notice deadline = expiry_date - notice_period_days
- Renewal deadline = expiry_date - renewal_notice_period_days
- Obligation deadlines = stored directly from contract

The Deadlines page defaults to a 180-day window; users can choose between 1 and 365 days. Calculations include explicit expiry dates, renewal/renewal-notice dates derived from an expiry date and notice period, and obligations with a stored calendar deadline. Conflicting expiry dates produce clearly labeled low-certainty candidate renewal dates. Each dated and undated item also displays whether it is pending review or approved. Obligations without a known calendar date remain visible as trigger-dependent or recurring; no date is invented for unknown event dates. Rejected and stale records are excluded.

Business-day arithmetic is not currently implemented. Obligations that use business days remain undated; calculating them would also require a known reference event/date and the applicable client holiday calendar.

## Local Setup

### Prerequisites
- Node.js 18+
- Python 3.10+
- PostgreSQL 12+

### Backend Setup

1. **Create virtual environment**:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies** (from the `backend` directory):
```bash
pip install -r requirements.txt
```

The requirements select compatible Pydantic and AsyncPG versions for Python 3.14. SQLAlchemy's asyncio extra installs `greenlet`, which is required for async database operations. Use the same virtual environment to install dependencies and run the backend.

3. **Configure environment**:
```bash
cp ../.env.example .env
# Edit .env with your configuration
```

Set `DATABASE_URL` and `GROQ_API_KEY` in `backend/.env` before starting the backend.

4. **Set up database**:
```bash
# Create PostgreSQL database
createdb contract_assistant

# Run migrations
alembic upgrade head
```

5. **Run backend**:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

1. **Install dependencies**:
```bash
cd frontend
npm install
```

2. **Run development server**:
```bash
npm run dev
```

The frontend will be available at http://localhost:5173

## Environment Variables

Required environment variables (see `.env.example`):

```env
# Application Configuration
APP_NAME=Contract Obligation Assistant
APP_VERSION=1.0.0
DEBUG=true

# Database
DATABASE_URL=  # Set this to your PostgreSQL connection string

# AI/LLM
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
GROQ_BASE_URL=https://api.groq.com/openai/v1

# File Upload
MAX_UPLOAD_SIZE_MB=10

# CORS
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

## Running Backend

```bash
cd backend
uvicorn app.main:app --reload
```

API documentation available at: http://localhost:8000/docs

## Running Frontend

```bash
cd frontend
npm run dev
```

Frontend available at: http://localhost:5173

## Testing

### Backend Tests

```bash
cd backend
pytest tests/ -v
```

Test coverage includes:
- Document parsing validation
- Date calculation logic
- AI schema validation
- API endpoints (with test database)

### Frontend Tests

Frontend tests are not yet implemented. This is a known limitation.

## Deployment

This project can be deployed with **Render PostgreSQL + a Render FastAPI web service + a Vercel Vite frontend**. The frontend calls the backend directly; Render must allow the Vercel site origin through CORS.

Current public service URLs:

- Frontend: `https://contract-obligation-assistant.vercel.app`
- Backend: `https://contract-obligation-assistant.onrender.com`

### 1. Create the Render PostgreSQL database

1. In Render, create a PostgreSQL database. Choose a region and keep it available for the lifetime of the application; do not use an expiring trial database for persistent contract data.
2. Open the database's **Connect** details and copy its **Internal Database URL**. The Render web service and database must be in the same region to use the internal hostname.
3. Keep this URL private. Set it as the backend's `DATABASE_URL` environment variable; do not put it in frontend settings or commit it to the repository.

The application normalizes Render `postgres://` / `postgresql://` URLs to SQLAlchemy's async `asyncpg` driver. Use the internal URL exactly as provided by Render.

### 2. Deploy the FastAPI backend to Render

Create a Render **Web Service** connected to this Git repository and branch:

| Setting | Value |
|---|---|
| Root Directory | `backend` |
| Runtime | Python |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |
| Region | Same region as the Render PostgreSQL database |

Set these environment variables in the Render service settings:

| Variable | Value |
|---|---|
| `DATABASE_URL` | Render PostgreSQL **Internal Database URL** |
| `DEBUG` | `false` |
| `GROQ_API_KEY` | Your valid Groq API key (secret) |
| `GROQ_MODEL` | `openai/gpt-oss-120b` (or a model available to your Groq account) |
| `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` |
| `CORS_ORIGINS` | JSON array of exact frontend origins, e.g. `["https://your-app.vercel.app"]` |
| `MAX_UPLOAD_SIZE_MB` | `10` |

Add the Vercel custom domain to `CORS_ORIGINS` too if you use one. Use an exact origin (scheme and host, without a path or trailing slash); do not use `*`. If your Vercel preview deployments need API access, list each permitted preview origin explicitly.

For the current frontend, set `CORS_ORIGINS` to `["https://contract-obligation-assistant.vercel.app"]`.

**Database migrations must run before the API is used.** If the Render service provides a Pre-Deploy Command, set it to `alembic upgrade head`. Otherwise, run `alembic upgrade head` once from the service's Shell, with the service's `DATABASE_URL` configured. Run it again after deploying future commits that add migrations. Do not run schema creation manually.

After deployment, copy the service URL, such as `https://your-api.onrender.com`. Check `https://your-api.onrender.com/health` and confirm it returns JSON with `"status":"healthy"`. The `/health` endpoint only checks that the application started; verify the database separately with `/api/contracts`.

### 3. Deploy the React frontend to Vercel

1. Import the same Git repository into Vercel.
2. Set **Root Directory** to `frontend` and keep the framework preset as **Vite**.
3. Use `npm install` as the install command, `npm run build` as the build command, and `dist` as the output directory.
4. Add this Vercel environment variable for **Production** (and Preview too if previews should access the API):

   | Variable | Value |
   |---|---|
   | `VITE_API_BASE_URL` | `https://contract-obligation-assistant.onrender.com` |

   Do not append `/api`; the frontend adds that path itself. This value is compiled into the frontend at build time, so redeploy Vercel after changing it.

The checked-in `frontend/vercel.json` rewrites client-side routes to `index.html`, so refreshing `/review` or `/deadlines` works on Vercel.

### 4. Verify the complete deployment

After committing and deploying these settings to both services:

1. Visit `https://contract-obligation-assistant.onrender.com/health`; expect HTTP 200.
2. Visit `https://contract-obligation-assistant.onrender.com/api/contracts`; expect JSON (an empty contracts list is valid on a new database).
3. Open the Vercel URL and check the browser's Network panel. Requests for `/api/...` must go to the Render API origin and return successfully, not to Vercel.
4. Upload a small text-based PDF or DOCX, load its analysis, and verify the records persist after refreshing the page.
5. Try an AI analysis only after setting a valid server-side `GROQ_API_KEY`. Never set this secret as a `VITE_*` variable.

The Render free web-service plan may sleep when idle; its first request after sleeping can be slow. PostgreSQL plan retention and pricing vary, so check Render's current plan terms before choosing one for data you need to keep.

**Security note:** This application does not currently provide user authentication or authorization. Do not upload confidential contracts or expose the service for general use until access controls are added.

## Completed Scope

✅ Document upload (PDF, DOCX, text)
✅ AI-powered contract analysis
✅ Structured AI output validation
✅ Source evidence tracking (section, page, quote)
✅ Human review workflow (approve/edit/reject)
✅ Deterministic deadline calculation
✅ Contract versioning
✅ Stale item detection
✅ Dashboard with contract list
✅ Review workspace
✅ Deadline tracking
✅ Summary generation
✅ Backend tests (document parsing, date calc, AI schemas)
✅ Frontend production build
✅ Structured logging
✅ Sample contract data

## Excluded Scope

❌ OCR (documents must have extractable text)
❌ Electronic signatures
❌ External calendar integration
❌ Payment processing
❌ Legal recommendations
❌ Production database integrations (beyond PostgreSQL)
❌ Frontend unit tests
❌ Multi-user authentication
❌ Role-based access control
❌ Real-time collaboration

## Limitations

1. **AI Accuracy**: AI extraction may have errors. Human review is required.
2. **Document Format**: Only text-based PDF and DOCX files are supported. Scanned documents require OCR (not implemented).
3. **Date Parsing and Business Days**: Complex date expressions may not be parsed correctly. Business-day arithmetic is not implemented; those deadlines remain undated until the required event date and holiday calendar are available and supported.
4. **Legal Advice**: This tool provides information management, not legal advice.
5. **Single User**: No authentication or multi-user support.
6. **Performance**: Large documents may take longer to process.
7. **LLM Cost**: Each analysis consumes LLM API tokens (cost depends on provider).

## Reviewer Instructions

To evaluate this application:

1. **Set up local environment**:
   - Follow "Local Setup" instructions
   - Configure `backend/.env` with your Groq API key and database URL
   - Start PostgreSQL database
   - Run migrations

2. **Test document upload**:
   - Use the sample contract in `sample-data/sample_contract.txt`
   - Paste it via the Upload page
   - Verify it appears in Dashboard

3. **Test AI analysis**:
   - Go to Review page
   - Select the contract version
   - Click "Load Contract"
   - Verify extracted items appear with source evidence

4. **Test review workflow**:
   - Approve some items
   - Reject some items
   - Edit an item
   - Verify status changes

5. **Test deadline calculation**:
   - Go to Deadlines page
   - Select the contract version
   - Click "Calculate Deadlines"
   - Verify deadlines are calculated correctly

6. **Test versioning**:
   - Upload a modified version of the contract
   - Check Review page for both versions
   - Verify stale detection marks changed items

7. **Run tests**:
   ```bash
   cd backend
   pytest tests/ -v
   ```

8. **Check logs**:
   - Review application logs for structured events
   - Verify AI run metadata is logged

## Additional Information

- **AGENT_USAGE.md**: Documents AI-assisted development process
- **.env.example**: Template for environment configuration
- **sample-data/**: Sample contract for testing

## License

This project was created as a take-home assessment.
#   c o n t r a c t - o b l i g a t i o n - a s s i s t a n t  
 