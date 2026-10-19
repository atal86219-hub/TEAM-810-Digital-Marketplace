from flask import Flask, jsonify, request, send_from_directory
from pathlib import Path
import sqlite3
import os
import re
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("TEAM810_DB_PATH", ROOT / "data" / "team810.sqlite3"))
app = Flask(__name__, static_folder=None)
ALLOWED_CATEGORIES = {"design", "web", "translation", "other"}

def connect_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                contact TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)
init_db()

@app.get("/")
def home():
    return send_from_directory(ROOT, "index.html")

@app.get("/downloads/<path:filename>")
def downloads(filename):
    if filename not in {"shop.html", "portfolio.html", "business.html"}:
        return jsonify({"error": "Not found"}), 404
    return send_from_directory(ROOT / "downloads", filename, as_attachment=False)

@app.get("/api/health")
def health():
    return jsonify({"ok": True, "service": "TEAM 810 Digital Marketplace"})

@app.get("/api/services")
def list_services():
    with connect_db() as con:
        rows = con.execute(
            "SELECT id, name, category, description, contact, created_at FROM services ORDER BY id DESC LIMIT 200"
        ).fetchall()
    return jsonify([dict(row) for row in rows])

@app.post("/api/services")
def create_service():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    category = str(payload.get("category", "other")).strip()
    description = str(payload.get("description", "")).strip()
    contact = str(payload.get("contact", "")).strip()

    if not name or len(name) > 60:
        return jsonify({"error": "Name is required and must be 60 characters or fewer."}), 400
    if category not in ALLOWED_CATEGORIES:
        return jsonify({"error": "Invalid category."}), 400
    if not description or len(description) > 240:
        return jsonify({"error": "Description is required and must be 240 characters or fewer."}), 400
    if len(contact) > 100:
        return jsonify({"error": "Contact must be 100 characters or fewer."}), 400
    # Contact is displayed as text in the frontend, not inserted as HTML.
    created_at = datetime.now(timezone.utc).isoformat()
    with connect_db() as con:
        cur = con.execute(
            "INSERT INTO services (name, category, description, contact, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, category, description, contact, created_at),
        )
        item = con.execute(
            "SELECT id, name, category, description, contact, created_at FROM services WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
    return jsonify(dict(item)), 201

@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "Not found"}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
