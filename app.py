from flask import Flask, render_template, request, redirect, flash
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecretkey"
DB = 'crazy_hospital.db'

def get_db_connection():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS doctors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                specialization TEXT NOT NULL,
                beds_available INTEGER NOT NULL DEFAULT 0
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                phone TEXT,
                email TEXT,
                address TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER,
                doctor_id INTEGER,
                time_slot TEXT NOT NULL,
                FOREIGN KEY(patient_id) REFERENCES patients(id),
                FOREIGN KEY(doctor_id) REFERENCES doctors(id)
            )
        ''')

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/doctors', methods=['GET', 'POST'])
def doctors():
    with get_db_connection() as conn:
        if request.method == 'POST':
            name = request.form['name'].strip()
            specialization = request.form['specialization'].strip()
            beds = request.form['beds_available'].strip()
            if not name or not specialization or not beds.isdigit() or int(beds) < 0:
                flash("Please provide valid doctor info!", "error")
            else:
                conn.execute(
                    "INSERT INTO doctors (name, specialization, beds_available) VALUES (?, ?, ?)",
                    (name, specialization, int(beds))
                )
                flash("Doctor added successfully!", "success")
        doctors = conn.execute("SELECT * FROM doctors").fetchall()
    return render_template('doctors.html', doctors=doctors)

@app.route('/patients', methods=['GET', 'POST'])
def patients():
    with get_db_connection() as conn:
        if request.method == 'POST':
            name = request.form['name'].strip()
            age = request.form['age'].strip()
            phone = request.form.get('phone', '').strip()
            email = request.form.get('email', '').strip()
            address = request.form.get('address', '').strip()
            if not name or not age.isdigit() or int(age) <= 0:
                flash("Please provide valid patient info!", "error")
            else:
                conn.execute(
                    "INSERT INTO patients (name, age, phone, email, address) VALUES (?, ?, ?, ?, ?)",
                    (name, int(age), phone, email, address)
                )
                flash("Patient added successfully!", "success")
        patients = conn.execute("SELECT * FROM patients").fetchall()
    return render_template('patients.html', patients=patients)

@app.route('/book', methods=['GET', 'POST'])
def book():
    with get_db_connection() as conn:
        if request.method == 'POST':
            patient_id = request.form.get('existing_patient')
            name = request.form.get('name', '').strip()
            age = request.form.get('age', '').strip()
            phone = request.form.get('phone', '').strip()
            email = request.form.get('email', '').strip()
            address = request.form.get('address', '').strip()
            doctor_id = request.form.get('doctor_id')
            time_slot = request.form.get('time_slot', '').strip()

            if not doctor_id or not time_slot:
                flash("Please select doctor and time slot!", "error")
                return redirect('/book')

            if not patient_id:
                if not name or not age.isdigit() or int(age) <= 0:
                    flash("Please provide valid new patient info!", "error")
                    return redirect('/book')
                age = int(age)
                cursor = conn.execute(
                    "INSERT INTO patients (name, age, phone, email, address) VALUES (?, ?, ?, ?, ?)",
                    (name, age, phone, email, address)
                )
                patient_id = cursor.lastrowid
            else:
                patient_id = int(patient_id)

            beds = conn.execute(
                "SELECT beds_available FROM doctors WHERE id = ?", (doctor_id,)
            ).fetchone()

            if beds is None or beds['beds_available'] <= 0:
                flash("No beds available for selected doctor!", "error")
                return redirect('/book')

            conn.execute(
                "INSERT INTO bookings (patient_id, doctor_id, time_slot) VALUES (?, ?, ?)",
                (patient_id, doctor_id, time_slot)
            )
            conn.execute(
                "UPDATE doctors SET beds_available = beds_available - 1 WHERE id = ?",
                (doctor_id,)
            )
            flash("Booking successful!", "success")
            return redirect('/book')

        doctors = conn.execute("SELECT * FROM doctors").fetchall()
        patients = conn.execute("SELECT id, name FROM patients").fetchall()
        bookings = conn.execute('''
            SELECT bookings.id, patients.name AS patient_name, doctors.name AS doctor_name, bookings.time_slot
            FROM bookings
            JOIN patients ON bookings.patient_id = patients.id
            JOIN doctors ON bookings.doctor_id = doctors.id
            ORDER BY bookings.id DESC
        ''').fetchall()

    return render_template('book.html', doctors=doctors, patients=patients, bookings=bookings)

@app.route('/delete_booking/<int:id>')
def delete_booking(id):
    with get_db_connection() as conn:
        booking = conn.execute(
            "SELECT doctor_id FROM bookings WHERE id = ?", (id,)
        ).fetchone()
        if booking:
            doctor_id = booking['doctor_id']
            conn.execute("DELETE FROM bookings WHERE id = ?", (id,))
            conn.execute(
                "UPDATE doctors SET beds_available = beds_available + 1 WHERE id = ?",
                (doctor_id,)
            )
            flash("Booking deleted & bed restored!", "success")
        else:
            flash("Booking not found!", "error")
    return redirect('/book')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
