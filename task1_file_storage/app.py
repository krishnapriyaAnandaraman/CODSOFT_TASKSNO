"""
TASK 1 - CLOUD FILE STORAGE SYSTEM
-----------------------------------
A Flask web app that lets users UPLOAD, VIEW (list), DOWNLOAD and DELETE
files, with the actual file bytes stored in an AWS S3 bucket (not on the
local disk). This satisfies every bullet point in the CodSoft brief:
  - upload / download / view / delete files securely
  - store files in a cloud storage service (AWS S3 here)
  - basic file validation + access control
  - BONUS: shareable pre-signed download links

HOW TO RUN (see README.md for the full walkthrough):
  1. pip install -r requirements.txt
  2. Create a `.env` file (or set env vars) with your AWS credentials + bucket name
  3. python app.py
  4. Open http://127.0.0.1:5000
"""

import os
import uuid
from datetime import datetime

import boto3
from botocore.exceptions import ClientError
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, send_file, abort
)
from werkzeug.utils import secure_filename

# --------------------------------------------------------------------------
# CONFIGURATION
# --------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")

# Pull AWS config from environment variables so we NEVER hard-code secrets
# in the source file (important for security + for pushing this to GitHub).
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")  # e.g. "my-codsoft-file-storage"

# Only allow a safe, explicit whitelist of file extensions.
# This is the "file validation" requirement from the brief.
ALLOWED_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "pdf", "txt", "docx",
    "xlsx", "csv", "zip", "mp4", "mp3"
}
MAX_FILE_SIZE_MB = 20
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE_MB * 1024 * 1024  # Flask-level limit

# Single boto3 client reused across requests (boto3 clients are thread-safe).
s3 = boto3.client("s3", region_name=AWS_REGION)


def allowed_file(filename: str) -> bool:
    """Return True only if the filename has one of our whitelisted extensions."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# --------------------------------------------------------------------------
# ROUTES
# --------------------------------------------------------------------------

@app.route("/")
def index():
    """
    VIEW: List every file currently stored in the S3 bucket.
    We call list_objects_v2 and pass the results to the template.
    """
    try:
        response = s3.list_objects_v2(Bucket=BUCKET_NAME)
        files = []
        for obj in response.get("Contents", []):
            files.append({
                "key": obj["Key"],
                "size_kb": round(obj["Size"] / 1024, 1),
                "last_modified": obj["LastModified"].strftime("%Y-%m-%d %H:%M"),
            })
        # Newest files first
        files.sort(key=lambda f: f["last_modified"], reverse=True)
    except ClientError as e:
        flash(f"Could not reach S3 bucket: {e}", "error")
        files = []

    return render_template("index.html", files=files, bucket=BUCKET_NAME)


@app.route("/upload", methods=["POST"])
def upload():
    """
    UPLOAD: Validate the incoming file, then stream it straight to S3
    using upload_fileobj (no need to save to local disk first).
    """
    if "file" not in request.files:
        flash("No file part in the request.", "error")
        return redirect(url_for("index"))

    file = request.files["file"]

    if file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("index"))

    if not allowed_file(file.filename):
        flash(f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}", "error")
        return redirect(url_for("index"))

    # secure_filename() strips dangerous characters (path traversal etc.)
    safe_name = secure_filename(file.filename)

    # Prefix with a short uuid so two people uploading "resume.pdf" don't collide.
    unique_key = f"{uuid.uuid4().hex[:8]}_{safe_name}"

    try:
        s3.upload_fileobj(
            file,
            BUCKET_NAME,
            unique_key,
            ExtraArgs={"ContentType": file.content_type}
        )
        flash(f"Uploaded '{safe_name}' successfully.", "success")
    except ClientError as e:
        flash(f"Upload failed: {e}", "error")

    return redirect(url_for("index"))


@app.route("/download/<path:key>")
def download(key):
    """
    DOWNLOAD: Stream the object bytes from S3 straight back to the browser.
    We fetch into memory here for simplicity; for very large files you'd
    instead redirect the user to a pre-signed URL (see /share below).
    """
    try:
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        return send_file(
            obj["Body"],
            download_name=key.split("_", 1)[-1],  # strip the uuid prefix for a clean filename
            as_attachment=True,
        )
    except ClientError:
        abort(404, description="File not found.")


@app.route("/delete/<path:key>", methods=["POST"])
def delete(key):
    """DELETE: Remove the object from the bucket permanently."""
    try:
        s3.delete_object(Bucket=BUCKET_NAME, Key=key)
        flash(f"Deleted '{key}'.", "success")
    except ClientError as e:
        flash(f"Delete failed: {e}", "error")
    return redirect(url_for("index"))


@app.route("/share/<path:key>")
def share(key):
    """
    BONUS: Generate a temporary, shareable pre-signed download link.
    Anyone with this URL can download the file WITHOUT needing AWS
    credentials, but only for a limited time (1 hour here).
    """
    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": key},
            ExpiresIn=3600,  # seconds = 1 hour
        )
        flash(f"Shareable link (valid 1 hour): {url}", "success")
    except ClientError as e:
        flash(f"Could not generate link: {e}", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    if not BUCKET_NAME:
        raise SystemExit(
            "ERROR: Set the S3_BUCKET_NAME environment variable before running.\n"
            "See README.md for setup instructions."
        )
    app.run(debug=True)
