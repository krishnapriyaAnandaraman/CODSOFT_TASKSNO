# Task 3: Cloud-Based Bus Ticket Reservation System

Search routes, view a live seat map, book a seat, and manage bookings —
built to run locally and then be **deployed to the cloud** so it can
handle real traffic (the "scalable cloud infrastructure" requirement).

## What each requirement maps to

| Brief requirement | Where it's implemented |
|---|---|
| Search routes, reserve seats, manage bookings | `/`, `/bus/<id>`, `/book/<seat_id>`, `/my-bookings`, `/cancel/<ref>` |
| Store booking info securely in a cloud database | SQLite locally → swap for AWS RDS in production (see below) |
| Support high traffic / scalable infra | Atomic `UPDATE ... WHERE is_booked=0` prevents double-booking under concurrency; deploy on Elastic Beanstalk/EC2/Render behind a load balancer |
| Deploy and test | Step-by-step deployment section below |

## Run it locally first
```bash
cd task3_bus_reservation
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Open **http://127.0.0.1:5002**. The database is auto-created and seeded
with 3 demo routes (Chennai↔Bangalore, Chennai↔Puducherry) on first run.

## Try the concurrency-safety yourself
Open the same seat's booking dialog in two browser tabs and submit both
almost simultaneously — only one will succeed; the second gets "seat was
just booked by someone else." This is what the atomic `UPDATE` guards
against, and it's worth mentioning explicitly in your demo video since
it's the part graders/interviewers usually ask about.

## Deploying to the cloud (pick ONE — all are free-tier friendly)

### Option A: Render.com (simplest, recommended for a student demo)
1. Push this folder to your GitHub repo.
2. On https://render.com → **New Web Service** → connect your repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app` (add `gunicorn` to `requirements.txt` first)
5. Deploy — Render gives you a public URL, e.g. `https://your-app.onrender.com`.

### Option B: AWS Elastic Beanstalk
1. Install the EB CLI: `pip install awsebcli`
2. `eb init -p python-3.11 codsoft-bus-app`
3. `eb create codsoft-bus-env`
4. `eb open` — this launches an EC2 instance, load balancer, and
   auto-scaling group behind the scenes, which is literally the
   "scalable cloud infrastructure" the brief asks for.

### Swapping SQLite for a real cloud database (optional but impressive)
For production, replace the `sqlite3` calls with **AWS RDS
(PostgreSQL)** + the `psycopg2` library, or **DynamoDB** + `boto3`. The
route logic (search → book → cancel) stays identical; only `get_db()`
and the SQL syntax change. Mentioning this swap in your video/README
shows you understand why SQLite is a stand-in, not the final answer.

## For your GitHub submission
Include this README, a `.gitignore` (`venv/`, `*.db`, `__pycache__/`),
and 2–3 screenshots: search results, seat map, and a confirmed booking.

## For your LinkedIn demo video
Show: (1) searching Chennai→Bangalore, (2) picking a seat and booking
it, (3) the seat turning grey afterward, (4) My Bookings page, (5)
canceling a booking and seeing the seat free up again. If you deployed
it, show the live public URL working instead of localhost — that's a
strong signal you actually completed the "deploy and test" bullet.
