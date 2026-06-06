from pathlib import Path
import re

root = Path(r"C:\Users\windows 10\Desktop\Principle of Database Design and Data Management(CS3432)()\Project\database")
app_path = root / "app.py"
text = app_path.read_text(encoding="utf-8")

old_helpers = """def m(sql, args=()):
    \"\"\"Execute INSERT / UPDATE / DELETE, commit, return lastrowid.\"\"\"
    cur = mysql.connection.cursor()
    cur.execute(sql, args)
    mysql.connection.commit()
    lid = cur.lastrowid
    cur.close()
    return lid
"""
new_helpers = """def m(sql, args=()):
    \"\"\"Execute INSERT / UPDATE / DELETE, commit, return lastrowid.\"\"\"
    cur = mysql.connection.cursor()
    cur.execute(sql, args)
    mysql.connection.commit()
    lid = cur.lastrowid
    cur.close()
    return lid


def m_count(sql, args=()):
    \"\"\"Execute INSERT / UPDATE / DELETE, commit, return affected row count.\"\"\"
    cur = mysql.connection.cursor()
    cur.execute(sql, args)
    mysql.connection.commit()
    count = cur.rowcount
    cur.close()
    return count
"""
text = text.replace(old_helpers, new_helpers)

marker = "# â”€â”€ Auth decorator"
insert_block = """def create_notification(audience_role, title, message, level='info', ride_id=None, audience_user_id=None):
    m(\"\"\"
        INSERT INTO Notifications (
            audience_role, audience_user_id, ride_id, title, message, level
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    \"\"\", (audience_role, audience_user_id, ride_id, title, message, level))


def get_notifications(audience_role, audience_user_id=None, limit=6):
    if audience_user_id is None:
        return q(\"\"\"
            SELECT *
            FROM Notifications
            WHERE audience_role = %s
              AND audience_user_id IS NULL
            ORDER BY created_at DESC
            LIMIT %s
        \"\"\", (audience_role, limit))

    return q(\"\"\"
        SELECT *
        FROM Notifications
        WHERE audience_role = %s
          AND audience_user_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    \"\"\", (audience_role, audience_user_id, limit))


def unread_notification_count(audience_role, audience_user_id=None):
    if audience_user_id is None:
        row = q(\"\"\"
            SELECT COUNT(*) AS c
            FROM Notifications
            WHERE audience_role = %s
              AND audience_user_id IS NULL
              AND is_read = 0
        \"\"\", (audience_role,), one=True)
    else:
        row = q(\"\"\"
            SELECT COUNT(*) AS c
            FROM Notifications
            WHERE audience_role = %s
              AND audience_user_id = %s
              AND is_read = 0
        \"\"\", (audience_role, audience_user_id), one=True)
    return row['c'] if row else 0


def mark_notifications_read(audience_role, audience_user_id=None):
    if audience_user_id is None:
        m(\"\"\"
            UPDATE Notifications
            SET is_read = 1
            WHERE audience_role = %s
              AND audience_user_id IS NULL
              AND is_read = 0
        \"\"\", (audience_role,))
        return

    m(\"\"\"
        UPDATE Notifications
        SET is_read = 1
        WHERE audience_role = %s
          AND audience_user_id = %s
          AND is_read = 0
    \"\"\", (audience_role, audience_user_id))


def find_best_available_driver(pickup_location_id):
    pickup = q(\"SELECT location_id, area_zone FROM Locations WHERE location_id=%s\", (pickup_location_id,), one=True)
    if not pickup:
        return None

    return q(\"\"\"
        SELECT d.driver_id, d.first_name, d.last_name
        FROM Drivers d
        LEFT JOIN (
            SELECT v.driver_id, v.current_location_id
            FROM Vehicle_Status v
            JOIN (
                SELECT driver_id, MAX(status_id) AS max_status_id
                FROM Vehicle_Status
                GROUP BY driver_id
            ) latest ON latest.max_status_id = v.status_id
        ) vs ON vs.driver_id = d.driver_id
        LEFT JOIN Locations dl ON dl.location_id = vs.current_location_id
        WHERE d.is_available = 1
        ORDER BY
            CASE
                WHEN vs.current_location_id = %s THEN 0
                WHEN dl.area_zone = %s THEN 1
                ELSE 2
            END,
            d.driver_id ASC
        LIMIT 1
    \"\"\", (pickup_location_id, pickup['area_zone']), one=True)


def auto_assign_ride(ride_id, pickup_location_id):
    driver = find_best_available_driver(pickup_location_id)
    if not driver:
        return None

    updated = m_count(\"\"\"
        UPDATE Rides
        SET driver_id = %s,
            ride_status = 'ASSIGNED'
        WHERE ride_id = %s
          AND ride_status = 'REQUESTED'
    \"\"\", (driver['driver_id'], ride_id))

    if not updated:
        return None

    m(\"UPDATE Drivers SET is_available = 0 WHERE driver_id = %s\", (driver['driver_id'],))
    return driver


"""
text = text.replace(marker, insert_block + marker)

