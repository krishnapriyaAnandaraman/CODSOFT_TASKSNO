# Task 1: Cloud File Storage System

A Flask app that lets a user **upload, view, download, and delete** files
stored in **AWS S3**, plus a bonus **shareable pre-signed link** feature.

## What each requirement maps to

| Brief requirement | Where it's implemented |
|---|---|
| Upload/download/view/delete files securely | `/upload`, `/download/<key>`, `/`, `/delete/<key>` routes in `app.py` |
| Store files in a cloud storage service | `boto3` S3 client (`s3.upload_fileobj`, `s3.get_object`, `s3.delete_object`) |
| File validation & basic access permissions | `allowed_file()` extension whitelist, `MAX_CONTENT_LENGTH` size cap, `secure_filename()` |
| Bonus: shareable download links | `/share/<key>` uses `generate_presigned_url` |

## Step-by-step setup

### 1. Create an AWS account (skip if you have one)
Go to https://aws.amazon.com and sign up. AWS has a free tier that covers
S3 for a small student project.

### 2. Create an S3 bucket
1. AWS Console → search "S3" → **Create bucket**.
2. Bucket name must be globally unique, e.g. `yourname-codsoft-filestorage`.
3. Region: pick one close to you (e.g. `ap-south-1` for India).
4. Leave "Block all public access" **checked** (we use pre-signed URLs
   instead of making the bucket public — this is the secure approach).
5. Click **Create bucket**.

### 3. Create an IAM user with programmatic access
1. AWS Console → **IAM** → **Users** → **Create user**.
2. Name it e.g. `codsoft-app-user`.
3. Attach policy **AmazonS3FullAccess** (for a class project this is fine;
   in production you'd scope it to just your bucket).
4. After creating the user, go to **Security credentials** → **Create
   access key** → choose "Application running outside AWS" → copy the
   **Access Key ID** and **Secret Access Key**. You will NOT see the
   secret again, so save it now.

### 4. Configure credentials locally
Create a file named `.env` in this folder (this file is already listed
in a typical `.gitignore` — **never commit it to GitHub**):

```
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_REGION=ap-south-1
S3_BUCKET_NAME=yourname-codsoft-filestorage
FLASK_SECRET_KEY=any-random-string
```

Then at the very top of `app.py`, add these two lines (or just run
`pip install python-dotenv` and add them yourself) so the `.env` file is
loaded automatically:
```python
from dotenv import load_dotenv
load_dotenv()
```

Alternatively, on Mac/Linux you can just export the variables in your
terminal before running:
```bash
export AWS_ACCESS_KEY_ID=your-access-key-id
export AWS_SECRET_ACCESS_KEY=your-secret-access-key
export S3_BUCKET_NAME=yourname-codsoft-filestorage
```

### 5. Install dependencies & run
```bash
cd task1_file_storage
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open **http://127.0.0.1:5000** in your browser. Upload a file, then try
Download, Share Link, and Delete.

### 6. Test it actually reaches S3
Go back to the AWS Console → your bucket → **Objects** tab. You should
see the file appear there after you upload from the app.

## Common errors & fixes
- **`NoCredentialsError`** → your `.env` isn't being loaded / env vars
  not set. Confirm `AWS_ACCESS_KEY_ID` is actually set in the shell
  running `python app.py`.
- **`AccessDenied`** → the IAM user's policy doesn't allow S3 actions on
  this bucket — recheck step 3.
- **Bucket name error on creation** → bucket names are globally unique
  across ALL AWS accounts; add your name/random digits.

## For your GitHub submission
- Rename the repo `CODSOFT_TASKSNO` per the internship instructions.
- Add a `.gitignore` containing `.env`, `venv/`, `__pycache__/` so you
  never leak your AWS keys.
- In your README, briefly describe the app and include 2–3 screenshots
  of the running app (upload success, S3 console showing the file).

## For your LinkedIn demo video
Screen-record: (1) uploading a file, (2) refreshing the AWS S3 console
to show it landed in the bucket, (3) downloading it back, (4) using the
share link in an incognito window, (5) deleting it. 60–90 seconds is
plenty. Tag CodSoft and add `#codsoft #internship #cloudcomputing`.
