"""Beauty Parlour - Fullstack Flask app (dynamic, SQLite-backed, mobile-friendly)."""
import os
import secrets
import sqlite3
from urllib.parse import quote
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# DB location can be overridden with DATABASE_URL (a local path, e.g. a persistent disk
# mount on Render). If it looks like a remote database URL (postgres/mysql), ignore it so
# sqlite doesn't try to open a network URL. Defaults to ./parlour.db
_db_url = os.environ.get("DATABASE_URL")
if _db_url and not _db_url.startswith(("postgres://", "postgresql://", "mysql://", "mariadb://")):
    DB_PATH = _db_url
else:
    DB_PATH = os.path.join(BASE_DIR, "parlour.db")

# Debug mode: FLASK_DEBUG=1 locally. Render (production) leaves it unset.
DEBUG = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")

# Never crash on missing secrets — fall back so the app always boots.
# Best practice for production: set SECRET_KEY and ADMIN_PASSWORD in Render → Environment.
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    print("WARNING: SECRET_KEY env var not set — using a temporary random key. "
          "Sessions will reset on restart. Add SECRET_KEY in Render → Environment.")

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    ADMIN_PASSWORD = "arjun123"
    print("WARNING: ADMIN_PASSWORD env var not set — using default 'arjun123'. "
          "Add ADMIN_PASSWORD in Render → Environment to change it.")

app = Flask(__name__)
app.secret_key = SECRET_KEY


