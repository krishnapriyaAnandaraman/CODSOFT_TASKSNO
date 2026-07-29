# Task 2: Cloud Data Deduplication System

Detects and blocks duplicate files (by **content**, not filename) before
they're stored in the cloud, using SHA-256 hashing + a small SQLite index.

## How the dedup logic works

1. When a file is uploaded, we read it in 8KB chunks and compute its
   **SHA-256 hash** — a unique fingerprint of the file's exact bytes.
2. We look up that hash in a local SQLite table (`files`). This table is
   our "cloud database" of what has already been stored (swap for
   DynamoDB/RDS in a real deployment — same logic).
3. **If the hash already exists** → we reject the upload immediately, tell
   the user which existing file it matches, and never touch S3.
4. **If the hash is new** → we upload to S3 and insert a new row recording
   the hash, S3 key, filename, size, and timestamp.

This means renaming a file and re-uploading it will still be caught as a
duplicate (because the content hash is identical), which is a stronger
test than comparing filenames.

## Setup (shares the same AWS account/bucket as Task 1)

You can reuse the exact same S3 bucket and IAM user you created for
Task 1 — no need to create new AWS resources.

```bash
cd task2_deduplication
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file (same as Task 1):
```
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_REGION=ap-south-1
S3_BUCKET_NAME=yourname-codsoft-filestorage
```

Run it:
```bash
python app.py
```
It runs on **port 5001** (so you can run Task 1 and Task 2 at the same
time on ports 5000/5001 if you want).

## How to demo the dedup behaviour for your video
1. Upload `report.pdf` — it succeeds and appears in the table.
2. Upload the exact same `report.pdf` again — you'll see the red
   "Duplicate detected!" message and it will NOT appear twice.
3. Rename a copy of the same file to `report_copy.pdf` and upload it —
   still rejected, because the **content** hash matches, proving this
   isn't just a filename check.
4. Upload a genuinely different file — it succeeds.

## Common errors & fixes
- **`sqlite3.OperationalError: database is locked`** — happens if you
  run two instances against the same `dedup.db` simultaneously; stick to
  one running process for the demo.
- **Duplicate not detected** — make sure the two files are byte-for-byte
  identical (e.g. re-saving a Word doc can change internal metadata and
  therefore its hash, even if the visible content looks the same).

## For your GitHub/LinkedIn submission
Same process as Task 1: separate folder inside your `CODSOFT_TASKSNO`
repo, `.gitignore` for `.env`/`venv`/`dedup.db`, and a short demo video
showing the duplicate-rejection flow described above.
