"""
TASK 2 - CLOUD DATA DEDUPLICATION SYSTEM
------------------------------------------
Goal: before saving a new upload to cloud storage, check whether an
IDENTICAL file (by content, not just filename) already exists. If it
does, reject/skip the upload and tell the user; if not, store it and
record its "fingerprint" so future uploads can be checked against it.

Design:
  - We hash each file's CONTENT with SHA-256. Two files with different
    names but identical bytes will produce the exact same hash -> this
    is how we detect true duplicates (not just same-filename).
  - A small SQLite table (`files` table) acts as our "index" of what's
    already in the cloud, storing: hash, s3_key, original filename,
    size, uploaded_at. SQLite here plays the role of a lightweight
    "cloud database" (in a real deployment you'd swap this for
    DynamoDB / RDS — the app logic doesn't change).
  - Only files whose hash is NOT already in the table are uploaded to S3.

This directly satisfies the brief:
  - detect & eliminate duplicate data records         -> hash lookup
  - validate new data against existing records         -> query before insert
  - prevent duplicate/invalid entries from being stored -> early return
  - save only verified, unique information              -> insert after check
  - optimize storage / keep DB consistent                -> one row per unique file
"""

import hashlib
import os
import sqlite3
import uuid
from datetime import datetime

import boto3
from botocore.exceptions import ClientError
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

# --------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
DB_PATH = os.environ.get("DB_PATH", "dedup.db")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "txt", "docx", "xlsx", "csv", "zip"}
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB cap

s3 = boto3.client("s3", region_name=AWS_REGION)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# --------------------------------------------------------------------------
# "CLOUD DATABASE" (SQLite standing in for DynamoDB/RDS)
# --------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the files index table if it doesn't already exist."""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_hash TEXT UNIQUE NOT NULL,   -- SHA-256 of the file contents
            s3_key TEXT NOT NULL,
            original_name TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            uploaded_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def compute_sha256(file_stream) -> str:
    """
    Read the uploaded file in chunks and compute its SHA-256 hash.
    We read in 8KB chunks so we never load a huge file entirely into
    memory just to hash it. We rewind the stream afterwards so it can
    still be uploaded to S3 in the caller.
    """
    hasher = hashlib.sha256()
    for chunk in iter(lambda: file_stream.read(8192), b""):
        hasher.update(chunk)
    file_stream.seek(0)  # rewind so upload_fileobj can read it again
    return hasher.hexdigest()


# --------------------------------------------------------------------------
# ROUTES
# --------------------------------------------------------------------------
@app.route("/")
def index():
    conn = get_db()
    rows = conn.execute("SELECT * FROM files ORDER BY uploaded_at DESC").fetchall()
    conn.close()
    return render_template("index.html", files=rows, bucket=BUCKET_NAME)


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files or request.files["file"].filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("index"))

    file = request.files["file"]

    if not allowed_file(file.filename):
        flash(f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}", "error")
        return redirect(url_for("index"))

    # STEP 1: fingerprint the file content
    file_hash = compute_sha256(file.stream)

    # STEP 2: check against existing records BEFORE touching S3
    conn = get_db()
    existing = conn.execute(
        "SELECT * FROM files WHERE file_hash = ?", (file_hash,)
    ).fetchone()

    if existing:
        # Duplicate detected -> reject, do NOT re-upload to S3, do NOT
        # insert a new DB row. This is the core "deduplication" behaviour.
        flash(
            f"Duplicate detected! This exact file already exists as "
            f"'{existing['original_name']}' (uploaded {existing['uploaded_at']}). "
            f"Upload skipped.",
            "error"
        )
        conn.close()
        return redirect(url_for("index"))

    # STEP 3: unique file -> upload to cloud storage
    safe_name = secure_filename(file.filename)
    unique_key = f"{uuid.uuid4().hex[:8]}_{safe_name}"

    try:
        s3.upload_fileobj(file, BUCKET_NAME, unique_key)
    except ClientError as e:
        flash(f"Upload to S3 failed: {e}", "error")
        conn.close()
        return redirect(url_for("index"))

    # STEP 4: record the fingerprint so future uploads can be checked
    conn.execute(
        "INSERT INTO files (file_hash, s3_key, original_name, size_bytes, uploaded_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (file_hash, unique_key, safe_name, file.content_length or 0,
         datetime.utcnow().isoformat(timespec="seconds"))
    )
    conn.commit()
    conn.close()

    flash(f"'{safe_name}' is unique — uploaded and indexed successfully.", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    if not BUCKET_NAME:
        raise SystemExit("ERROR: Set S3_BUCKET_NAME env var first. See README.md.")
    init_db()
    app.run(debug=True, port=5001)