book_block = """@app.route('/book', methods=['GET', 'POST'])
def book():
    locations = q(\"\"\"
        SELECT * FROM Locations
        WHERE is_active=1
        ORDER BY area_zone, location_name
    \"\"\")
    methods = q(\"\"\"
        SELECT * FROM Payment_Methods
        WHERE is_active=1
        ORDER BY method_name
    \"\"\")
    fares = q(\"SELECT * FROM Fares ORDER BY zone_from, zone_to\")

    if request.method == 'POST':
        name = request.form.get('passenger_name', '').strip()
        phone = request.form.get('passenger_phone', '').strip()
        pickup = request.form.get('pickup', '')
        dropoff = request.form.get('dropoff', '')
        pay = request.form.get('payment', '')
        notes = request.form.get('notes', '').strip()

        errors = []

        if not val_name(name):
            errors.append('Please enter your full name (at least 2 characters).')

        if not phone:
            errors.append('Phone number is required.')
        elif not val_phone(phone):
            errors.append('Enter a valid phone number (e.g. +26657123456).')

        if not pickup:
            errors.append('Please select a pickup location.')

        if not dropoff:
            errors.append('Please select a destination.')

        if pickup and dropoff and pickup == dropoff:
            errors.append('Pickup and destination cannot be the same location.')

        if not pay:
            errors.append('Please select a payment method.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template(
                'book.html',
                locations=locations,
                methods=methods,
                form=request.form,
                fares=fares
            )

        existing_ride = q(\"\"\"
            SELECT ride_id
            FROM Rides
            WHERE passenger_phone = %s
              AND pickup_location_id = %s
              AND dropoff_location_id = %s
              AND ride_status IN ('REQUESTED', 'ASSIGNED', 'ACCEPTED', 'IN_PROGRESS')
            ORDER BY requested_at DESC
            LIMIT 1
        \"\"\", (phone, int(pickup), int(dropoff)), one=True)

        if existing_ride:
            flash(
                \"You already have an active ride for this route. We’ve opened the existing ride.\",
                'warning'
            )
            return redirect(url_for('track', ride_id=existing_ride['ride_id']))

        fare = get_fare(int(pickup), int(dropoff))
        if fare is None:
            flash('Could not calculate fare for this route. Please try again.', 'danger')
            return render_template(
                'book.html',
                locations=locations,
                methods=methods,
                form=request.form,
                fares=fares
            )

        ride_id = m(\"\"\"
            INSERT INTO Rides (
                passenger_name,
                passenger_phone,
                pickup_location_id,
                dropoff_location_id,
                payment_method_id,
                notes,
                ride_status,
                fare_amount
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'REQUESTED', %s)
        \"\"\", (name, phone, int(pickup), int(dropoff), int(pay), notes, fare))

        create_notification('admin', 'New ride booked', f'Ride #{ride_id} booked by {name}.', 'info', ride_id)
        assigned_driver = auto_assign_ride(ride_id, int(pickup))

        if assigned_driver:
            driver_name = f\"{assigned_driver['first_name']} {assigned_driver['last_name']}\"
            create_notification(
                'driver',
                'Ride auto-assigned',
                f'Ride #{ride_id} from {name} has been assigned to you.',
                'success',
                ride_id,
                assigned_driver['driver_id']
            )
            create_notification('admin', 'Ride auto-assigned', f'Ride #{ride_id} assigned to {driver_name}.', 'success', ride_id)
            flash(
                f'Ride #{ride_id} booked! Fare: M {fare:.2f}. Driver {driver_name} has been assigned.',
                'success'
            )
        else:
            create_notification('admin', 'Driver needed', f'Ride #{ride_id} is waiting for an available driver.', 'warning', ride_id)
            flash(
                f'Ride #{ride_id} booked! Fare: M {fare:.2f}. No driver is available yet, so your ride is pending assignment.',
                'success'
            )

        return redirect(url_for('track', ride_id=ride_id))

    return render_template('book.html', locations=locations, methods=methods, form={}, fares=fares)
"""
text = re.sub(r"@app\.route\('/book', methods=\['GET', 'POST'\]\)\ndef book\(\):.*?return render_template\('book\.html', locations=locations, methods=methods, form=\{\}, fares=fares\)\n", book_block + "\n", text, flags=re.S)

driver_home_block = """@app.route('/driver')
@auth('driver')
def driver_home():
    driver = q(\"SELECT * FROM Drivers WHERE driver_id=%s\", (session['uid'],), one=True)

    pending = []
    if driver and driver['is_available']:
        pending = q(\"\"\"
            SELECT r.*,
                   pu.location_name AS pickup_name,
                   dr.location_name AS dropoff_name,
                   pm.method_name
            FROM Rides r
            JOIN Locations pu ON r.pickup_location_id = pu.location_id
            JOIN Locations dr ON r.dropoff_location_id = dr.location_id
            JOIN Payment_Methods pm ON r.payment_method_id = pm.payment_method_id
            WHERE r.ride_status = 'REQUESTED'
              AND r.driver_id IS NULL
            ORDER BY r.requested_at ASC
        \"\"\")

    my_rides = q(\"\"\"
        SELECT r.*,
               pu.location_name AS pickup_name,
               dr.location_name AS dropoff_name,
               pm.method_name
        FROM Rides r
        JOIN Locations pu ON r.pickup_location_id = pu.location_id
        JOIN Locations dr ON r.dropoff_location_id = dr.location_id
        JOIN Payment_Methods pm ON r.payment_method_id = pm.payment_method_id
        WHERE r.driver_id = %s
          AND r.ride_status IN ('ASSIGNED','ACCEPTED','IN_PROGRESS')
        ORDER BY FIELD(r.ride_status, 'ASSIGNED', 'ACCEPTED', 'IN_PROGRESS'), r.requested_at ASC
    \"\"\", (session['uid'],))

    stats = q(\"\"\"
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN ride_status='COMPLETED' THEN 1 ELSE 0 END) AS completed,
               COALESCE(SUM(CASE WHEN ride_status='COMPLETED' THEN fare_amount ELSE 0 END), 0) AS earned
        FROM Rides
        WHERE driver_id = %s
    \"\"\", (session['uid'],), one=True)

    unread_notifications = unread_notification_count('driver', session['uid'])
    notifications = get_notifications('driver', session['uid'], 6)
    if unread_notifications:
        mark_notifications_read('driver', session['uid'])

    return render_template(
        'driver/home.html',
        driver=driver,
        pending=pending,
        my_rides=my_rides,
        stats=stats,
        notifications=notifications,
        unread_notifications=unread_notifications
    )
"""
text = re.sub(r"@app\.route\('/driver'\)\n@auth\('driver'\)\ndef driver_home\(\):.*?return render_template\(\n\s*'driver/home\.html',\n\s*driver=driver,\n\s*pending=pending,\n\s*my_rides=my_rides,\n\s*stats=stats\n\s*\)\n", driver_home_block + "\n", text, flags=re.S)

