import os
import string
import random

from flask import Flask, request, jsonify, redirect, render_template
import psycopg2
import psycopg2.extras

app = Flask(__name__)

DB_HOST = os.environ.get("DB_HOST", "db")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "urlshortener")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080")
CODE_LENGTH = int(os.environ.get("CODE_LENGTH", 6))


def get_db():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS urls (
            id SERIAL PRIMARY KEY,
            code VARCHAR(16) UNIQUE NOT NULL,
            original_url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            clicks INTEGER DEFAULT 0
        );
        """
    )
    conn.commit()
    cur.close()
    conn.close()


def generate_code(length=CODE_LENGTH):
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


@app.route("/health")
def health():
    return jsonify(status="ok"), 200


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/shorten", methods=["POST"])
def shorten():
    data = request.get_json(silent=True) or {}
    original_url = data.get("url", "").strip()

    if not original_url:
        return jsonify(error="url is required"), 400
    if not (original_url.startswith("http://") or original_url.startswith("https://")):
        original_url = "https://" + original_url

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    code = generate_code()
    while True:
        cur.execute("SELECT 1 FROM urls WHERE code = %s", (code,))
        if cur.fetchone() is None:
            break
        code = generate_code()

    cur.execute(
        "INSERT INTO urls (code, original_url) VALUES (%s, %s) RETURNING code, original_url, created_at",
        (code, original_url),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return jsonify(
        short_url=f"{BASE_URL}/{row['code']}",
        code=row["code"],
        original_url=row["original_url"],
    ), 201


@app.route("/<code>")
def redirect_to_original(code):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT original_url FROM urls WHERE code = %s", (code,))
    row = cur.fetchone()

    if row is None:
        cur.close()
        conn.close()
        return jsonify(error="short URL not found"), 404

    cur.execute("UPDATE urls SET clicks = clicks + 1 WHERE code = %s", (code,))
    conn.commit()
    cur.close()
    conn.close()

    return redirect(row["original_url"], code=302)


@app.route("/api/stats/<code>")
def stats(code):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT code, original_url, created_at, clicks FROM urls WHERE code = %s",
        (code,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if row is None:
        return jsonify(error="short URL not found"), 404

    return jsonify(row), 200


def init_db_with_retry(attempts=10, delay=3):
    import time
    for i in range(attempts):
        try:
            init_db()
            return
        except psycopg2.OperationalError:
            time.sleep(delay)
    raise RuntimeError("could not connect to database after retries")


init_db_with_retry()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
