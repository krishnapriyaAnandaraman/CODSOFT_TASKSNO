"""
TASK 3 - CLOUD-BASED BUS TICKET RESERVATION SYSTEM
------------------------------------------------------
A Flask app where users can:
  - search bus routes (source, destination, date)
  - view seat availability and reserve a seat
  - manage/cancel their bookings

Storage: SQLite in this template (see README.md for how to swap it for
a managed cloud DB like AWS RDS / DynamoDB with almost no code changes —
that's the "deploy to a scalable cloud infrastructure" requirement).

The trickiest requirement here is "booking information stored securely
and the system handling concurrent users without double-booking a seat".
We solve double-booking with an ATOMIC UPDATE: instead of "check seat is
free, THEN book it" (two steps -> race condition), we do a single SQL
statement: `UPDATE seats SET is_booked=1 WHERE id=? AND is_booked=0` and
check `rowcount`. If two users click "Book" on the same seat at the same
instant, only one UPDATE will actually change a row — the other gets
rowcount=0 and is told the seat's gone. That's what makes this safe
under real traffic, not just single-user demos.
"""

import sqlite3
import uuid
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"
DB_PATH = "bus_reservation.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables (if needed) and seed a few demo buses/seats."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS buses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operator TEXT NOT NULL,
            source TEXT NOT NULL,
            destination TEXT NOT NULL,
            journey_date TEXT NOT NULL,     -- 'YYYY-MM-DD'
            departure_time TEXT NOT NULL,   -- 'HH:MM'
            fare INTEGER NOT NULL,
            total_seats INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS seats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_id INTEGER NOT NULL REFERENCES buses(id),
            seat_number TEXT NOT NULL,
            is_booked INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_ref TEXT UNIQUE NOT NULL,
            seat_id INTEGER NOT NULL REFERENCES seats(id),
            bus_id INTEGER NOT NULL REFERENCES buses(id),
            passenger_name TEXT NOT NULL,
            passenger_email TEXT NOT NULL,
            booked_at TEXT NOT NULL
        );
    """)
    conn.commit()

    # Seed demo data only if the buses table is empty, so re-running
    # the app doesn't duplicate routes every time.
    count = conn.execute("SELECT COUNT(*) FROM buses").fetchone()[0]
    if count == 0:
        demo_buses = [
            ("GreenLine Travels", "Chennai", "Bangalore", "2026-08-05", "22:00", 650, 20),
            ("SilverStar Bus",    "Chennai", "Bangalore", "2026-08-05", "23:30", 550, 15),
            ("MetroLink",         "Chennai", "Puducherry", "2026-08-05", "07:00", 200, 25),
        ]
        for operator, src, dest, date, time, fare, seats in demo_buses:
            cur = conn.execute(
                "INSERT INTO buses (operator, source, destination, journey_date, "
                "departure_time, fare, total_seats) VALUES (?,?,?,?,?,?,?)",
                (operator, src, dest, date, time, fare, seats)
            )
            bus_id = cur.lastrowid
            for i in range(1, seats + 1):
                seat_label = f"{(i - 1) // 4 + 1}{'ABCD'[(i - 1) % 4]}"  # e.g. 1A, 1B, 2A...
                conn.execute(
                    "INSERT INTO seats (bus_id, seat_number, is_booked) VALUES (?,?,0)",
                    (bus_id, seat_label)
                )
        conn.commit()
    conn.close()


# --------------------------------------------------------------------------
# ROUTES
# --------------------------------------------------------------------------
@app.route("/")
def index():
    """Search form + results. Query params: source, destination, date."""
    conn = get_db()
    source = request.args.get("source", "").strip()
    destination = request.args.get("destination", "").strip()
    date = request.args.get("date", "").strip()

    query = "SELECT * FROM buses WHERE 1=1"
    params = []
    if source:
        query += " AND source LIKE ?"
        params.append(f"%{source}%")
    if destination:
        query += " AND destination LIKE ?"
        params.append(f"%{destination}%")
    if date:
        query += " AND journey_date = ?"
        params.append(date)

    buses = conn.execute(query, params).fetchall()

    # Attach a live "seats available" count to each bus for display.
    results = []
    for bus in buses:
        available = conn.execute(
            "SELECT COUNT(*) FROM seats WHERE bus_id = ? AND is_booked = 0", (bus["id"],)
        ).fetchone()[0]
        results.append({**dict(bus), "available_seats": available})
    conn.close()

    return render_template("index.html", buses=results, source=source,
                            destination=destination, date=date)


@app.route("/bus/<int:bus_id>")
def seat_map(bus_id):
    """Show the seat map for one bus so the user can pick a free seat."""
    conn = get_db()
    bus = conn.execute("SELECT * FROM buses WHERE id = ?", (bus_id,)).fetchone()
    if not bus:
        conn.close()
        flash("Bus not found.", "error")
        return redirect(url_for("index"))

    seats = conn.execute(
        "SELECT * FROM seats WHERE bus_id = ? ORDER BY id", (bus_id,)
    ).fetchall()
    conn.close()
    return render_template("seats.html", bus=bus, seats=seats)


@app.route("/book/<int:seat_id>", methods=["POST"])
def book(seat_id):
    """
    Reserve a seat. Uses a single atomic UPDATE to prevent double-booking
    when two users try to grab the same seat at the same time.
    """
    passenger_name = request.form.get("passenger_name", "").strip()
    passenger_email = request.form.get("passenger_email", "").strip()

    if not passenger_name or not passenger_email:
        flash("Name and email are required.", "error")
        return redirect(request.referrer or url_for("index"))

    conn = get_db()
    seat = conn.execute("SELECT * FROM seats WHERE id = ?", (seat_id,)).fetchone()
    if not seat:
        conn.close()
        flash("Seat not found.", "error")
        return redirect(url_for("index"))

    # ---- THE ATOMIC, CONCURRENCY-SAFE STEP ----
    # This single statement both checks AND claims the seat. If another
    # request already booked it a millisecond earlier, rowcount will be 0.
    cur = conn.execute(
        "UPDATE seats SET is_booked = 1 WHERE id = ? AND is_booked = 0", (seat_id,)
    )
    conn.commit()

    if cur.rowcount == 0:
        conn.close()
        flash("Sorry, that seat was just booked by someone else. Please pick another.", "error")
        return redirect(url_for("seat_map", bus_id=seat["bus_id"]))

    booking_ref = uuid.uuid4().hex[:10].upper()
    conn.execute(
        "INSERT INTO bookings (booking_ref, seat_id, bus_id, passenger_name, "
        "passenger_email, booked_at) VALUES (?,?,?,?,?,?)",
        (booking_ref, seat_id, seat["bus_id"], passenger_name, passenger_email,
         datetime.utcnow().isoformat(timespec="seconds"))
    )
    conn.commit()
    conn.close()

    flash(f"Booked! Your reference is {booking_ref} — seat {seat['seat_number']}.", "success")
    session.setdefault("my_refs", []).append(booking_ref)
    session.modified = True
    return redirect(url_for("my_bookings"))


@app.route("/my-bookings")
def my_bookings():
    """Show bookings made in this browser session (looked up by ref)."""
    refs = session.get("my_refs", [])
    conn = get_db()
    bookings = []
    if refs:
        placeholders = ",".join("?" * len(refs))
        bookings = conn.execute(
            f"""SELECT bookings.*, seats.seat_number, buses.operator, buses.source,
                       buses.destination, buses.journey_date, buses.departure_time, buses.fare
                FROM bookings
                JOIN seats ON bookings.seat_id = seats.id
                JOIN buses ON bookings.bus_id = buses.id
                WHERE booking_ref IN ({placeholders})
                ORDER BY bookings.booked_at DESC""",
            refs
        ).fetchall()
    conn.close()
    return render_template("my_bookings.html", bookings=bookings)


@app.route("/cancel/<booking_ref>", methods=["POST"])
def cancel(booking_ref):
    """Cancel a booking: free up the seat again and remove the booking row."""
    conn = get_db()
    booking = conn.execute(
        "SELECT * FROM bookings WHERE booking_ref = ?", (booking_ref,)
    ).fetchone()
    if booking:
        conn.execute("UPDATE seats SET is_booked = 0 WHERE id = ?", (booking["seat_id"],))
        conn.execute("DELETE FROM bookings WHERE booking_ref = ?", (booking_ref,))
        conn.commit()
        flash("Booking cancelled and seat released.", "success")
    conn.close()
    return redirect(url_for("my_bookings"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5002)