driver_accept_block = """@app.route('/driver/accept/<int:ride_id>', methods=['POST'])
@auth('driver')
def driver_accept(ride_id):
    ride = q(\"\"\"
        SELECT *
        FROM Rides
        WHERE ride_id = %s
          AND (
              (ride_status = 'REQUESTED' AND driver_id IS NULL)
              OR (ride_status = 'ASSIGNED' AND driver_id = %s)
          )
    \"\"\", (ride_id, session['uid']), one=True)

    if ride:
        if ride['ride_status'] == 'REQUESTED':
            m(\"\"\"
                UPDATE Rides
                SET driver_id = %s,
                    ride_status = 'ACCEPTED',
                    accepted_at = NOW()
                WHERE ride_id = %s
                  AND ride_status = 'REQUESTED'
            \"\"\", (session['uid'], ride_id))
        else:
            m(\"\"\"
                UPDATE Rides
                SET ride_status = 'ACCEPTED',
                    accepted_at = NOW()
                WHERE ride_id = %s
                  AND driver_id = %s
                  AND ride_status = 'ASSIGNED'
            \"\"\", (ride_id, session['uid']))

        m(\"UPDATE Drivers SET is_available = 0 WHERE driver_id = %s\", (session['uid'],))
        create_notification('admin', 'Ride accepted', f'Ride #{ride_id} accepted by {session[\"name\"]}.', 'success', ride_id)
        create_notification('driver', 'Ride accepted', f'You accepted ride #{ride_id}.', 'info', ride_id, session['uid'])
        flash(f'Ride #{ride_id} accepted! Head to the pickup location.', 'success')
    else:
        flash('Ride no longer available.', 'warning')

    return redirect(url_for('driver_home'))
"""
text = re.sub(r"@app\.route\('/driver/accept/<int:ride_id>', methods=\['POST'\]\)\n@auth\('driver'\)\ndef driver_accept\(ride_id\):.*?return redirect\(url_for\('driver_home'\)\)\n", driver_accept_block + "\n", text, flags=re.S)

driver_start_block = """@app.route('/driver/start/<int:ride_id>', methods=['POST'])
@auth('driver')
def driver_start(ride_id):
    ride = q(\"\"\"
        SELECT passenger_name
        FROM Rides
        WHERE ride_id = %s
          AND driver_id = %s
          AND ride_status = 'ACCEPTED'
    \"\"\", (ride_id, session['uid']), one=True)

    if not ride:
        flash('Ride is not ready to start.', 'warning')
        return redirect(url_for('driver_home'))

    m(\"\"\"
        UPDATE Rides
        SET ride_status = 'IN_PROGRESS'
        WHERE ride_id = %s
          AND driver_id = %s
          AND ride_status = 'ACCEPTED'
    \"\"\", (ride_id, session['uid']))

    create_notification('admin', 'Ride in progress', f'Ride #{ride_id} is now in progress.', 'info', ride_id)
    flash('Ride started!', 'success')
    return redirect(url_for('driver_home'))
"""
text = re.sub(r"@app\.route\('/driver/start/<int:ride_id>', methods=\['POST'\]\)\n@auth\('driver'\)\ndef driver_start\(ride_id\):.*?return redirect\(url_for\('driver_home'\)\)\n", driver_start_block + "\n", text, flags=re.S)

driver_complete_block = """@app.route('/driver/complete/<int:ride_id>', methods=['POST'])
@auth('driver')
def driver_complete(ride_id):
    ride = q(\"\"\"
        SELECT fare_amount
        FROM Rides
        WHERE ride_id = %s
          AND driver_id = %s
          AND ride_status = 'IN_PROGRESS'
    \"\"\", (ride_id, session['uid']), one=True)

    if not ride:
        flash('Ride not found or already completed.', 'danger')
        return redirect(url_for('driver_home'))

    m(\"\"\"
        UPDATE Rides
        SET ride_status = 'COMPLETED',
            completed_at = NOW()
        WHERE ride_id = %s
          AND driver_id = %s
          AND ride_status = 'IN_PROGRESS'
    \"\"\", (ride_id, session['uid']))

    m(\"UPDATE Drivers SET is_available = 1 WHERE driver_id = %s\", (session['uid'],))
    create_notification('admin', 'Ride completed', f'Ride #{ride_id} was completed by {session[\"name\"]}.', 'success', ride_id)
    create_notification('driver', 'Ride completed', f'Ride #{ride_id} was marked as completed.', 'success', ride_id, session['uid'])

    fare = ride['fare_amount'] or 0
    flash(f'Ride completed! Collect M {fare:.2f} from the passenger.', 'success')
    return redirect(url_for('driver_home'))
"""
text = re.sub(r"@app\.route\('/driver/complete/<int:ride_id>', methods=\['POST'\]\)\n@auth\('driver'\)\ndef driver_complete\(ride_id\):.*?return redirect\(url_for\('driver_home'\)\)\n", driver_complete_block + "\n", text, flags=re.S)

