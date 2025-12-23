# Recommended Improvements for Link de Pago

This document outlines areas for improvement identified in the codebase, organized by priority and category.

---

## 1. Testing (Critical)

**Current State:** The `tests/` directory is empty (only `__init__.py`).

### Recommendations

**Unit Tests:**
- Test payment link creation, validation, and status transitions
- Test transaction state machine (PENDING → AUTHORIZED/FAILED)
- Test Webpay service response parsing
- Test email service (mock SMTP)

**Integration Tests:**
- Test OAuth flow with mocked Google responses
- Test full payment flow with mocked Webpay responses
- Test database transactions and rollbacks

**Example test structure:**
```
tests/
├── conftest.py           # Fixtures (test DB, mock services)
├── test_api/
│   ├── test_auth.py
│   ├── test_payment_links.py
│   └── test_payments.py
├── test_services/
│   ├── test_webpay.py
│   └── test_email.py
└── test_models/
    ├── test_payment_link.py
    └── test_transaction.py
```

**Tools to add:**
- `pytest` and `pytest-asyncio` for async test support
- `pytest-cov` for coverage reporting
- `httpx` for testing FastAPI (already in deps)
- `factory-boy` for test data generation

---

## 2. Security

### 2.1 XSS Prevention in Templates
**File:** `app/templates/dashboard.html:120-121`

User-provided data (`link.description`) is interpolated directly into HTML via JavaScript template literals without escaping.

```javascript
// Current (vulnerable)
<span class="font-medium">${link.description}</span>

// Recommended: escape HTML entities
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
```

### 2.2 Rate Limiting
Add rate limiting to prevent abuse:
- `/auth/google/login` - Prevent OAuth flood
- `/pay/{slug}/init` - Prevent transaction spam
- `/api/v1/links/` POST - Prevent link creation abuse

**Recommendation:** Use `slowapi` or `fastapi-limiter`:
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@router.post("/{slug}/init")
@limiter.limit("10/minute")
async def init_payment(...):
```

### 2.3 CSRF Protection
While session cookies use `same_site="lax"`, explicit CSRF tokens would provide defense in depth for state-changing operations.

### 2.4 Input Validation
**File:** `app/schemas/payment_link.py`

Consider adding:
- Regex validation for description (prevent special characters that could cause issues)
- Stricter currency validation (currently allows any 3-char string)

### 2.5 Audit Logging
Add audit trail for sensitive operations:
- Payment link creation/modification/deletion
- Successful/failed payment attempts
- Authentication events

---

## 3. Error Handling & Resilience

### 3.1 Retry Logic for External Services
**Files:** `app/services/webpay.py`, `app/services/email.py`

Add retry logic with exponential backoff for transient failures:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
async def send_payment_notification(...):
```

### 3.2 Timeout Configuration
**File:** `app/services/webpay.py`

The Transbank SDK calls don't have explicit timeout configuration. Consider wrapping with timeouts:

```python
import asyncio

async def create_transaction_with_timeout(...):
    return await asyncio.wait_for(
        asyncio.to_thread(self.tx.create, ...),
        timeout=30.0
    )
```

### 3.3 Circuit Breaker
For production resilience, consider circuit breaker pattern for Webpay integration to fail fast when the service is down.

### 3.4 Graceful Error Messages
**File:** `app/api/payments.py:93-94`

Some error messages expose implementation details. Ensure user-facing errors are generic while logging detailed errors internally.

---

## 4. Code Organization

### 4.1 Repository Pattern
Extract database queries into a repository layer:

```python
# app/repositories/payment_link.py
class PaymentLinkRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_slug(self, slug: str) -> PaymentLink | None:
        return self.db.query(PaymentLink).filter(PaymentLink.slug == slug).first()

    def get_user_links(self, user_id: UUID, skip: int, limit: int) -> list[PaymentLink]:
        ...
```

### 4.2 Service Layer for Business Logic
**File:** `app/api/payments.py`

The `payment_return` function (lines 48-166) mixes HTTP handling with business logic. Extract payment processing logic:

```python
# app/services/payment_processor.py
class PaymentProcessor:
    def process_webpay_return(self, token: str) -> PaymentResult:
        # Business logic here
```

### 4.3 Constants and Enums
Extract magic strings/numbers to constants:

```python
# app/constants.py
SESSION_MAX_AGE_DAYS = 7
MIN_PAYMENT_AMOUNT_CLP = 50
MAX_PAYMENT_AMOUNT_CLP = 999_999_999
BUY_ORDER_MAX_LENGTH = 26
```

---

## 5. Logging & Observability

### 5.1 Structured Logging
**Current:** Basic Python logging with string formatting.

**Recommendation:** Use structured logging for better observability:

```python
import structlog

logger = structlog.get_logger()

logger.info(
    "payment_initiated",
    buy_order=buy_order,
    amount=link.amount,
    link_id=str(link.id),
)
```

### 5.2 Request ID Tracing
Add request ID middleware for tracing requests across logs:

