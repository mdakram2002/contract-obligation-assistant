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
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
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

### Production Build

**Frontend**:
```bash
cd frontend
npm run build
```
Output in `frontend/dist/`

**Backend**:
No special build step required. Ensure:
- `DEBUG=false` in production
- Use production PostgreSQL database
- Set secure CORS origins
- Use environment variables for secrets

### Deployment Options

The application can be deployed using:

**Frontend**: Vercel, Netlify, or any static hosting

**Backend**: Render, Railway, Azure App Service, or any Python hosting

**Database**: Managed PostgreSQL (Render, Neon, AWS RDS, etc.)

### Deployment Steps

1. Deploy PostgreSQL database
2. Set environment variables in hosting platform
3. Run database migrations: `alembic upgrade head`
4. Deploy backend (Python + FastAPI)
5. Build and deploy frontend (React + Vite)
6. Configure CORS to allow frontend domain
7. Test end-to-end functionality

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