"""Patch script: replace the /book function body precisely by line range."""
path = r"f:\web projects\beauty parlour\app.py"
with open(path, encoding="utf-8") as fh:
    lines = fh.readlines()

start = None
end = None
for i, l in enumerate(lines):
    if l.startswith('@app.route("/book"'):
        start = i
    if start is not None and l.startswith('@app.route("/api/services"'):
        end = i
        break

if start is None or end is None:
    raise SystemExit("Could not locate /book function boundaries")

new_book = [
    '@app.route("/book", methods=["GET", "POST"])\n',
    'def book():\n',
    '    conn = get_db()\n',
    '    services = conn.execute("SELECT name, price, duration FROM services ORDER BY category, name").fetchall()\n',
    '    if request.method == "POST":\n',
    '        errors, cleaned = validate_booking(request.form)\n',
    '        if errors:\n',
    '            for e in errors:\n',
    '                flash(e, "error")\n',
    '        else:\n',
    '            conn.execute(\n',
    '                "INSERT INTO bookings (name, phone, email, service, date, time, notes, created_at) VALUES (?,?,?,?,?,?,?,?,)",\n',
    '                (cleaned["name"], cleaned["phone"], cleaned["email"], cleaned["service"],\n',
    '                 cleaned["date"], cleaned["time"], cleaned["notes"], datetime.now().isoformat()),\n',
    '            )\n',
    '            conn.commit()\n',
    '            conn.close()\n',
    '            flash("✅ Your booking request was received! We will call you to confirm.", "success")\n',
    '            return redirect(url_for("book"))\n',
    '    conn.close()\n',
    '    return render_template("book.html", services=services)\n',
]

lines[start:end] = new_book

with open(path, "w", encoding="utf-8", newline="") as fh:
    fh.writelines(lines)
print("PATCH OK")