```python
from starlette.middleware.base import BaseHTTPMiddleware
import uuid

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

### 5.3 Metrics
Add application metrics for monitoring:
- Payment success/failure rates
- API response times
- Active payment links count
- Transaction volume

**Recommendation:** Use `prometheus-fastapi-instrumentator`

### 5.4 Enhanced Health Check
**File:** `app/main.py:44-46`

Current health check is minimal. Add dependency checks:

```python
@app.get("/health")
async def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "database": db_status,
        "version": "1.0.0",
    }
```

---

## 6. Database

### 6.1 Async SQLAlchemy
**Current:** Synchronous SQLAlchemy with `psycopg2`.

For better performance with FastAPI's async nature, consider migrating to async SQLAlchemy:

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

engine = create_async_engine("postgresql+asyncpg://...")
```

### 6.2 Connection Pooling Configuration
**File:** `app/database.py`

Add explicit pool configuration:

```python
engine = create_engine(
    settings.database_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections after 1 hour
)
```

### 6.3 Missing Indexes
Consider adding composite indexes for common query patterns:

```python
# For filtering by user_id + status (common in list queries)
__table_args__ = (
    Index('ix_payment_links_user_status', 'user_id', 'status'),
)
```

### 6.4 Soft Deletes
Consider soft deletes instead of status changes for audit trail:

```python
deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

---

## 7. API Design

### 7.1 Pagination Response
**File:** `app/api/payment_links.py:49-64`

Return pagination metadata with list responses:

```python
@router.get("/", response_model=PaginatedResponse[PaymentLinkRead])
async def list_links(...):
    total = db.query(PaymentLink).filter(...).count()
    return {
        "items": links,
        "total": total,
        "skip": skip,
        "limit": limit,
    }
```

### 7.2 Transaction History Endpoint
Add endpoint for users to view transaction history for their links:

```
GET /api/v1/links/{link_id}/transactions
```

### 7.3 API Versioning Strategy
Document the versioning strategy. Consider using header-based versioning for future flexibility:

```python
@router.get("/", headers={"X-API-Version": "1"})
```

### 7.4 OpenAPI Documentation
Enhance OpenAPI schema with:
- Detailed descriptions for endpoints
- Example request/response bodies
- Error response schemas

---

## 8. Frontend

### 8.1 Error Handling
**File:** `app/templates/dashboard.html:96-98`

API calls lack proper error handling:

```javascript
// Current
const res = await fetch(API_URL);
const links = await res.json();

// Recommended
try {
    const res = await fetch(API_URL);
    if (!res.ok) throw new Error('Failed to load links');
    const links = await res.json();
} catch (error) {
    container.innerHTML = '<p class="text-red-500">Error loading links</p>';
}
```

### 8.2 Loading States
Add proper loading indicators and disable buttons during operations to prevent double-submissions.

### 8.3 Accessibility
- Add `aria-label` attributes to icon buttons
- Ensure proper focus management in modal
- Add keyboard navigation support (Escape to close modal)

### 8.4 Progressive Enhancement
Consider server-side rendering for initial page load with JavaScript enhancement, improving SEO and initial load performance.

---

## 9. Configuration & DevOps

### 9.1 Environment-Specific Configuration
Add support for multiple environments:

```
.env.development
.env.staging
.env.production
```

### 9.2 Docker Improvements
Add application Dockerfile:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 9.3 CI/CD Pipeline
Add GitHub Actions workflow:
- Run tests on PR
- Lint with `ruff` or `flake8`
- Type check with `mypy`
- Security scan with `bandit`

### 9.4 Database Migrations in Production
Add migration command to deployment process:

```bash
alembic upgrade head
```

---

## 10. Documentation

### 10.1 API Documentation
- Add docstrings to all public functions
- Document expected request/response formats
- Add examples in OpenAPI schema

### 10.2 Developer Documentation
- Setup instructions for local development
- Architecture decision records (ADRs)
- Deployment runbook

### 10.3 Code Comments
Add comments explaining non-obvious business logic, especially in:
- `app/api/payments.py` - Webpay callback handling
- `app/services/webpay.py` - SDK response parsing

---

## Priority Matrix

| Priority | Category | Effort | Impact |
|----------|----------|--------|--------|
| Critical | Testing | High | High |
| Critical | XSS Prevention | Low | High |
| High | Rate Limiting | Medium | High |
| High | Structured Logging | Medium | Medium |
| High | Error Handling | Medium | Medium |
| Medium | Repository Pattern | High | Medium |
| Medium | Async SQLAlchemy | High | Medium |
| Medium | API Pagination | Low | Medium |
| Low | Soft Deletes | Medium | Low |
| Low | Progressive Enhancement | High | Low |

---

## Quick Wins (Can be done immediately)

1. Add XSS escaping in dashboard template
2. Add basic pytest configuration and first test
3. Enhance health check with database ping
4. Add connection pool configuration
5. Fix error handling in frontend JavaScript
6. Add request ID middleware for tracing

---

## Next Steps

1. Start with critical security fixes (XSS prevention)
2. Set up testing infrastructure and write first integration test
3. Add rate limiting to public endpoints
4. Implement structured logging
5. Create CI/CD pipeline with automated tests