# ---------- Database helpers ----------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            duration TEXT,
            description TEXT,
            image TEXT
        );
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            service TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            notes TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS gallery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            image TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS testimonials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            rating INTEGER DEFAULT 5,
            message TEXT NOT NULL
        );
        """
    )
    # Seed sample data only if empty
    if conn.execute("SELECT COUNT(*) c FROM services").fetchone()["c"] == 0:
        conn.executescript(
            """
            INSERT INTO services (name, category, price, duration, description, image) VALUES
            ('Bridal Makeup', 'Makeup', 8000, '2-3 hrs', 'Complete bridal look with premium HD makeup, hairstyle and draping.', 'makeup1.jpg'),
            ('Party Makeup', 'Makeup', 2500, '1-1.5 hrs', 'Glamorous party look with long-lasting makeup.', 'makeup2.jpg'),
            ('Haircut & Styling', 'Hair', 700, '45 min', 'Trendy haircut with wash, blow-dry and styling.', 'hair1.jpg'),
            ('Hair Spa', 'Hair', 1200, '1 hr', 'Deep conditioning and relaxing scalp massage.', 'hair2.jpg'),
            ('Facial (Gold)', 'Skin', 1500, '1 hr', 'Radiance-boosting gold facial for glowing skin.', 'facial1.jpg'),
            ('Cleanup & Tan Removal', 'Skin', 900, '45 min', 'Gentle exfoliation, tan removal and hydration.', 'facial2.jpg'),
            ('Manicure & Pedicure', 'Nails', 800, '1 hr', 'Nail shaping, cuticle care and relaxing hand-foot massage.', 'nails1.jpg'),
            ('Gel Nail Art', 'Nails', 1500, '1-1.5 hrs', 'Long-lasting gel polish with custom nail art.', 'nails2.jpg'),
            ('Threading & Waxing', 'Grooming', 400, '30 min', 'Precise eyebrow threading and full-arm waxing.', 'groom1.jpg'),
            ('Mehndi (Bridal)', 'Grooming', 3000, '2-4 hrs', 'Intricate bridal mehndi designs for hands and feet.', 'mehndi1.jpg');
            """
        )
    if conn.execute("SELECT COUNT(*) c FROM testimonials").fetchone()["c"] == 0:
        conn.executescript(
            """
            INSERT INTO testimonials (name, rating, message) VALUES
            ('Priya S.', 5, 'Best bridal makeup in town! Everyone loved my look on my wedding day.'),
            ('Anjali K.', 5, 'Relaxing hair spa and super friendly staff. My salon forever now.'),
            ('Meera R.', 4, 'Great facials and clean, hygienic place. Booking online was easy.');
            """
        )
    if conn.execute("SELECT COUNT(*) c FROM gallery").fetchone()["c"] == 0:
        conn.executescript(
            """
            INSERT INTO gallery (title, image) VALUES
            ('Bridal Look', 'g1.jpg'), ('Party Glam', 'g2.jpg'), ('Hairstyle', 'g3.jpg'),
            ('Nail Art', 'g4.jpg'), ('Mehndi', 'g5.jpg'), ('Glow Facial', 'g6.jpg');
            """
        )
    conn.commit()
    conn.close()


def validate_booking(d):
    """Returns (errors: list, cleaned: dict) — rejects empty fields, bad dates/times and bad phone numbers."""
    errors = []
    name = (d.get("name") or "").strip()
    phone = (d.get("phone") or "").strip()
    phone_digits = "".join(ch for ch in phone if ch.isdigit())
    email = (d.get("email") or "").strip()
    service = (d.get("service") or "").strip()
    bdate = (d.get("date") or "").strip()
    btime = (d.get("time") or "").strip()
    notes = (d.get("notes") or "").strip()

    if not name:
        errors.append("Please enter your name.")
    if not (10 <= len(phone_digits) <= 15):
        errors.append("Please enter a valid phone number (10–15 digits).")
    if not service:
        errors.append("Please choose a service.")
    if email and "@" not in email:
        errors.append("Please enter a valid email address.")
    if bdate:
        try:
            parsed = datetime.strptime(bdate, "%Y-%m-%d")
            if parsed.date() < date.today():
                errors.append("Please pick a date that is not in the past.")
        except ValueError:
            errors.append("Please pick a valid date.")
    else:
        errors.append("Please pick a date.")
    if btime:
        try:
            datetime.strptime(btime, "%H:%M")
        except ValueError:
            errors.append("Please pick a valid time.")
    else:
        errors.append("Please pick a time.")

    return errors, {
        "name": name, "phone": phone, "email": email, "service": service,
        "date": bdate, "time": btime, "notes": notes,
    }


# ---------- Routes (pages) ----------
@app.route("/")
def home():
    conn = get_db()
    services = conn.execute("SELECT * FROM services ORDER BY category, name").fetchall()
    testimonials = conn.execute("SELECT * FROM testimonials").fetchall()
    gallery = conn.execute("SELECT * FROM gallery").fetchall()
    conn.close()
    return render_template("index.html", services=services, testimonials=testimonials, gallery=gallery)


@app.route("/book", methods=["GET", "POST"])
def book():
    conn = get_db()
    services = conn.execute("SELECT name, price, duration FROM services ORDER BY category, name").fetchall()
    if request.method == "POST":
        errors, cleaned = validate_booking(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
        else:
            conn.execute(
                "INSERT INTO bookings (name, phone, email, service, date, time, notes, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (cleaned["name"], cleaned["phone"], cleaned["email"], cleaned["service"],
                 cleaned["date"], cleaned["time"], cleaned["notes"], datetime.now().isoformat()),
            )
            conn.commit()
            conn.close()
            flash("✅ Your booking request was received! We will call you to confirm.", "success")
            return redirect(url_for("book"))
    conn.close()
    return render_template("book.html", services=services)
@app.route("/api/services")
def api_services():
    conn = get_db()
    rows = [dict(r) for r in conn.execute("SELECT * FROM services ORDER BY category, name")]
    conn.close()
    return jsonify(rows)


@app.route("/api/bookings", methods=["GET", "POST"])
def api_bookings():
    if request.method == "POST":
        d = request.get_json(force=True) if request.is_json else request.form
        errors, cleaned = validate_booking(d)
        if errors:
            return jsonify({"errors": errors}), 400
        conn = get_db()
        conn.execute(
            "INSERT INTO bookings (name, phone, email, service, date, time, notes, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (cleaned["name"], cleaned["phone"], cleaned["email"], cleaned["service"],
             cleaned["date"], cleaned["time"], cleaned["notes"], datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
        return jsonify({"message": "Booking created"}), 201
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_db()
    rows = [dict(r) for r in conn.execute("SELECT * FROM bookings ORDER BY created_at DESC")]
    conn.close()
    return jsonify(rows)


@app.route("/api/bookings/<int:bid>/status", methods=["POST"])
def api_booking_status(bid):
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401
    status = request.form.get("status", "confirmed")
    if status not in ("confirmed", "rejected", "done", "canceled"):
        return jsonify({"error": "Invalid status"}), 400
    conn = get_db()
    conn.execute("UPDATE bookings SET status=? WHERE id=?", (status, bid,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))


@app.route("/api/bookings/<int:bid>/delete", methods=["POST"])
def delete_booking(bid):
    """Permanently remove a booking (e.g. canceled/rejected ones) — admin only."""
    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_db()
    booking = conn.execute("SELECT name FROM bookings WHERE id=?", (bid,)).fetchone()
    conn.execute("DELETE FROM bookings WHERE id=?", (bid,))
    conn.commit()
    conn.close()
    if booking:
        flash(f"🗑️ Booking #{bid} ({booking['name']}) was removed.", "success")
    else:
        flash(f"Booking #{bid} not found.", "error")
    return redirect(url_for("admin"))


@app.route("/admin/clear-canceled", methods=["POST"])
def clear_canceled():
    """Remove all canceled & rejected bookings in one click — admin only."""
    if not session.get("admin"):
        return redirect(url_for("admin"))
    conn = get_db()
    cur = conn.execute("DELETE FROM bookings WHERE status IN ('canceled','rejected')")
    removed = cur.rowcount
    conn.commit()
    conn.close()
    flash(f"🗑️ Removed {removed} canceled/rejected booking(s).", "success")
    return redirect(url_for("admin"))


# ---------- WhatsApp helper (100% free, no API needed) ----------
def _wa_number(phone):
    phone = "".join(ch for ch in str(phone) if ch.isdigit())
    if len(phone) == 10:  # assume Indian number if no country code
        phone = "91" + phone
    return phone


def build_whatsapp_message(booking):
    """Build the confirmation message text for a booking."""
    return (
        f"Hi {booking['name']}! \u2728 Your booking at Beauty Parlour is CONFIRMED.\n\n"
        f"\U0001F484 Service: {booking['service']}\n"
        f"\U0001F4C5 Date: {booking['date']}\n"
        f"\u23F0 Time: {booking['time']}\n\n"
        f"We look forward to seeing you!"
    )


def build_reject_message(booking):
    """Message asking the customer to pick a new time (workload)."""
    return (
        f"Hi {booking['name']}, sorry! \U0001F615 Due to high workload at Beauty Parlour, "
        f"we cannot take your booking for {booking['service']} on {booking['date']} at {booking['time']}.\n\n"
        f"Could you please reply with another date/time that suits you? "
        f"We will do our best to accommodate you! \U0001F64F"
    )


def whatsapp_link(booking, kind="confirm"):
    """Free WhatsApp click-to-chat link with the message pre-typed.
    No API, no account, no cost. Admin just clicks and presses Enter."""
    text = build_whatsapp_message(booking) if kind == "confirm" else build_reject_message(booking)
    return "https://wa.me/" + _wa_number(booking["phone"]) + "?text=" + quote(text)


# ---------- Admin (simple password) ----------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
        else:
            flash("Wrong password", "error")
    if not session.get("admin"):
        return render_template("admin_login.html")
    conn = get_db()
    bookings = conn.execute("SELECT * FROM bookings ORDER BY created_at DESC").fetchall()
    counts = {row["status"]: row["c"] for row in conn.execute(
        "SELECT status, COUNT(*) c FROM bookings GROUP BY status")}
    # Build a free WhatsApp click-to-chat link for each confirmed booking
    wa_links = {b["id"]: whatsapp_link(dict(b)) for b in bookings}
    wa_reject_links = {b["id"]: whatsapp_link(dict(b), kind="reject") for b in bookings}
    conn.close()
    return render_template("admin.html", bookings=bookings, counts=counts,
                           wa_links=wa_links, wa_reject_links=wa_reject_links)


@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("home"))


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=DEBUG)