admin_home_block = """@app.route('/admin')
@auth('admin')
def admin_home():
    stats = q(\"\"\"
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN ride_status='COMPLETED' THEN 1 ELSE 0 END) AS completed,
               SUM(CASE WHEN ride_status='CANCELLED' THEN 1 ELSE 0 END) AS cancelled,
               SUM(CASE WHEN ride_status IN ('REQUESTED','ASSIGNED') THEN 1 ELSE 0 END) AS pending,
               SUM(CASE WHEN ride_status='IN_PROGRESS' THEN 1 ELSE 0 END) AS in_progress,
               COALESCE(SUM(fare_amount), 0) AS revenue
        FROM Rides
    \"\"\", one=True)

    drivers_total = q(\"SELECT COUNT(*) AS c FROM Drivers\", one=True)
    drivers_online = q(\"SELECT COUNT(*) AS c FROM Drivers WHERE is_available=1\", one=True)

    recent = q(\"\"\"
        SELECT r.*,
               pu.location_name AS pickup_name,
               dr.location_name AS dropoff_name,
               CONCAT(d.first_name, ' ', d.last_name) AS driver_name,
               pm.method_name
        FROM Rides r
        JOIN Locations pu ON r.pickup_location_id = pu.location_id
        JOIN Locations dr ON r.dropoff_location_id = dr.location_id
        JOIN Payment_Methods pm ON r.payment_method_id = pm.payment_method_id
        LEFT JOIN Drivers d ON r.driver_id = d.driver_id
        ORDER BY r.requested_at DESC
        LIMIT 8
    \"\"\")

    top_locs = q(\"\"\"
        SELECT l.location_name, COUNT(r.ride_id) AS cnt
        FROM Locations l
        LEFT JOIN Rides r ON l.location_id = r.pickup_location_id
        GROUP BY l.location_id, l.location_name
        ORDER BY cnt DESC
        LIMIT 5
    \"\"\")

    pay_stats = q(\"\"\"
        SELECT pm.method_name,
               COUNT(r.ride_id) AS cnt,
               COALESCE(SUM(r.fare_amount), 0) AS total
        FROM Payment_Methods pm
        LEFT JOIN Rides r ON pm.payment_method_id = r.payment_method_id
        GROUP BY pm.payment_method_id, pm.method_name
        ORDER BY pm.method_name
    \"\"\")

    unread_notifications = unread_notification_count('admin')
    notifications = get_notifications('admin', None, 6)
    if unread_notifications:
        mark_notifications_read('admin')

    return render_template(
        'admin/home.html',
        stats=stats,
        drivers_total=drivers_total,
        drivers_online=drivers_online,
        recent=recent,
        top_locs=top_locs,
        pay_stats=pay_stats,
        notifications=notifications,
        unread_notifications=unread_notifications
    )
"""
text = re.sub(r"@app\.route\('/admin'\)\n@auth\('admin'\)\ndef admin_home\(\):.*?return render_template\(\n\s*'admin/home\.html',\n\s*stats=stats,\n\s*drivers_total=drivers_total,\n\s*drivers_online=drivers_online,\n\s*recent=recent,\n\s*top_locs=top_locs,\n\s*pay_stats=pay_stats\n\s*\)\n", admin_home_block + "\n", text, flags=re.S)

admin_rides_block = """@app.route('/admin/rides')
@auth('admin')
def admin_rides():
    search = request.args.get('q', '')
    status = request.args.get('status', '')
    loc_id = request.args.get('loc_id', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    sql = \"\"\"
        SELECT r.*,
               pu.location_name AS pickup_name,
               dr.location_name AS dropoff_name,
               CONCAT(d.first_name, ' ', d.last_name) AS driver_name,
               pm.method_name,
               p.payment_status
        FROM Rides r
        JOIN Locations pu ON r.pickup_location_id = pu.location_id
        JOIN Locations dr ON r.dropoff_location_id = dr.location_id
        JOIN Payment_Methods pm ON r.payment_method_id = pm.payment_method_id
        LEFT JOIN Drivers d ON r.driver_id = d.driver_id
        LEFT JOIN Payments p ON p.ride_id = r.ride_id
        WHERE 1=1
    \"\"\"
    args = []

    if search:
        sql += \"\"\"
            AND (
                r.passenger_name LIKE %s
                OR r.passenger_phone LIKE %s
                OR COALESCE(CONCAT(d.first_name, ' ', d.last_name), '') LIKE %s
                OR pu.location_name LIKE %s
                OR dr.location_name LIKE %s
            )
        \"\"\"
        args += [f'%{search}%'] * 5

    if status:
        sql += \" AND r.ride_status = %s\"
        args.append(status)

    if loc_id:
        sql += \" AND (r.pickup_location_id = %s OR r.dropoff_location_id = %s)\"
        args += [loc_id, loc_id]

    if date_from:
        sql += \" AND DATE(r.requested_at) >= %s\"
        args.append(date_from)

    if date_to:
        sql += \" AND DATE(r.requested_at) <= %s\"
        args.append(date_to)

    sql += \" ORDER BY r.requested_at DESC\"

    rides = q(sql, tuple(args))
    locations = q(\"\"\"
        SELECT * FROM Locations
        WHERE is_active=1
        ORDER BY location_name
    \"\"\")

    return render_template(
        'admin/rides.html',
        rides=rides,
        locations=locations,
        search=search,
        status=status,
        loc_id=loc_id,
        date_from=date_from,
        date_to=date_to
    )
"""
text = re.sub(r"@app\.route\('/admin/rides'\)\n@auth\('admin'\)\ndef admin_rides\(\):.*?return render_template\(\n\s*'admin/rides\.html',\n\s*rides=rides,\n\s*locations=locations,\n\s*search=search,\n\s*status=status,\n\s*loc_id=loc_id,\n\s*date_from=date_from,\n\s*date_to=date_to\n\s*\)\n", admin_rides_block + "\n", text, flags=re.S)

admin_cancel_block = """@app.route('/admin/rides/<int:ride_id>/cancel', methods=['POST'])
@auth('admin')
def admin_cancel_ride(ride_id):
    ride = q(\"SELECT * FROM Rides WHERE ride_id=%s\", (ride_id,), one=True)

    if ride and ride['ride_status'] in ('REQUESTED', 'ASSIGNED', 'ACCEPTED', 'IN_PROGRESS'):
        m(\"UPDATE Rides SET ride_status='CANCELLED' WHERE ride_id=%s\", (ride_id,))
        if ride['driver_id']:
            m(\"UPDATE Drivers SET is_available=1 WHERE driver_id=%s\", (ride['driver_id'],))
            create_notification('driver', 'Ride cancelled', f'Ride #{ride_id} was cancelled by admin.', 'warning', ride_id, ride['driver_id'])
        create_notification('admin', 'Ride cancelled', f'Ride #{ride_id} was cancelled.', 'warning', ride_id)
        flash(f'Ride #{ride_id} cancelled.', 'info')
    else:
        flash('This ride cannot be cancelled.', 'danger')

    return redirect(url_for('admin_rides'))
"""
text = re.sub(r"@app\.route\('/admin/rides/<int:ride_id>/cancel', methods=\['POST'\]\)\n@auth\('admin'\)\ndef admin_cancel_ride\(ride_id\):.*?return redirect\(url_for\('admin_rides'\)\)\n", admin_cancel_block + "\n", text, flags=re.S)

