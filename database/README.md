# Urban Cab - Flask + MySQL App

Maseru CBD ride-hailing system. Anonymous passenger model - no account needed to book.

## Quick Start (Windows)

1. Install dependencies:

```bash
python -m pip install -r database\requirements.txt
```

2. Create the MySQL database:

```bash
mysql -u root -p < "database\lipalangoang mysql.sql"
```

3. Set `DB_HOST`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME` if you do not want the defaults in [`database/app.py`](C:\Users\windows 10\Desktop\Workshop\urban-cab\database\app.py).

4. Start the Flask app:

```bash
python database\app.py
```

Then open: `http://localhost:5000`

## Demo Credentials

| Role | Username/Phone | Password |
|---|---|---|
| Driver | +26658200001 | Driver@1234 |
| Admin | admin | Admin@1234 |

## Project Notes

- The live Flask app is `database/app.py`.
- The MySQL schema and seed data are in `database/lipalangoang mysql.sql`.
- Fare lookup bills by normalized fare zones: every `CBD*` location counts as `CBD`, and every `MSU*` location counts as `MSU Local`.
- The final coursework schema uses 9 tables, including `Payments` and `Ride_Ratings` for transaction completion and feedback.
- There is also a duplicate legacy copy under `database/database/`; keep the primary working copy under `database/`.

## Canonical Status Lifecycles

- Ride status: `REQUESTED` -> `ACCEPTED` -> `IN_PROGRESS` -> `COMPLETED` or `CANCELLED`
- Payment status: `PENDING` -> `COMPLETED` or `CANCELLED`

The app does not use a `PAID` payment status. Revenue and payment summaries are based on `payment_status='COMPLETED'`.
