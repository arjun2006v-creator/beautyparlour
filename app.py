"""Beauty Parlour - Fullstack Flask app (dynamic, SQLite-backed, mobile-friendly)."""
import os
import sqlite3
from urllib.parse import quote
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DB location can be overridden with the DATABASE_URL env var
# (e.g. a persistent disk path on Render). Defaults to ./parlour.db
DB_PATH = os.environ.get("DATABASE_URL", os.path.join(BASE_DIR, "parlour.db"))

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "parlour-secret-change-me")


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
    if request.method == "POST":
        f = request.form
        conn.execute(
            "INSERT INTO bookings (name, phone, email, service, date, time, notes, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (f.get("name"), f.get("phone"), f.get("email"), f.get("service"),
             f.get("date"), f.get("time"), f.get("notes", ""), datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
        flash("✅ Your booking request was received! We will call you to confirm.", "success")
        return redirect(url_for("book"))
    services = conn.execute("SELECT name, price, duration FROM services ORDER BY category, name").fetchall()
    conn.close()
    return render_template("book.html", services=services)


# ---------- JSON API (dynamic frontend / mobile app ready) ----------
@app.route("/api/services")
def api_services():
    conn = get_db()
    rows = [dict(r) for r in conn.execute("SELECT * FROM services ORDER BY category, name")]
    conn.close()
    return jsonify(rows)


@app.route("/api/bookings", methods=["GET", "POST"])
def api_bookings():
    conn = get_db()
    if request.method == "POST":
        d = request.get_json(force=True) if request.is_json else request.form
        conn.execute(
            "INSERT INTO bookings (name, phone, email, service, date, time, notes, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (d.get("name"), d.get("phone"), d.get("email"), d.get("service"),
             d.get("date"), d.get("time"), d.get("notes", ""), datetime.now().isoformat()),
        )
        conn.commit()
        return jsonify({"message": "Booking created"}), 201
    rows = [dict(r) for r in conn.execute("SELECT * FROM bookings ORDER BY created_at DESC")]
    conn.close()
    return jsonify(rows)


@app.route("/api/bookings/<int:bid>/status", methods=["POST"])
def api_booking_status(bid):
    conn = get_db()
    conn.execute("UPDATE bookings SET status=? WHERE id=?", (request.form.get("status", "confirmed"), bid))
    conn.commit()
    conn.close()
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
        if request.form.get("password") == os.environ.get("ADMIN_PASSWORD", "admin123"):
            session["admin"] = True
        else:
            flash("Wrong password", "error")
    if not session.get("admin"):
        return render_template("admin_login.html")
    conn = get_db()
    bookings = conn.execute("SELECT * FROM bookings ORDER BY created_at DESC").fetchall()
    # Build a free WhatsApp click-to-chat link for each confirmed booking
    wa_links = {b["id"]: whatsapp_link(dict(b)) for b in bookings}
    wa_reject_links = {b["id"]: whatsapp_link(dict(b), kind="reject") for b in bookings}
    conn.close()
    return render_template("admin.html", bookings=bookings, wa_links=wa_links, wa_reject_links=wa_reject_links)


@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("home"))


init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