app_path.write_text(text, encoding="utf-8")

(root / "templates" / "driver" / "home.html").write_text("""{% extends \"base.html\" %}
{% block title %}Driver Dashboard{% endblock %}
{% block topbar %}{% endblock %}
{% block extra_css %}
<style>
.driver-shell{width:100vw;min-height:100vh;margin-left:calc(50% - 50vw);background:linear-gradient(135deg,#0a1628 0%,#1e4d8c 100%);padding:28px 20px 110px;color:#fff}
.driver-wrap{max-width:980px;margin:0 auto}
.driver-top{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:24px}
.driver-back{display:inline-flex;align-items:center;gap:8px;color:#cbd5e1;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.12);padding:10px 14px;border-radius:12px;text-decoration:none}
.driver-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px}
.driver-card{background:rgba(255,255,255,.05);border-radius:20px;padding:20px;border:1px solid rgba(255,255,255,.1)}
.driver-alert{background:#06b6d4;color:#0a1628;padding:10px 14px;border-radius:10px;font-weight:700;margin-bottom:16px}
.driver-action{width:100%;padding:12px 14px;background:#06b6d4;color:#0a1628;border:none;border-radius:12px;font-weight:800;cursor:pointer;margin-top:12px}
.driver-subtle{background:rgba(255,255,255,.08);color:#fff;border:1px solid rgba(255,255,255,.15)}
.notif-badge{display:inline-flex;align-items:center;justify-content:center;min-width:24px;height:24px;padding:0 8px;border-radius:999px;background:#f5c518;color:#111827;font-size:.85rem;font-weight:800;margin-left:10px}
.notif-item{padding:12px;background:rgba(255,255,255,.04);border-radius:12px;margin-bottom:10px;border-left:3px solid rgba(255,255,255,.18)}
.notif-item.success{border-left-color:#22c55e}
.notif-item.warning{border-left-color:#f59e0b}
.notif-item.danger{border-left-color:#ef4444}
.notif-item.info{border-left-color:#38bdf8}
.notif-time{color:#94a3b8;font-size:.82rem;margin-top:6px}
</style>
{% endblock %}
{% block content %}
<div class=\"driver-shell\">
  <div class=\"driver-wrap\">
    <div class=\"driver-top\">
      <a href=\"/logout\" class=\"driver-back\">Exit</a>
      <h2 style=\"font-size:2rem;font-weight:800\">Driver Dispatch Hub{% if unread_notifications %}<span class=\"notif-badge\">{{ unread_notifications }}</span>{% endif %}</h2>
      <form method=\"POST\" action=\"/driver/toggle\" id=\"toggleAvailabilityForm\">
        <button type=\"button\" class=\"driver-back\" onclick=\"showSheet('{% if driver.is_available %}Go Offline?{% else %}Go Online?{% endif %}','{% if driver.is_available %}You will stop receiving requests.{% else %}You will start receiving requests.{% endif %}',()=>document.getElementById('toggleAvailabilityForm').submit())\">{% if driver.is_available %}Online{% else %}Offline{% endif %}</button>
      </form>
    </div>
    {% if my_rides and my_rides[0].ride_status == 'ASSIGNED' %}
      <div class=\"driver-alert\">AUTO-ASSIGNED RIDE READY FOR ACCEPTANCE</div>
    {% elif pending %}
      <div class=\"driver-alert\">NEW REQUEST RECEIVED</div>
    {% endif %}
    <div class=\"driver-grid\">
      <div class=\"driver-card\">
        <h3 style=\"margin-bottom:12px\">Summary</h3>
        <div style=\"color:#94a3b8;line-height:1.9\">Driver: <strong style=\"color:#fff\">{{ session.name }}</strong><br>Total rides: <strong style=\"color:#fff\">{{ stats.total or 0 }}</strong><br>Completed: <strong style=\"color:#fff\">{{ stats.completed or 0 }}</strong><br>Earned: <strong style=\"color:#67e8f9\">M {{ '%.2f'|format(stats.earned or 0) }}</strong></div>
      </div>
      <div class=\"driver-card\">
        <h3 style=\"margin-bottom:12px\">Active Ride</h3>
        {% if my_rides %}
          {% set r = my_rides[0] %}
          <div><strong>#{{ r.ride_id }}</strong><br>{{ r.pickup_name }} -> {{ r.dropoff_name }}<br>{{ r.passenger_name }} ({{ r.passenger_phone }})</div>
          {% if r.ride_status == 'ASSIGNED' %}
          <form method=\"POST\" action=\"/driver/accept/{{ r.ride_id }}\" id=\"assignedForm{{ r.ride_id }}\"><button type=\"button\" class=\"driver-action\" onclick=\"showSheet('Accept Assigned Ride?','Confirm you are taking ride #{{ r.ride_id }}.',()=>document.getElementById('assignedForm{{ r.ride_id }}').submit())\">ACCEPT ASSIGNED RIDE</button></form>
          {% elif r.ride_status == 'ACCEPTED' %}
          <form method=\"POST\" action=\"/driver/start/{{ r.ride_id }}\" id=\"sForm{{ r.ride_id }}\"><button type=\"button\" class=\"driver-action driver-subtle\" onclick=\"showSheet('Start Ride?','Confirm you have picked up {{ r.passenger_name }}.',()=>document.getElementById('sForm{{ r.ride_id }}').submit())\">START RIDE</button></form>
          {% elif r.ride_status == 'IN_PROGRESS' %}
          <form method=\"POST\" action=\"/driver/complete/{{ r.ride_id }}\" id=\"cForm{{ r.ride_id }}\"><button type=\"button\" class=\"driver-action\" onclick=\"showSheet('Complete Ride?','Confirm you have collected M {{ '%.2f'|format(r.fare_amount or 0) }} from {{ r.passenger_name }}.',()=>document.getElementById('cForm{{ r.ride_id }}').submit())\">COMPLETE RIDE</button></form>
          {% else %}
          <div style=\"margin-top:10px;color:#94a3b8\">Status: {{ r.ride_status.replace('_',' ') }}</div>
          {% endif %}
        {% else %}
          <div style=\"color:#94a3b8\">No active ride.</div>
        {% endif %}
      </div>
      <div class=\"driver-card\">
        <h3 style=\"margin-bottom:12px\">Notifications</h3>
        {% for n in notifications %}
          <div class=\"notif-item {{ n.level }}\">
            <div style=\"font-weight:700\">{{ n.title }}</div>
            <div style=\"margin-top:4px;color:#cbd5e1\">{{ n.message }}</div>
            <div class=\"notif-time\">{{ n.created_at.strftime('%Y-%m-%d %H:%M') if n.created_at else '' }}</div>
          </div>
        {% else %}
          <div style=\"color:#94a3b8\">No notifications yet.</div>
        {% endfor %}
      </div>
      <div class=\"driver-card\">
        <h3 style=\"margin-bottom:12px\">Available Requests</h3>
        {% if driver.is_available and pending %}
          {% for r in pending[:5] %}
          <div style=\"padding:12px;background:rgba(255,255,255,.03);border-radius:12px;margin-bottom:10px\">
            <div><strong>Trip #{{ r.ride_id }}</strong></div>
            <div style=\"color:#94a3b8;margin-top:4px\">{{ r.pickup_name }} -> {{ r.dropoff_name }}</div>
            <div style=\"margin-top:4px\">{{ r.passenger_name }} | {{ r.passenger_phone }}</div>
            <form method=\"POST\" action=\"/driver/accept/{{ r.ride_id }}\" id=\"aForm{{ r.ride_id }}\"><button type=\"button\" class=\"driver-action\" onclick=\"showSheet('Accept Ride?','Accept the ride from {{ r.passenger_name }}?',()=>document.getElementById('aForm{{ r.ride_id }}').submit())\">ACCEPT RIDE</button></form>
          </div>
          {% endfor %}
        {% elif not driver.is_available %}
          <div style=\"color:#94a3b8\">You are currently assigned or offline, so new requests are paused.</div>
        {% else %}
          <div style=\"color:#94a3b8\">No requests right now.</div>
        {% endif %}
      </div>
    </div>
  </div>
</div>
<script>setTimeout(()=>location.reload(),15000);</script>
{% endblock %}
{% block bnav %}
<nav class=\"bnav\">
  <a class=\"bn on\" href=\"/driver\"><svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><path d=\"M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z\"/></svg>Dashboard</a>
  <a class=\"bn\" href=\"/driver/history\"><svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><path d=\"M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z\"/></svg>History</a>
  <a class=\"bn\" href=\"/driver/profile\"><svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><circle cx=\"12\" cy=\"8\" r=\"4\"/><path d=\"M4 20c0-4 3.6-7 8-7s8 3 8 7\"/></svg>Profile</a>
  <a class=\"bn\" href=\"/logout\"><svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><path d=\"M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4\"/><polyline points=\"16 17 21 12 16 7\"/><line x1=\"21\" y1=\"12\" x2=\"9\" y2=\"12\"/></svg>Logout</a>
</nav>
{% endblock %}
""", encoding="utf-8")

