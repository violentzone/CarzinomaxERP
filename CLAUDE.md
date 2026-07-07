# Carzinomax ERP
This is a ERP build for free and easy deploy with AI integrated

## Structure
### Directory Tree
```text
D:\python\server1\carzinomaxERP
├── AGENTS.md
└── backend
    ├── .env
    ├── .python-version
    ├── .venv/
    ├── README.md
    ├── pyproject.toml
    ├── requirements.txt
    ├── uv.lock
    └── app
        ├── main.py
        ├── api
        │   ├── deps.py
        │   └── v1
        │       ├── __init__.py
        │       ├── auth.py
        │       ├── dev_tracking.py
        │       ├── finance.py
        │       ├── hr.py
        │       └── scm.py
        ├── core
        │   ├── config.py
        │   ├── database.py
        │   └── security.py
        ├── models
        │   ├── __init__.py
        │   ├── auth.py
        │   ├── base.py
        │   ├── dev_tracking.py
        │   ├── finance.py
        │   ├── hr.py
        │   └── scm.py
        └── schemas
            ├── __init__.py
            ├── auth.py
            ├── dev_tracking.py
            ├── finance.py
            ├── hr.py
            └── scm.py
```

### Technology Stack
#### Backend
- Framework: FastAPI
- Database: PostgreSQL + sqlalchemy

#### Frontend
- Framework: ReactJS (Yet to be created)

### ERP modules
1. Finance and Accounting
This is the heart of any ERP system. It automates financial operations, ensures regulatory compliance, and provides real-time visibility into the company's financial health.
   - General Ledger: The central repository for financial data.
   - Accounts Payable/Receivable: Manages incoming bills and outgoing invoices.
   - Fixed Assets: Tracks depreciation and lifecycle of company equipment.
   - Financial Reporting: Generates balance sheets, cash flow statements, and P&L reports.

2. Supply Chain Management (SCM)
SCM modules track the flow of goods and services from raw materials to final delivery.
   - Inventory Management: Monitors stock levels and stock movements. 
   - Procurement: Manages purchasing requests, vendor selection, and purchase orders. 
   - Logistics & Distribution: Coordinates shipping, warehousing, and tracking.

3. Human Resources (HRM/HCM)
HR modules streamline employee-related processes and data management.
   - Payroll: Automates salary payments, tax deductions, and benefits. 
   - Time & Attendance: Tracks hours worked, overtime, and leave management. 
   - Recruitment & Onboarding: Manages the hiring pipeline and new employee integration.

4. Development tracking
    - Development investments: Payments spent on cloud services
    - Development worker paychecks: Worker cost of project
    - Project Download counts: Counts of download on github

### LLM
- Framework: vLLM
- Model:

## Coding Conventions
### Docstrings
**Always use Google-style docstrings** for every module, class, and function — including FastAPI path operation functions. This is the project standard; keep it consistent so that both developers and LLM agents can read and extend the code reliably.

Structure: a one-line summary, followed by `Args:`, `Returns:`, and `Raises:` sections as applicable.

```python
def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token.

    Args:
        subject: The token subject, typically the user ID.
        expires_delta: Optional lifetime override. Defaults to the configured expiry.

    Returns:
        str: The encoded JWT access token.

    Raises:
        ValueError: If the subject is empty.
    """
```

