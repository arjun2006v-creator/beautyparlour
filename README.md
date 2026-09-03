# 🌸 Glow & Grace — Beauty Parlour Fullstack Web App

A dynamic, mobile-friendly fullstack application built with **Python (Flask)** and **SQLite** — no paid services required.

## ✨ Features
- Dynamic pages rendered from a database (services, gallery, testimonials)
- Online appointment booking (form + JSON API)
- Admin dashboard to view/confirm bookings (password protected)
- Beautiful background-image hero and card images
- Fully responsive — works on mobile phones (hamburger menu, fluid grids)
- REST APIs (`/api/services`, `/api/bookings`) ready for a future mobile app

## 🚀 Run locally (free)
```powershell
cd "f:\web projects\beauty parlour"
pip install -r requirements.txt
python app.py
```
Open http://localhost:5000

- Booking page: `/book`
- Admin dashboard: `/admin` (password: `admin123` — change via `ADMIN_PASSWORD` env var)
- JSON API: `/api/services`, `/api/bookings`

## 🖼️ Images
Place your own photos in `static/img/` with these names (any JPG works):
`hero-bg.jpg`, `booking-bg.jpg`, and per-service/gallery images listed in the DB seed (`makeup1.jpg`, `hair1.jpg`, `g1.jpg`, …).
Fallback pastel colors show until you add them, so the site never looks broken.

## ☁️ Deploy free (Render.com)
1. Push this folder to a GitHub repo.
2. On https://render.com → **New → Web Service** → connect the repo.
3. Settings: Build command `pip install -r requirements.txt`, Start command `gunicorn app:app --bind 0.0.0.0:$PORT` (or it reads the included `Procfile`).
4. Add env var `SECRET_KEY` (anything random) and `ADMIN_PASSWORD`.
5. Deploy — you get a free `https://yourapp.onrender.com` URL. Free alternatives: Railway, PythonAnywhere, Fly.io.

> Note: SQLite resets on free-tier redeploys. For persistent free storage, point Render's disk at `parlour.db` or later upgrade to Postgres.