(root / "templates" / "admin" / "home.html").write_text("""{% extends \"base.html\" %}
{% block title %}Admin Dashboard{% endblock %}
{% block topbar %}{% endblock %}
{% block extra_css %}
<style>
.admin-shell{width:100vw;min-height:100vh;margin-left:calc(50% - 50vw);background:#0a1628;padding:28px 20px 110px;color:#fff}
.admin-wrap{max-width:1180px;margin:0 auto}
.admin-top{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:24px}
.admin-link{display:inline-flex;align-items:center;gap:8px;color:#67e8f9;text-decoration:none}
.admin-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px}
.admin-card{background:rgba(255,255,255,.03);padding:20px;border-radius:20px;border:1px solid rgba(255,255,255,.1);min-height:260px}
.admin-pill{padding:20px;background:#1e4d8c;border-radius:15px;margin-top:10px}
.notif-badge{display:inline-flex;align-items:center;justify-content:center;min-width:24px;height:24px;padding:0 8px;border-radius:999px;background:#f5c518;color:#111827;font-size:.85rem;font-weight:800;margin-left:10px}
.notif-item{padding:12px;background:rgba(255,255,255,.02);border-radius:12px;margin-top:10px;border-left:3px solid rgba(255,255,255,.18)}
.notif-item.success{border-left-color:#22c55e}
.notif-item.warning{border-left-color:#f59e0b}
.notif-item.danger{border-left-color:#ef4444}
.notif-item.info{border-left-color:#38bdf8}
.notif-time{color:#94a3b8;font-size:.82rem;margin-top:6px}
</style>
{% endblock %}
{% block content %}
<div class=\"admin-shell\">
  <div class=\"admin-wrap\">
    <div class=\"admin-top\">
      <h2 style=\"font-size:2rem;font-weight:800\">Admin Control Center{% if unread_notifications %}<span class=\"notif-badge\">{{ unread_notifications }}</span>{% endif %}</h2>
      <a href=\"/logout\" class=\"admin-link\">Exit</a>
    </div>
    <div class=\"admin-grid\">
      <div class=\"admin-card\">
        <h3>DIRECTORY</h3>
        <a href=\"/admin/drivers/new\" class=\"admin-link\">+ ENROLL STAFF</a>
        <div style=\"margin-top:16px;display:flex;flex-direction:column;gap:10px\">
          <a href=\"/admin/drivers\" style=\"color:#fff;text-decoration:none;padding:10px 0;border-bottom:1px solid #1e293b\">Drivers <small style=\"color:#94a3b8\">{{ drivers_total.c }} registered</small></a>
          <a href=\"/admin/rides\" style=\"color:#fff;text-decoration:none;padding:10px 0;border-bottom:1px solid #1e293b\">Rides <small style=\"color:#94a3b8\">{{ stats.total or 0 }} total</small></a>
          <a href=\"/admin/reports\" style=\"color:#fff;text-decoration:none;padding:10px 0;border-bottom:1px solid #1e293b\">Reports <small style=\"color:#94a3b8\">Analytics and exports</small></a>
          <a href=\"/admin/locations\" style=\"color:#fff;text-decoration:none;padding:10px 0\">Locations <small style=\"color:#94a3b8\">Manage stops</small></a>
        </div>
      </div>
      <div class=\"admin-card\">
        <h3>REVENUE</h3>
        <div class=\"admin-pill\">Total Fleet Income:<br><b style=\"font-size:1.6rem\">M {{ '%.2f'|format(stats.revenue or 0) }}</b></div>
        <div style=\"margin-top:16px;color:#94a3b8;line-height:1.8\">Completed rides: <strong style=\"color:#fff\">{{ stats.completed or 0 }}</strong><br>Pending / assigned rides: <strong style=\"color:#fff\">{{ stats.pending or 0 }}</strong><br>Drivers online: <strong style=\"color:#fff\">{{ drivers_online.c or 0 }}/{{ drivers_total.c }}</strong></div>
      </div>
      <div class=\"admin-card\">
        <h3>NOTIFICATIONS</h3>
        {% for n in notifications %}
          <div class=\"notif-item {{ n.level }}\">
            <div style=\"font-weight:700\">{{ n.title }}</div>
            <div style=\"margin-top:4px;color:#cbd5e1\">{{ n.message }}</div>
            <div class=\"notif-time\">{{ n.created_at.strftime('%Y-%m-%d %H:%M') if n.created_at else '' }}</div>
          </div>
        {% else %}
          <div style=\"color:#94a3b8;margin-top:12px\">No notifications yet.</div>
        {% endfor %}
      </div>
      <div class=\"admin-card\">
        <h3>SAFETY LOG (24H)</h3>
        <div style=\"margin-top:12px;display:flex;flex-direction:column;gap:10px\">
          {% for r in recent[:8] %}
          <div style=\"padding:10px;background:rgba(255,255,255,.02);border-radius:10px\">
            <b>Trip #{{ r.ride_id }}</b><br>
            {% if r.passenger_name %}<span style=\"color:#06b6d4\">{{ r.passenger_name }} ({{ r.passenger_phone }})</span>{% else %}<span style=\"color:#ef4444\">PII PURGED</span>{% endif %}
          </div>
          {% else %}
          <div style=\"color:#94a3b8\">No recent trips.</div>
          {% endfor %}
        </div>
      </div>
    </div>
  </div>
</div>
{% endblock %}
{% block bnav %}
<nav class=\"bnav\">
  <a class=\"bn on\" href=\"/admin\"><svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><path d=\"M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z\"/></svg>Home</a>
  <a class=\"bn\" href=\"/admin/rides\"><svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><circle cx=\"12\" cy=\"12\" r=\"10\"/><polyline points=\"12 6 12 12 16 14\"/></svg>Rides</a>
  <a class=\"bn\" href=\"/admin/drivers\"><svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><circle cx=\"12\" cy=\"8\" r=\"4\"/><path d=\"M4 20c0-4 3.6-7 8-7s8 3 8 7\"/></svg>Drivers</a>
  <a class=\"bn\" href=\"/admin/reports\"><svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><line x1=\"18\" y1=\"20\" x2=\"18\" y2=\"10\"/><line x1=\"12\" y1=\"20\" x2=\"12\" y2=\"4\"/><line x1=\"6\" y1=\"20\" x2=\"6\" y2=\"14\"/></svg>Reports</a>
  <a class=\"bn\" href=\"/logout\"><svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><path d=\"M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4\"/><polyline points=\"16 17 21 12 16 7\"/><line x1=\"21\" y1=\"12\" x2=\"9\" y2=\"12\"/></svg>Logout</a>
</nav>
{% endblock %}
""", encoding="utf-8")

