"""
Urban Cab — Flask Web Application (MySQL)
Maseru CBD + MSU Local Passenger Transportation System
Anonymous passenger model: name + phone captured on ride, no account required.
9 tables: Locations, Payment_Methods, Fares, Drivers, Admin_Users,
          Rides, Payments, Ride_Ratings, Ride_Reports

Requirements: pip install flask werkzeug flask-mysqldb
Database:     Run urban_cab_mysql.sql against your MySQL server first.
Config:       Set DB_HOST, DB_USER, DB_PASSWORD, DB_NAME env vars,
              or edit the app.config lines directly in this file.
"""
import os, hashlib, secrets, re, datetime, logging
from flask_mysqldb import MySQL
import MySQLdb.cursors
from functools import wraps
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, g, jsonify)

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.logger.setLevel(logging.INFO)

@app.template_filter('dtfmt')
def dtfmt(value, fmt='%Y-%m-%d %H:%M'):
    """Render either a datetime object or a datetime string safely in templates."""
    if not value:
        return ''
    if hasattr(value, 'strftime'):
        return value.strftime(fmt)
    text = str(value)
    for parser in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d'):
        try:
            return datetime.datetime.strptime(text, parser).strftime(fmt)
        except ValueError:
            continue
    return text

# ── MySQL config ─────────────────────────────────────────────
app.config['MYSQL_HOST']     = os.environ.get('DB_HOST',     'localhost')
app.config['MYSQL_USER']     = os.environ.get('DB_USER',     'root')
app.config['MYSQL_PASSWORD'] = os.environ.get('DB_PASSWORD', '@Master5725#')
app.config['MYSQL_DB']       = os.environ.get('DB_NAME',     'urban_cab_db')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)

