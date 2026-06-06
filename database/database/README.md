# Urban Cab — Simplified Flask App

Maseru CBD ride-hailing system. Anonymous passenger model — no account needed to book.

## Quick Start (Windows)

```
py -m pip install flask werkzeug
py app.py
```

Then open: **http://localhost:5000**

## Demo Credentials

| Role | Username/Phone | Password |
|---|---|---|
| Driver | +26658200001 | Driver@1234 |
| Admin | admin | Admin@1234 |

## Schema (7 tables)

- **Locations** — 15 Maseru CBD stops
- **Payment_Methods** — Cash, Mobile Money, Card on Delivery
- **Drivers** — registered drivers with vehicles
- **Admin_Users** — platform administrators
- **Rides** — core table; passenger name+phone stored inline (no account needed)
- **Vehicle_Status** — driver location audit log
- **Ride_Reports** — generated management summaries

## MySQL Migration

1. `py -m pip install flask-mysqldb`
2. Replace `get_db()` / `q()` / `m()` helpers with `flask_mysqldb` cursor
3. Run `urban_cab_simplified.sql` against your MySQL server
4. Update connection config in `app.py`