(root / "templates" / "admin" / "rides.html").write_text("""{% extends \"base.html\" %}
{% block title %}All Rides{% endblock %}
{% block topbar %}<div class=\"topbar\"><a href=\"/admin\" class=\"t-back\">&larr; Back</a><span class=\"t-title\" style=\"text-align:center\">All Rides</span><span class=\"role-pill rp-admin\">Admin</span></div>{% endblock %}
{% block content %}
<div style=\"padding-bottom:3rem\">
  <form method=\"GET\" action=\"/admin/rides\">
    <div class=\"sbar\">
      <div class=\"iw\" style=\"flex:1\"><span class=\"ico\" style=\"font-size:13px\">&#128269;</span><input class=\"inp\" type=\"text\" name=\"q\" value=\"{{ search }}\" placeholder=\"Search passenger, driver, location...\" style=\"padding-left:34px;min-height:40px;font-size:13px;border-radius:8px\"></div>
      <button type=\"submit\" class=\"find\">Find</button>
    </div>
    <div class=\"fpanel\">
      <div class=\"fld-row\">
        <div class=\"fld\"><div class=\"lbl\" style=\"font-size:10px\">Status</div><div class=\"sw\"><select class=\"sel\" name=\"status\" style=\"min-height:36px;padding:7px 28px 7px 10px;font-size:12px\"><option value=\"\">All Statuses</option>{% for s in ['REQUESTED','ASSIGNED','ACCEPTED','IN_PROGRESS','COMPLETED','CANCELLED'] %}<option value=\"{{ s }}\" {% if status==s %}selected{% endif %}>{{ s.replace('_',' ') }}</option>{% endfor %}</select></div></div>
        <div class=\"fld\"><div class=\"lbl\" style=\"font-size:10px\">Location</div><div class=\"sw\"><select class=\"sel\" name=\"loc_id\" style=\"min-height:36px;padding:7px 28px 7px 10px;font-size:12px\"><option value=\"\">All Locations</option>{% for loc in locations %}<option value=\"{{ loc.location_id }}\" {% if loc_id|string==loc.location_id|string %}selected{% endif %}>{{ loc.location_name }}</option>{% endfor %}</select></div></div>
      </div>
      <div class=\"fld-row\">
        <div class=\"fld\"><div class=\"lbl\" style=\"font-size:10px\">From</div><input class=\"inp\" type=\"date\" name=\"date_from\" value=\"{{ date_from }}\" style=\"min-height:36px;padding:7px 10px;font-size:12px\"></div>
        <div class=\"fld\"><div class=\"lbl\" style=\"font-size:10px\">To</div><input class=\"inp\" type=\"date\" name=\"date_to\" value=\"{{ date_to }}\" style=\"min-height:36px;padding:7px 10px;font-size:12px\"></div>
      </div>
      <div class=\"ffoot\"><button type=\"submit\" class=\"btn btn-primary\">Apply Filters</button><a href=\"/admin/rides\" class=\"btn btn-ghost\">Clear</a></div>
    </div>
  </form>
  <div class=\"sh\">{{ rides|length }} ride(s)</div>
  {% for r in rides %}
  {% set status_class = {'REQUESTED':'c-req','ASSIGNED':'c-acc','ACCEPTED':'c-acc','IN_PROGRESS':'c-ip','COMPLETED':'c-done','CANCELLED':'c-cxl'}[r.ride_status] %}
  <div class=\"rc\" style=\"margin-bottom:8px\">
    <div class=\"rc-h\">
      <div class=\"rc-r\">
        <div class=\"rrow\"><div class=\"du\"></div>{{ r.pickup_name }}</div>
        <div class=\"vb\" style=\"margin:3px 0 3px 3px\"></div>
        <div class=\"rrow\"><div class=\"dd\"></div>{{ r.dropoff_name }}</div>
      </div>
      <span class=\"chip {{ status_class }}\" style=\"font-size:10px\">{{ r.ride_status.replace('_',' ') }}</span>
    </div>
    <div class=\"rc-b\">
      <div class=\"chips\" style=\"margin-bottom:{% if r.ride_status in ['REQUESTED','ASSIGNED','ACCEPTED','IN_PROGRESS'] %}8px{% else %}0{% endif %}\">
        <span class=\"chip c-muted mono\" style=\"font-size:10px\">#{{ r.ride_id }}</span>
        <span class=\"chip c-muted\">{{ r.passenger_name }}</span>
        <span class=\"chip c-muted mono\">{{ r.passenger_phone }}</span>
        {% if r.driver_name %}<span class=\"chip c-muted\">Driver {{ r.driver_name }}</span>{% else %}<span class=\"chip c-muted\">Awaiting driver</span>{% endif %}
        {% if r.fare_amount %}<span class=\"chip c-brand\">M {{ '%.2f'|format(r.fare_amount) }}</span>{% endif %}
        {% if r.payment_status %}<span class=\"chip c-muted\">Payment {{ r.payment_status }}</span>{% endif %}
      </div>
      {% if r.ride_status in ['REQUESTED','ASSIGNED','ACCEPTED','IN_PROGRESS'] %}
      <form method=\"POST\" action=\"/admin/rides/{{ r.ride_id }}/cancel\" id=\"cancel{{ r.ride_id }}\">
        <button type=\"button\" class=\"btn btn-ghost btn-sm\"
          onclick=\"showSheet('Cancel Ride #{{ r.ride_id }}?','This will cancel the ride immediately.',()=>document.getElementById('cancel{{ r.ride_id }}').submit())\">
          Cancel Ride
        </button>
      </form>
      {% endif %}
    </div>
  </div>
  {% else %}
  <div class=\"empty\"><div class=\"ei\">Ride</div><div>No rides found.</div></div>
  {% endfor %}
</div>
{% endblock %}
{% block bnav %}
<nav class=\"bnav\">
  <a class=\"bn\" href=\"/admin\"><svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><path d=\"M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z\"/></svg>Home</a>
  <a class=\"bn on\" href=\"/admin/rides\"><svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><circle cx=\"12\" cy=\"12\" r=\"10\"/><polyline points=\"12 6 12 12 16 14\"/></svg>Rides</a>
  <a class=\"bn\" href=\"/admin/drivers\"><svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><circle cx=\"12\" cy=\"8\" r=\"4\"/><path d=\"M4 20c0-4 3.6-7 8-7s8 3 8 7\"/></svg>Drivers</a>
  <a class=\"bn\" href=\"/admin/reports\"><svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><line x1=\"18\" y1=\"20\" x2=\"18\" y2=\"10\"/><line x1=\"12\" y1=\"20\" x2=\"12\" y2=\"4\"/><line x1=\"6\" y1=\"20\" x2=\"6\" y2=\"14\"/></svg>Reports</a>
  <a class=\"bn\" href=\"/logout\"><svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><path d=\"M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4\"/><polyline points=\"16 17 21 12 16 7\"/><line x1=\"21\" y1=\"12\" x2=\"9\" y2=\"12\"/></svg>Logout</a>
</nav>
{% endblock %}
""", encoding="utf-8")