# ── DB helpers ────────────────────────────────────────────────
def q(sql, args=(), one=False):
    """Execute a SELECT and return list of dicts (or one dict)."""
    cur = mysql.connection.cursor()
    cur.execute(sql, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def m(sql, args=()):
    """Execute INSERT / UPDATE / DELETE, commit, return lastrowid."""
    cur = mysql.connection.cursor()
    cur.execute(sql, args)
    mysql.connection.commit()
    lid = cur.lastrowid
    cur.close()
    return lid

def m_count(sql, args=()):
    """Execute INSERT / UPDATE / DELETE, commit, and return affected rows."""
    cur = mysql.connection.cursor()
    cur.execute(sql, args)
    mysql.connection.commit()
    rowcount = cur.rowcount
    cur.close()
    return rowcount

def hash_pw(pw):   return hashlib.sha256(pw.encode()).hexdigest()
def check_pw(p,h): return hash_pw(p) == h

# ── Validation ────────────────────────────────────────────────
def val_phone(p): return bool(re.match(r'^\+?[0-9]{8,15}$', p.replace(' ','')))
def val_email(e): return bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', e)) if e else True
def val_pw(p):    return len(p) >= 6
def val_plate(p): return bool(re.match(r'^[A-Z0-9 \-]{4,12}$', p.upper()))
def val_lic(l):   return len(l.strip()) >= 4
def val_name(n):  return len(n.strip()) >= 2

def normalize_zone(zone):
    """Collapse location zones into the fare table's two billing zones."""
    zone = (zone or '').strip()
    if zone.upper().startswith('MSU'):
        return 'MSU Local'
    return 'CBD'

def get_fare(pickup_id, dropoff_id):
    """Look up the fixed fare for two location IDs via normalized fare zones."""
    route = q("""SELECT
            pu.location_name AS pickup_name,
            pu.area_zone AS pickup_zone,
            dr.location_name AS dropoff_name,
            dr.area_zone AS dropoff_zone
        FROM Locations pu
        JOIN Locations dr
        WHERE pu.location_id=%s AND dr.location_id=%s""",
        (pickup_id, dropoff_id), one=True)
    if not route:
        app.logger.warning('Fare lookup failed: invalid location ids pickup=%s dropoff=%s',
                           pickup_id, dropoff_id)
        return None

    zone_from = normalize_zone(route['pickup_zone'])
    zone_to = normalize_zone(route['dropoff_zone'])
    row = q("""SELECT amount FROM Fares
        WHERE zone_from=%s AND zone_to=%s""",
        (zone_from, zone_to), one=True)
    if not row:
        app.logger.warning(
            'Fare missing for route pickup=%s (%s -> %s) dropoff=%s (%s -> %s)',
            pickup_id, route['pickup_name'], route['pickup_zone'],
            dropoff_id, route['dropoff_name'], route['dropoff_zone']
        )
        return None
    return float(row['amount']) if row else None

# ── Auth decorator ────────────────────────────────────────────
def auth(role=None):
    def dec(f):
        @wraps(f)
        def wrap(*a, **kw):
            if 'uid' not in session:
                flash('Please log in to continue.', 'warning')
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                flash('Access denied.', 'danger')
                return redirect(url_for('home'))
            return f(*a, **kw)
        return wrap
    return dec

# ── DB init ───────────────────────────────────────────────────

# ═══════════════════════════════════════════════════════════════
#  SHARED ROUTES
# ═══════════════════════════════════════════════════════════════
@app.route('/')
def index():
    if 'uid' in session:
        return redirect(url_for('home'))
    return render_template('landing.html')

@app.route('/home')
def home():
    role = session.get('role')
    if role == 'driver': return redirect(url_for('driver_home'))
    if role == 'admin':  return redirect(url_for('admin_home'))
    return redirect(url_for('index'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        role  = request.form.get('role','driver')
        ident = request.form.get('identifier','').strip()
        pw    = request.form.get('password','')
        if not ident or not pw:
            flash('Please enter your credentials.', 'danger')
            return render_template('login.html', role=role, ident=ident)
        if role == 'driver':
            u = q("SELECT * FROM Drivers WHERE phone_number=%s", (ident,), one=True)
            if u and check_pw(pw, u['password_hash']):
                session.update({'uid':u['driver_id'], 'role':'driver',
                                'name': f"{u['first_name']} {u['last_name']}"})
                flash(f"Welcome, {u['first_name']}!", 'success')
                return redirect(url_for('driver_home'))
        elif role == 'admin':
            u = q("SELECT * FROM Admin_Users WHERE username=%s OR email=%s", (ident,ident), one=True)
            if u and check_pw(pw, u['password_hash']):
                session.update({'uid':u['admin_id'], 'role':'admin', 'name':u['username']})
                flash('Admin login successful.', 'success')
                return redirect(url_for('admin_home'))
        flash('Incorrect credentials. Please try again.', 'danger')
        return render_template('login.html', role=role, ident=ident)
    return render_template('login.html', role='driver', ident='')

@app.route('/logout')
def logout():
    name = session.get('name','')
    session.clear()
    flash(f'Goodbye, {name}! You have been logged out.', 'info')
    return redirect(url_for('index'))

# ═══════════════════════════════════════════════════════════════
#  PUBLIC — BOOK A RIDE  (no login needed)
# ═══════════════════════════════════════════════════════════════
@app.route('/book', methods=['GET','POST'])
def book():
    locations = q("SELECT * FROM Locations WHERE is_active=1 ORDER BY area_zone,location_name")
    methods   = q("SELECT * FROM Payment_Methods WHERE is_active=1")
    location_ids = {str(loc['location_id']) for loc in locations}
    method_ids = {str(method['payment_method_id']) for method in methods}
    fares = q("SELECT * FROM Fares")
    if request.method == 'POST':
        name    = request.form.get('passenger_name','').strip()
        phone   = request.form.get('passenger_phone','').strip()
        pickup  = request.form.get('pickup','')
        dropoff = request.form.get('dropoff','')
        pay     = request.form.get('payment','')
        notes   = request.form.get('notes','').strip()
        errors  = []
        if not val_name(name):    errors.append('Please enter your full name (at least 2 characters).')
        if not phone:             errors.append('Phone number is required.')
        elif not val_phone(phone):errors.append('Enter a valid phone number (e.g. +26657123456).')
        if not pickup:            errors.append('Please select a pickup location.')
        if not dropoff:           errors.append('Please select a destination.')
        if pickup and pickup not in location_ids:
            errors.append('Selected pickup location is invalid.')
        if dropoff and dropoff not in location_ids:
            errors.append('Selected destination is invalid.')
        if pickup and dropoff and pickup == dropoff:
            errors.append('Pickup and destination cannot be the same location.')
        if not pay:               errors.append('Please select a payment method.')
        elif pay not in method_ids:
            errors.append('Selected payment method is invalid.')
        if errors:
            for e in errors: flash(e, 'danger')
            return render_template('book.html', locations=locations, methods=methods, form=request.form, fares=fares)
        # Look up fixed fare from rate table
        fare = get_fare(int(pickup), int(dropoff))
        if fare is None:
            flash('Could not calculate fare for this route. Please try again.', 'danger')
            return render_template('book.html', locations=locations, methods=methods, form=request.form, fares=fares)

        ride_id = m(
            "INSERT INTO Rides(passenger_name,passenger_phone,pickup_location_id,"
            "dropoff_location_id,payment_method_id,notes,ride_status,fare_amount) VALUES(%s,%s,%s,%s,%s,%s,'REQUESTED',%s)",
            (name, phone, int(pickup), int(dropoff), int(pay), notes, fare)
        )
        m("""INSERT INTO Payments(ride_id, payment_method_id, payment_status, amount_due)
             VALUES(%s, %s, 'PENDING', %s)""",
          (ride_id, int(pay), fare))
        flash(f'Ride #{ride_id} booked! Fare: M {fare:.2f}. Show your ride number to track it.', 'success')
        return redirect(url_for('track', ride_id=ride_id))
    return render_template('book.html', locations=locations, methods=methods, form={}, fares=fares)

@app.route('/track/<int:ride_id>')
def track(ride_id):
    ride = q("""SELECT r.*,
        pu.location_name AS pickup_name, dr.location_name AS dropoff_name,
        pm.method_name,
        CONCAT(d.first_name, ' ', d.last_name) AS driver_name,
        d.vehicle_plate, d.vehicle_model, d.phone_number AS driver_phone,
        p.payment_status, p.amount_due, p.amount_paid, p.paid_at,
        rr.rating_score, rr.rating_comment, rr.created_at AS rated_at
        FROM Rides r
        JOIN Locations pu ON r.pickup_location_id=pu.location_id
        JOIN Locations dr ON r.dropoff_location_id=dr.location_id
        JOIN Payment_Methods pm ON r.payment_method_id=pm.payment_method_id
        LEFT JOIN Drivers d ON r.driver_id=d.driver_id
        LEFT JOIN Payments p ON p.ride_id=r.ride_id
        LEFT JOIN Ride_Ratings rr ON rr.ride_id=r.ride_id
        WHERE r.ride_id=%s""", (ride_id,), one=True)
    if not ride:
        flash('Ride not found.', 'danger')
        return redirect(url_for('book'))
    return render_template('track.html', ride=ride)

@app.route('/api/ride/<int:ride_id>/status')
def api_status(ride_id):
    ride = q("SELECT ride_status, driver_id FROM Rides WHERE ride_id=%s", (ride_id,), one=True)
    if ride: return jsonify({'status': ride['ride_status'], 'driver_id': ride['driver_id']})
    return jsonify({'error': 'not found'}), 404

# ═══════════════════════════════════════════════════════════════
#  DRIVER ROUTES
# ═══════════════════════════════════════════════════════════════
@app.route('/driver')
@auth('driver')
def driver_home():
    driver   = q("SELECT * FROM Drivers WHERE driver_id=%s", (session['uid'],), one=True)
    pending  = q("""SELECT r.*,
        pu.location_name AS pickup_name, dr.location_name AS dropoff_name, pm.method_name
        FROM Rides r
        JOIN Locations pu ON r.pickup_location_id=pu.location_id
        JOIN Locations dr ON r.dropoff_location_id=dr.location_id
        JOIN Payment_Methods pm ON r.payment_method_id=pm.payment_method_id
        WHERE r.ride_status='REQUESTED' AND r.driver_id IS NULL
        ORDER BY r.requested_at ASC""")
    my_rides = q("""SELECT r.*,
        pu.location_name AS pickup_name, dr.location_name AS dropoff_name, pm.method_name
        FROM Rides r
        JOIN Locations pu ON r.pickup_location_id=pu.location_id
        JOIN Locations dr ON r.dropoff_location_id=dr.location_id
        JOIN Payment_Methods pm ON r.payment_method_id=pm.payment_method_id
        WHERE r.driver_id=%s AND r.ride_status IN ('ACCEPTED','IN_PROGRESS')
        ORDER BY r.accepted_at DESC""", (session['uid'],))
    stats    = q("""SELECT COUNT(*) as total,
        SUM(CASE WHEN ride_status='COMPLETED' THEN 1 ELSE 0 END) as completed,
        COALESCE(SUM(fare_amount),0) as earned
        FROM Rides WHERE driver_id=%s""", (session['uid'],), one=True)
    return render_template('driver/home.html', driver=driver, pending=pending,
                           my_rides=my_rides, stats=stats)

@app.route('/driver/accept/<int:ride_id>', methods=['POST'])
@auth('driver')
def driver_accept(ride_id):
    updated = m_count(
        "UPDATE Rides SET driver_id=%s,ride_status='ACCEPTED',accepted_at=NOW() "
        "WHERE ride_id=%s AND ride_status='REQUESTED' AND driver_id IS NULL",
        (session['uid'], ride_id)
    )
    if updated:
        m("UPDATE Drivers SET is_available=0 WHERE driver_id=%s", (session['uid'],))
        flash(f'Ride #{ride_id} accepted! Head to the pickup location.', 'success')
    else:
        flash('Ride no longer available.', 'warning')
    return redirect(url_for('driver_home'))

@app.route('/driver/start/<int:ride_id>', methods=['POST'])
@auth('driver')
def driver_start(ride_id):
    updated = m_count(
        "UPDATE Rides SET ride_status='IN_PROGRESS' "
        "WHERE ride_id=%s AND driver_id=%s AND ride_status='ACCEPTED'",
        (ride_id, session['uid'])
    )
    if updated:
        flash('Ride started!', 'success')
    else:
        flash('Unable to start that ride.', 'warning')
    return redirect(url_for('driver_home'))

@app.route('/driver/complete/<int:ride_id>', methods=['POST'])
@auth('driver')
def driver_complete(ride_id):
    # Fare is already set at booking time — driver just marks ride complete
    ride = q("SELECT fare_amount FROM Rides WHERE ride_id=%s AND driver_id=%s AND ride_status='IN_PROGRESS'",
             (ride_id, session['uid']), one=True)
    if not ride:
        flash('Ride not found or already completed.', 'danger')
        return redirect(url_for('driver_home'))
    m("UPDATE Rides SET ride_status='COMPLETED',completed_at=NOW() "
      "WHERE ride_id=%s AND driver_id=%s AND ride_status='IN_PROGRESS'",
      (ride_id, session['uid']))
    m("""INSERT INTO Payments
         (ride_id, payment_method_id, payment_status, amount_due, amount_paid, paid_at, received_by_driver_id)
         SELECT ride_id, payment_method_id, 'COMPLETED', fare_amount, fare_amount, NOW(), %s
         FROM Rides WHERE ride_id=%s
         ON DUPLICATE KEY UPDATE
           payment_status='COMPLETED',
           amount_due=VALUES(amount_due),
           amount_paid=VALUES(amount_paid),
           paid_at=VALUES(paid_at),
           received_by_driver_id=VALUES(received_by_driver_id)""",
      (session['uid'], ride_id))
    m("UPDATE Drivers SET is_available=1 WHERE driver_id=%s", (session['uid'],))
    fare = ride['fare_amount'] or 0
    flash(f'Ride completed! Collect M {fare:.2f} from the passenger.', 'success')
    return redirect(url_for('driver_home'))

@app.route('/driver/toggle', methods=['POST'])
@auth('driver')
def driver_toggle():
    d   = q("SELECT is_available FROM Drivers WHERE driver_id=%s", (session['uid'],), one=True)
    new = 0 if d['is_available'] else 1
    m("UPDATE Drivers SET is_available=%s WHERE driver_id=%s", (new, session['uid']))
    flash(f"Status: {'Online — you will receive ride requests.' if new else 'Offline.'}", 'info')
    return redirect(url_for('driver_home'))

@app.route('/driver/history')
@auth('driver')
def driver_history():
    search    = request.args.get('q','')
    date_from = request.args.get('date_from','')
    date_to   = request.args.get('date_to','')
    sql  = """SELECT r.*,
        pu.location_name AS pickup_name, dr.location_name AS dropoff_name, pm.method_name
        FROM Rides r
        JOIN Locations pu ON r.pickup_location_id=pu.location_id
        JOIN Locations dr ON r.dropoff_location_id=dr.location_id
        JOIN Payment_Methods pm ON r.payment_method_id=pm.payment_method_id
        WHERE r.driver_id=%s AND r.ride_status='COMPLETED'"""
    args = [session['uid']]
    if search:    sql += " AND (r.passenger_name LIKE %s OR r.passenger_phone LIKE %s)"; args += [f'%{search}%']*2
    if date_from: sql += " AND DATE(r.completed_at)>=%s"; args.append(date_from)
    if date_to:   sql += " AND DATE(r.completed_at)<=%s"; args.append(date_to)
    sql += " ORDER BY r.completed_at DESC"
    rides = q(sql, args)
    total = sum(r['fare_amount'] or 0 for r in rides)
    return render_template('driver/history.html', rides=rides, total=total,
                           search=search, date_from=date_from, date_to=date_to)

@app.route('/driver/profile', methods=['GET','POST'])
@auth('driver')
def driver_profile():
    d = q("SELECT * FROM Drivers WHERE driver_id=%s", (session['uid'],), one=True)
    if request.method == 'POST':
        fn  = request.form.get('first_name','').strip()
        ln  = request.form.get('last_name','').strip()
        vm  = request.form.get('vehicle_model','').strip()
        plt = request.form.get('vehicle_plate','').strip().upper()
        pw  = request.form.get('new_password','')
        pw2 = request.form.get('confirm_password','')
        errors = []
        if not val_name(fn): errors.append('First name must be at least 2 characters.')
        if not val_name(ln): errors.append('Last name must be at least 2 characters.')
        if plt and not val_plate(plt): errors.append('Vehicle plate format: 4–12 alphanumeric characters.')
        if pw and not val_pw(pw):      errors.append('Password must be at least 6 characters.')
        if pw and pw != pw2:           errors.append('Passwords do not match.')
        if errors:
            for e in errors: flash(e, 'danger')
            return render_template('driver/profile.html', d=d)
        if pw:
            m("UPDATE Drivers SET first_name=%s,last_name=%s,vehicle_model=%s,vehicle_plate=%s,password_hash=%s "
              "WHERE driver_id=%s", (fn, ln, vm, plt or d['vehicle_plate'], hash_pw(pw), session['uid']))
        else:
            m("UPDATE Drivers SET first_name=%s,last_name=%s,vehicle_model=%s,vehicle_plate=%s WHERE driver_id=%s",
              (fn, ln, vm, plt or d['vehicle_plate'], session['uid']))
        session['name'] = f"{fn} {ln}"
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('driver_profile'))
    return render_template('driver/profile.html', d=d)

# ═══════════════════════════════════════════════════════════════
#  ADMIN ROUTES
# ═══════════════════════════════════════════════════════════════
@app.route('/admin')
@auth('admin')
def admin_home():
    stats = q("""SELECT COUNT(*) as total,
        SUM(CASE WHEN ride_status='COMPLETED'   THEN 1 ELSE 0 END) as completed,
        SUM(CASE WHEN ride_status='CANCELLED'   THEN 1 ELSE 0 END) as cancelled,
        SUM(CASE WHEN ride_status='REQUESTED'   THEN 1 ELSE 0 END) as pending,
        SUM(CASE WHEN ride_status='IN_PROGRESS' THEN 1 ELSE 0 END) as in_progress
        FROM Rides""", one=True)
    drivers_total  = q("SELECT COUNT(*) as c FROM Drivers", one=True)
    drivers_online = q("SELECT COUNT(*) as c FROM Drivers WHERE is_available=1", one=True)
    payment_stats = q("""SELECT
        COUNT(*) as total,
        SUM(CASE WHEN payment_status='COMPLETED' THEN 1 ELSE 0 END) as completed,
        SUM(CASE WHEN payment_status='PENDING' THEN 1 ELSE 0 END) as pending,
        SUM(CASE WHEN payment_status='CANCELLED' THEN 1 ELSE 0 END) as cancelled,
        COALESCE(SUM(CASE WHEN payment_status='COMPLETED' THEN amount_paid ELSE 0 END),0) as revenue
        FROM Payments""", one=True)
    rating_stats = q("""SELECT
        COUNT(*) as total,
        COALESCE(AVG(rating_score), 0) as average_score
        FROM Ride_Ratings""", one=True)
    recent = q("""SELECT r.*,
        pu.location_name AS pickup_name, dr.location_name AS dropoff_name,
        CONCAT(d.first_name, ' ', d.last_name) AS driver_name, pm.method_name,
        p.payment_status
        FROM Rides r
        JOIN Locations pu ON r.pickup_location_id=pu.location_id
        JOIN Locations dr ON r.dropoff_location_id=dr.location_id
        JOIN Payment_Methods pm ON r.payment_method_id=pm.payment_method_id
        LEFT JOIN Drivers d ON r.driver_id=d.driver_id
        LEFT JOIN Payments p ON p.ride_id=r.ride_id
        ORDER BY r.requested_at DESC LIMIT 8""")
    top_locs = q("""SELECT l.location_name, COUNT(r.ride_id) as cnt
        FROM Locations l LEFT JOIN Rides r ON l.location_id=r.pickup_location_id
        GROUP BY l.location_id ORDER BY cnt DESC LIMIT 5""")
    pay_stats = q("""SELECT pm.method_name, COUNT(r.ride_id) as cnt,
        COALESCE(SUM(r.fare_amount),0) as total
        FROM Payment_Methods pm LEFT JOIN Rides r ON pm.payment_method_id=r.payment_method_id
        GROUP BY pm.payment_method_id""")
    return render_template('admin/home.html', stats=stats,
                           drivers_total=drivers_total, drivers_online=drivers_online,
                           recent=recent, top_locs=top_locs, pay_stats=pay_stats,
                           payment_stats=payment_stats, rating_stats=rating_stats)

# ── Admin: Rides ─────────────────────────────────────────────
@app.route('/admin/rides')
@auth('admin')
def admin_rides():
    search    = request.args.get('q','')
    status    = request.args.get('status','')
    loc_id    = request.args.get('loc_id','')
    date_from = request.args.get('date_from','')
    date_to   = request.args.get('date_to','')
    sql  = """SELECT r.*,
        pu.location_name AS pickup_name, dr.location_name AS dropoff_name,
        CONCAT(d.first_name, ' ', d.last_name) AS driver_name, pm.method_name,
        p.payment_status
        FROM Rides r
        JOIN Locations pu ON r.pickup_location_id=pu.location_id
        JOIN Locations dr ON r.dropoff_location_id=dr.location_id
        JOIN Payment_Methods pm ON r.payment_method_id=pm.payment_method_id
        LEFT JOIN Drivers d ON r.driver_id=d.driver_id
        LEFT JOIN Payments p ON p.ride_id=r.ride_id WHERE 1=1"""
    args = []
    if search:    sql += " AND (r.passenger_name LIKE %s OR r.passenger_phone LIKE %s OR COALESCE(CONCAT(d.first_name, ' ', d.last_name),'') LIKE %s OR pu.location_name LIKE %s OR dr.location_name LIKE %s)"; args += [f'%{search}%']*5
    if status:    sql += " AND r.ride_status=%s"; args.append(status)
    if loc_id:    sql += " AND (r.pickup_location_id=%s OR r.dropoff_location_id=%s)"; args += [loc_id]*2
    if date_from: sql += " AND DATE(r.requested_at)>=%s"; args.append(date_from)
    if date_to:   sql += " AND DATE(r.requested_at)<=%s"; args.append(date_to)
    sql += " ORDER BY r.requested_at DESC"
    rides     = q(sql, args)
    locations = q("SELECT * FROM Locations WHERE is_active=1 ORDER BY location_name")
    return render_template('admin/rides.html', rides=rides, locations=locations,
                           search=search, status=status, loc_id=loc_id,
                           date_from=date_from, date_to=date_to)

@app.route('/admin/rides/<int:ride_id>/cancel', methods=['POST'])
@auth('admin')
def admin_cancel_ride(ride_id):
    ride = q("SELECT * FROM Rides WHERE ride_id=%s", (ride_id,), one=True)
    if ride and ride['ride_status'] in ('REQUESTED','ACCEPTED','IN_PROGRESS'):
        m("UPDATE Rides SET ride_status='CANCELLED' WHERE ride_id=%s", (ride_id,))
        m("""UPDATE Payments
             SET payment_status='CANCELLED', amount_paid=NULL, paid_at=NULL, received_by_driver_id=NULL
             WHERE ride_id=%s""", (ride_id,))
        if ride['driver_id']:
            m("UPDATE Drivers SET is_available=1 WHERE driver_id=%s", (ride['driver_id'],))
        flash(f'Ride #{ride_id} cancelled.', 'info')
    else:
        flash('This ride cannot be cancelled.', 'danger')
    return redirect(url_for('admin_rides'))

# ── Admin: Drivers ────────────────────────────────────────────
@app.route('/admin/drivers')
@auth('admin')
def admin_drivers():
    search       = request.args.get('q','')
    avail_filter = request.args.get('avail','')
    sql  = """SELECT d.*, COUNT(r.ride_id) as total_rides,
        COALESCE(SUM(r.fare_amount),0) as earned
        FROM Drivers d LEFT JOIN Rides r ON d.driver_id=r.driver_id AND r.ride_status='COMPLETED'
        WHERE 1=1"""
    args = []
    if search: sql += " AND (CONCAT(d.first_name, ' ', d.last_name) LIKE %s OR d.vehicle_plate LIKE %s OR d.license_number LIKE %s)"; args += [f'%{search}%']*3
    if avail_filter == '1': sql += " AND d.is_available=1"
    elif avail_filter == '0': sql += " AND d.is_available=0"
    sql += " GROUP BY d.driver_id ORDER BY d.joined_at DESC"
    drivers = q(sql, args)
    return render_template('admin/drivers.html', drivers=drivers,
                           search=search, avail_filter=avail_filter)

@app.route('/admin/drivers/new', methods=['GET','POST'])
@auth('admin')
def admin_new_driver():
    if request.method == 'POST':
        fn  = request.form.get('first_name','').strip()
        ln  = request.form.get('last_name','').strip()
        ph  = request.form.get('phone','').strip()
        lic = request.form.get('license','').strip().upper()
        plt = request.form.get('plate','').strip().upper()
        vm  = request.form.get('vehicle_model','').strip()
        pw  = request.form.get('password','')
        pw2 = request.form.get('confirm_password','')
        errors = []
        if not val_name(fn):  errors.append('First name required.')
        if not val_name(ln):  errors.append('Last name required.')
        if not ph or not val_phone(ph): errors.append('Valid phone number required.')
        if not lic or not val_lic(lic): errors.append('Valid license number required.')
        if not plt or not val_plate(plt): errors.append('Vehicle plate required (4–12 alphanumeric).')
        if not pw or not val_pw(pw): errors.append('Password must be at least 6 characters.')
        if pw != pw2: errors.append('Passwords do not match.')
        if errors:
            for e in errors: flash(e, 'danger')
            return render_template('admin/driver_form.html', driver=None, form=request.form)
        try:
            m("INSERT INTO Drivers(first_name,last_name,phone_number,license_number,"
              "vehicle_plate,vehicle_model,password_hash) VALUES(%s,%s,%s,%s,%s,%s,%s)",
              (fn, ln, ph, lic, plt, vm, hash_pw(pw)))
            flash(f'Driver {fn} {ln} added successfully.', 'success')
            return redirect(url_for('admin_drivers'))
        except:
            flash('Phone number, license, or plate already registered.', 'danger')
    return render_template('admin/driver_form.html', driver=None, form={})

@app.route('/admin/drivers/<int:did>/edit', methods=['GET','POST'])
@auth('admin')
def admin_edit_driver(did):
    d = q("SELECT * FROM Drivers WHERE driver_id=%s", (did,), one=True)
    if not d:
        flash('Driver not found.', 'danger')
        return redirect(url_for('admin_drivers'))
    if request.method == 'POST':
        fn  = request.form.get('first_name','').strip()
        ln  = request.form.get('last_name','').strip()
        ph  = request.form.get('phone','').strip()
        lic = request.form.get('license','').strip().upper()
        plt = request.form.get('plate','').strip().upper()
        vm  = request.form.get('vehicle_model','').strip()
        pw  = request.form.get('new_password', request.form.get('password',''))
        pw2 = request.form.get('confirm_password','')
        errors = []
        if not val_name(fn): errors.append('First name required.')
        if not val_name(ln): errors.append('Last name required.')
        if ph and not val_phone(ph): errors.append('Invalid phone number.')
        if plt and not val_plate(plt): errors.append('Invalid plate format.')
        if pw and not val_pw(pw): errors.append('Password must be at least 6 characters.')
        if pw and pw != pw2: errors.append('Passwords do not match.')
        if errors:
            for e in errors: flash(e, 'danger')
            return render_template('admin/driver_form.html', driver=d, form=request.form)
        if pw:
            m("UPDATE Drivers SET first_name=%s,last_name=%s,phone_number=%s,license_number=%s,"
              "vehicle_plate=%s,vehicle_model=%s,password_hash=%s WHERE driver_id=%s",
              (fn, ln, ph or d['phone_number'], lic or d['license_number'],
               plt or d['vehicle_plate'], vm, hash_pw(pw), did))
        else:
            m("UPDATE Drivers SET first_name=%s,last_name=%s,phone_number=%s,license_number=%s,"
              "vehicle_plate=%s,vehicle_model=%s WHERE driver_id=%s",
              (fn, ln, ph or d['phone_number'], lic or d['license_number'],
               plt or d['vehicle_plate'], vm, did))
        flash(f'Driver {fn} {ln} updated.', 'success')
        return redirect(url_for('admin_drivers'))
    return render_template('admin/driver_form.html', driver=d, form=dict(d))

@app.route('/admin/drivers/<int:did>/toggle', methods=['POST'])
@auth('admin')
def admin_toggle_driver(did):
    d = q("SELECT is_available FROM Drivers WHERE driver_id=%s", (did,), one=True)
    if d:
        m("UPDATE Drivers SET is_available=%s WHERE driver_id=%s", (0 if d['is_available'] else 1, did))
        flash('Driver availability updated.', 'info')
    return redirect(url_for('admin_drivers'))

@app.route('/admin/drivers/<int:did>/delete', methods=['POST'])
@auth('admin')
def admin_delete_driver(did):
    active = q("SELECT COUNT(*) as c FROM Rides WHERE driver_id=%s AND ride_status IN ('ACCEPTED','IN_PROGRESS')",
               (did,), one=True)
    if active['c'] > 0:
        flash('Cannot delete a driver with active rides.', 'danger')
    else:
        m("DELETE FROM Drivers WHERE driver_id=%s", (did,))
        flash('Driver removed.', 'info')
    return redirect(url_for('admin_drivers'))

# ── Admin: Locations ─────────────────────────────────────────
@app.route('/admin/locations', methods=['GET','POST'])
@auth('admin')
def admin_locations():
    if request.method == 'POST':
        name = request.form.get('location_name','').strip()
        zone = request.form.get('area_zone','CBD')
        desc = request.form.get('description','').strip()
        if len(name) < 3:
            flash('Location name must be at least 3 characters.', 'danger')
        else:
            try:
                m("INSERT INTO Locations(location_name,area_zone,description) VALUES(%s,%s,%s)", (name,zone,desc))
                flash(f'Location "{name}" added.', 'success')
            except:
                flash('A location with that name already exists.', 'danger')
        return redirect(url_for('admin_locations'))
    search = request.args.get('q','')
    zone   = request.args.get('zone','')
    sql    = """SELECT l.*,
        (SELECT COUNT(*) FROM Rides WHERE pickup_location_id=l.location_id OR dropoff_location_id=l.location_id) as ride_count
        FROM Locations l WHERE 1=1"""
    args   = []
    if search: sql += " AND l.location_name LIKE %s"; args.append(f'%{search}%')
    if zone:   sql += " AND l.area_zone=%s"; args.append(zone)
    sql += " ORDER BY l.area_zone, l.location_name"
    locations = q(sql, args)
    return render_template('admin/locations.html', locations=locations, search=search, zone=zone)

@app.route('/admin/payments')
@auth('admin')
def admin_payments():
    search = request.args.get('q', '')
    status = request.args.get('status', '')
    method_id = request.args.get('method_id', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    sql = """SELECT p.*,
        r.passenger_name, r.passenger_phone, r.ride_status,
        pm.method_name,
        pu.location_name AS pickup_name, dr.location_name AS dropoff_name,
        CONCAT(d.first_name, ' ', d.last_name) AS driver_name
        FROM Payments p
        JOIN Rides r ON p.ride_id=r.ride_id
        JOIN Payment_Methods pm ON p.payment_method_id=pm.payment_method_id
        JOIN Locations pu ON r.pickup_location_id=pu.location_id
        JOIN Locations dr ON r.dropoff_location_id=dr.location_id
        LEFT JOIN Drivers d ON p.received_by_driver_id=d.driver_id
        WHERE 1=1"""
    args = []
    if search:
        sql += """ AND (
            CAST(p.ride_id AS CHAR) LIKE %s OR
            r.passenger_name LIKE %s OR
            r.passenger_phone LIKE %s OR
            COALESCE(CONCAT(d.first_name, ' ', d.last_name), '') LIKE %s
        )"""
        args += [f'%{search}%'] * 4
    if status:
        sql += " AND p.payment_status=%s"
        args.append(status)
    if method_id:
        sql += " AND p.payment_method_id=%s"
        args.append(method_id)
    if date_from:
        sql += " AND DATE(COALESCE(p.paid_at, r.requested_at))>=%s"
        args.append(date_from)
    if date_to:
        sql += " AND DATE(COALESCE(p.paid_at, r.requested_at))<=%s"
        args.append(date_to)
    sql += " ORDER BY COALESCE(p.paid_at, r.requested_at) DESC, p.payment_id DESC"
    payments = q(sql, args)
    methods = q("SELECT * FROM Payment_Methods WHERE is_active=1 ORDER BY method_name")
    summary = q("""SELECT
        SUM(CASE WHEN payment_status='COMPLETED' THEN 1 ELSE 0 END) as completed,
        SUM(CASE WHEN payment_status='PENDING' THEN 1 ELSE 0 END) as pending,
        SUM(CASE WHEN payment_status='CANCELLED' THEN 1 ELSE 0 END) as cancelled,
        COALESCE(SUM(CASE WHEN payment_status='COMPLETED' THEN amount_paid ELSE 0 END),0) as revenue
        FROM Payments""", one=True)
    return render_template('admin/payments.html', payments=payments, methods=methods,
                           summary=summary, search=search, status=status,
                           method_id=method_id, date_from=date_from, date_to=date_to)

@app.route('/rate/<int:ride_id>', methods=['POST'])
def rate_ride(ride_id):
    ride = q("SELECT ride_id, ride_status FROM Rides WHERE ride_id=%s", (ride_id,), one=True)
    if not ride:
        flash('Ride not found.', 'danger')
        return redirect(url_for('book'))
    if ride['ride_status'] != 'COMPLETED':
        flash('You can only rate a completed ride.', 'warning')
        return redirect(url_for('track', ride_id=ride_id))

    score = request.form.get('rating_score', type=int)
    comment = request.form.get('rating_comment', '').strip()
    if score not in (1, 2, 3, 4, 5):
        flash('Please choose a rating between 1 and 5.', 'danger')
        return redirect(url_for('track', ride_id=ride_id))

    m("""INSERT INTO Ride_Ratings(ride_id, rating_score, rating_comment)
         VALUES(%s, %s, %s)
         ON DUPLICATE KEY UPDATE
           rating_score=VALUES(rating_score),
           rating_comment=VALUES(rating_comment)""",
      (ride_id, score, comment[:255]))
    flash('Thanks for rating your ride.', 'success')
    return redirect(url_for('track', ride_id=ride_id))

@app.route('/admin/locations/<int:lid>/edit', methods=['GET','POST'])
@auth('admin')
def admin_edit_location(lid):
    loc = q("""SELECT l.*,
        (SELECT COUNT(*) FROM Rides WHERE pickup_location_id=l.location_id OR dropoff_location_id=l.location_id) as ride_count
        FROM Locations l WHERE l.location_id=%s""", (lid,), one=True)
    if not loc:
        flash('Location not found.', 'danger')
        return redirect(url_for('admin_locations'))
    if request.method == 'POST':
        name = request.form.get('location_name','').strip()
        zone = request.form.get('area_zone','CBD')
        desc = request.form.get('description','').strip()
        if len(name) < 3:
            flash('Location name must be at least 3 characters.', 'danger')
        else:
            m("UPDATE Locations SET location_name=%s,area_zone=%s,description=%s WHERE location_id=%s",
              (name, zone, desc, lid))
            flash(f'Location updated to "{name}".', 'success')
            return redirect(url_for('admin_locations'))
    return render_template('admin/location_form.html', loc=loc)

@app.route('/admin/locations/<int:lid>/toggle', methods=['POST'])
@auth('admin')
def admin_toggle_location(lid):
    loc = q("SELECT is_active FROM Locations WHERE location_id=%s", (lid,), one=True)
    if loc:
        m("UPDATE Locations SET is_active=%s WHERE location_id=%s", (0 if loc['is_active'] else 1, lid))
        flash('Location status updated.', 'info')
    return redirect(url_for('admin_locations'))

# ── Admin: Reports ────────────────────────────────────────────
@app.route('/admin/reports', methods=['GET','POST'])
@auth('admin')
def admin_reports():
    today = datetime.date.today().isoformat()
    if request.method == 'POST':
        rdate = request.form.get('report_date','')
        rtype = request.form.get('report_type','Daily Summary')
        notes = request.form.get('notes','').strip()
        lid   = request.form.get('top_location_id','') or None
        if not rdate:
            flash('Please select a report date.', 'danger')
        else:
            totals = q("SELECT COUNT(*) as c, COALESCE(SUM(fare_amount),0) as rev "
                       "FROM Rides WHERE DATE(requested_at)=%s AND ride_status='COMPLETED'",
                       (rdate,), one=True)
            if not lid:
                top = q("SELECT pickup_location_id FROM Rides WHERE DATE(requested_at)=%s "
                        "GROUP BY pickup_location_id ORDER BY COUNT(*) DESC LIMIT 1", (rdate,), one=True)
                lid = top['pickup_location_id'] if top else None
            m("INSERT INTO Ride_Reports(admin_id,report_type,report_date,total_rides,total_revenue,"
              "top_location_id,notes) VALUES(%s,%s,%s,%s,%s,%s,%s)",
              (session['uid'], rtype, rdate, totals['c'], totals['rev'], lid, notes))
            flash(f'{rtype} report for {rdate} generated.', 'success')
        return redirect(url_for('admin_reports'))
    search      = request.args.get('q','')
    type_filter = request.args.get('type_filter','')
    sql  = """SELECT rr.*, a.username, l.location_name AS top_location_name
        FROM Ride_Reports rr
        JOIN Admin_Users a ON rr.admin_id=a.admin_id
        LEFT JOIN Locations l ON rr.top_location_id=l.location_id WHERE 1=1"""
    args = []
    if search:      sql += " AND (rr.report_type LIKE %s OR rr.notes LIKE %s)"; args += [f'%{search}%']*2
    if type_filter: sql += " AND rr.report_type=%s"; args.append(type_filter)
    sql += " ORDER BY rr.generated_at DESC"
    reports   = q(sql, args)
    daily     = q("""SELECT DATE(requested_at) as day, COUNT(*) as rides,
        COALESCE(SUM(fare_amount),0) as revenue
        FROM Rides GROUP BY DATE(requested_at) ORDER BY day DESC LIMIT 14""")
    locations = q("SELECT * FROM Locations WHERE is_active=1 ORDER BY location_name")
    return render_template('admin/reports.html', reports=reports, daily=daily,
                           locations=locations, today=today,
                           search=search, type_filter=type_filter)

@app.route('/admin/reports/<int:rid>/delete', methods=['POST'])
@auth('admin')
def admin_delete_report(rid):
    m("DELETE FROM Ride_Reports WHERE report_id=%s", (rid,))
    flash('Report deleted.', 'info')
    return redirect(url_for('admin_reports'))

@app.route('/api/fare')
def api_fare():
    """Return the fixed fare for two locations. Called by JS on the booking form."""
    pickup_id  = request.args.get('pickup', type=int)
    dropoff_id = request.args.get('dropoff', type=int)
    if not pickup_id or not dropoff_id:
        return jsonify({'fare': None})
    fare = get_fare(pickup_id, dropoff_id)
    return jsonify({'fare': fare})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
