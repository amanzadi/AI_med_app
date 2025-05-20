import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class ClinicDB:
    def __init__(self, db_path='clinic.db'):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables with proper doctor names and specialties"""
        c = self.conn.cursor()
        
        # Create tables
        c.execute('''CREATE TABLE IF NOT EXISTS patients
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      first_name TEXT,
                      last_name TEXT,
                      dob TEXT,
                      gender TEXT,
                      phone TEXT,
                      email TEXT UNIQUE,
                      insurance TEXT)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS doctors
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      first_name TEXT,
                      last_name TEXT,
                      specialty TEXT,
                      phone TEXT,
                      email TEXT,
                      office_location TEXT,
                      hourly_rate REAL)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS schedules
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      doctor_id INTEGER,
                      day_of_week TEXT,
                      start_time TEXT,
                      end_time TEXT,
                      is_available BOOLEAN,
                      FOREIGN KEY(doctor_id) REFERENCES doctors(id))''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS appointments
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      patient_id INTEGER,
                      doctor_id INTEGER,
                      appointment_time TEXT,
                      duration INTEGER,
                      status TEXT,
                      is_emergency BOOLEAN,
                      FOREIGN KEY(patient_id) REFERENCES patients(id),
                      FOREIGN KEY(doctor_id) REFERENCES doctors(id))''')
        
        # Insert sample data if tables are empty
        if not c.execute("SELECT COUNT(*) FROM patients").fetchone()[0]:
            self._insert_sample_data(c)
        
        self.conn.commit()
    
    def _insert_sample_data(self, cursor):
        """Insert sample data with realistic doctor names and specialties"""
        # Insert sample patients
        patients = [
            ("John", "Doe", "1985-05-15", "M", "555-0101", "john.doe@email.com", "BlueCross"),
            ("Jane", "Smith", "1990-08-22", "F", "555-0102", "jane.smith@email.com", "Aetna"),
            ("Robert", "Johnson", "1978-03-10", "M", "555-0103", "robert.j@email.com", "Medicare"),
            ("Emily", "Williams", "1995-11-30", "F", "555-0104", "emily.w@email.com", "UnitedHealth"),
            ("Michael", "Brown", "1982-07-18", "M", "555-0105", "michael.b@email.com", "Cigna"),
            ("Sarah", "Davis", "1988-09-25", "F", "555-0106", "sarah.d@email.com", "Kaiser"),
            ("David", "Miller", "1975-12-05", "M", "555-0107", "david.m@email.com", "Humana"),
            ("Jennifer", "Wilson", "1992-04-12", "F", "555-0108", "jennifer.w@email.com", "BlueShield"),
            ("Thomas", "Moore", "1980-06-20", "M", "555-0109", "thomas.m@email.com", "Medicaid"),
            ("Amir", "Amanzadi", "1995-06-20", "M", "555-0110", "amir.amanzadi@gmail.com", "Medicaid"),
            ("Lisa", "Taylor", "1987-01-15", "F", "555-0111", "lisa.t@email.com", "Aetna")
        ]
        cursor.executemany('''INSERT INTO patients 
                              (first_name, last_name, dob, gender, phone, email, insurance)
                              VALUES (?, ?, ?, ?, ?, ?, ?)''', patients)

        # Insert doctors with realistic names and specialties
        doctors = [
            ("William", "Harrison", "Cardiology", "555-0201", "cardiology@clinic.com", "Heart Center, Room 101", 220),
            ("Sophia", "Chen", "Dermatology", "555-0202", "dermatology@clinic.com", "Skin Clinic, Room 102", 190),
            ("James", "Wilson", "Pediatrics", "555-0203", "pediatrics@clinic.com", "Children's Wing, Room 103", 180),
            ("Olivia", "Rodriguez", "Neurology", "555-0204", "neurology@clinic.com", "Neuro Center, Room 104", 230),
            ("Michael", "Johnson", "Orthopedics", "555-0205", "orthopedics@clinic.com", "Bone & Joint Center, Room 105", 210),
            ("Emma", "Davis", "Ophthalmology", "555-0206", "ophthalmology@clinic.com", "Eye Center, Room 106", 195),
            ("Robert", "Martinez", "Gastroenterology", "555-0207", "gastro@clinic.com", "GI Center, Room 107", 200),
            ("Charlotte", "Brown", "Endocrinology", "555-0208", "endocrine@clinic.com", "Hormone Clinic, Room 108", 195),
            ("David", "Garcia", "Oncology", "555-0209", "oncology@clinic.com", "Cancer Center, Room 109", 240),
            ("Adam", "Smith", "General", "555-0210", "general@clinic.com", "General Clinic, Room 110", 240),
            ("Amelia", "Lee", "Psychiatry", "555-0211", "psychiatry@clinic.com", "Mental Health Wing, Room 111", 200)
        ]
        
        cursor.executemany('''INSERT INTO doctors 
                              (first_name, last_name, specialty, phone, email, office_location, hourly_rate)
                              VALUES (?, ?, ?, ?, ?, ?, ?)''', doctors)

        # Generate schedules for all doctors
        doctor_ids = [row[0] for row in cursor.execute("SELECT id FROM doctors").fetchall()]
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        time_slots = [("09:00", "12:00"), ("13:00", "17:00")]
        
        for doctor_id in doctor_ids:
            for day in days:
                for start, end in time_slots:
                    cursor.execute('''INSERT INTO schedules 
                                      (doctor_id, day_of_week, start_time, end_time, is_available)
                                      VALUES (?, ?, ?, ?, ?)''',
                                      (doctor_id, day, start, end, True))

    def get_specialties(self) -> List[str]:
        """Get a list of unique specialties available in the clinic"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT specialty FROM doctors")
        return [row[0] for row in cursor.fetchall()]

    def get_doctor_by_name(self, first_name: str, last_name: str) -> Optional[Dict]:
        """Get a doctor by their exact first and last name"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM doctors WHERE first_name=? AND last_name=?", (first_name, last_name))
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None

    def search_doctors_by_name(self, name_part: str) -> List[Dict]:
        """Search for doctors by partial match on first or last name"""
        cursor = self.conn.cursor()
        search_term = f"%{name_part}%"
        cursor.execute("SELECT * FROM doctors WHERE first_name LIKE ? OR last_name LIKE ?", (search_term, search_term))
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_patient_by_id(self, patient_id: int) -> Optional[Dict]:
        """Get patient by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE id=?", (patient_id,))
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None

    def get_doctor_by_id(self, doctor_id: int) -> Optional[Dict]:
        """Get doctor by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM doctors WHERE id=?", (doctor_id,))
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None

    def get_patient_by_email(self, email: str) -> Optional[Dict]:
        """Get patient by email address"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE email=?", (email,))
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None
    
    def get_doctors(self, specialty: Optional[str] = None) -> List[Dict]:
        """Get list of doctors, optionally filtered by specialty"""
        cursor = self.conn.cursor()
        if specialty:
            cursor.execute("SELECT * FROM doctors WHERE specialty=?", (specialty,))
        else:
            cursor.execute("SELECT * FROM doctors")
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_available_slots(self, doctor_id: int, date: str) -> List[str]:
        """Get available time slots for a doctor on a specific date, accounting for overlaps"""
        cursor = self.conn.cursor()
        target_day = datetime.strptime(date, "%Y-%m-%d").strftime("%A")
        cursor.execute('''SELECT start_time, end_time 
                          FROM schedules 
                          WHERE doctor_id=? AND day_of_week=? AND is_available=1''',
                          (doctor_id, target_day))
        working_hours = cursor.fetchall()
        
        if not working_hours:
            return []

        # Get all appointments for the doctor on that date
        cursor.execute('''SELECT appointment_time, duration 
                          FROM appointments 
                          WHERE doctor_id=? AND date(appointment_time)=?''',
                          (doctor_id, date))
        appointments = cursor.fetchall()
        appointment_intervals = []
        for apt_time, duration in appointments:
            start = datetime.fromisoformat(apt_time)
            end = start + timedelta(minutes=duration)
            appointment_intervals.append((start, end))

        available_slots = []
        for work_start, work_end in working_hours:
            work_start_dt = datetime.strptime(f"{date} {work_start}", "%Y-%m-%d %H:%M")
            work_end_dt = datetime.strptime(f"{date} {work_end}", "%Y-%m-%d %H:%M")
            current = work_start_dt
            while current + timedelta(minutes=30) <= work_end_dt:
                slot_end = current + timedelta(minutes=30)
                overlaps = any(
                    max(current, apt_start) < min(slot_end, apt_end)
                    for apt_start, apt_end in appointment_intervals
                )
                if not overlaps:
                    available_slots.append(current.strftime("%Y-%m-%d %H:%M"))
                current += timedelta(minutes=30)
        
        return available_slots
    
    def book_appointment(self, patient_id: int, doctor_id: int, 
                         appointment_time: str, duration: int = 30, 
                         is_emergency: bool = False) -> Dict:
        """Book an appointment with validation and return confirmation details"""
        cursor = self.conn.cursor()
        
        # Validate patient and doctor existence
        if not self.get_patient_by_id(patient_id):
            raise ValueError("Patient not found.")
        if not self.get_doctor_by_id(doctor_id):
            raise ValueError("Doctor not found.")

        # Check if appointment time is within working hours
        appointment_dt = datetime.fromisoformat(appointment_time)
        day_of_week = appointment_dt.strftime("%A")
        cursor.execute('''SELECT start_time, end_time 
                          FROM schedules 
                          WHERE doctor_id=? AND day_of_week=? AND is_available=1''',
                          (doctor_id, day_of_week))
        schedules = cursor.fetchall()
        is_within_schedule = False
        for start, end in schedules:
            schedule_start = datetime.strptime(f"{appointment_dt.date()} {start}", "%Y-%m-%d %H:%M")
            schedule_end = datetime.strptime(f"{appointment_dt.date()} {end}", "%Y-%m-%d %H:%M")
            if schedule_start <= appointment_dt < schedule_end:
                is_within_schedule = True
                break
        if not is_within_schedule:
            raise ValueError("The selected time is outside the doctor's working hours.")

        # Check for overlapping appointments
        start_dt = appointment_dt
        end_dt = start_dt + timedelta(minutes=duration)
        cursor.execute('''SELECT COUNT(*) FROM appointments
                          WHERE doctor_id=?
                          AND appointment_time < ?
                          AND datetime(appointment_time, '+' || duration || ' minutes') > ?''',
                          (doctor_id, end_dt.isoformat(), start_dt.isoformat()))
        if cursor.fetchone()[0] > 0:
            raise ValueError("The selected time slot is not available.")

        # Insert appointment
        cursor.execute('''INSERT INTO appointments 
                          (patient_id, doctor_id, appointment_time, duration, status, is_emergency)
                          VALUES (?, ?, ?, ?, ?, ?)''',
                          (patient_id, doctor_id, appointment_time, duration, "Confirmed", is_emergency))
        
        # Get details for confirmation
        patient = self.get_patient_by_id(patient_id)
        doctor = self.get_doctor_by_id(doctor_id)
        
        self.conn.commit()
        
        return {
            "confirmation_id": cursor.lastrowid,
            "patient": {
                "name": f"{patient['first_name']} {patient['last_name']}",
                "contact": patient['phone'],
                "email": patient['email']
            },
            "doctor": {
                "name": f"{doctor['first_name']} {doctor['last_name']}",
                "specialty": doctor['specialty'],
                "phone": doctor['phone'],
                "location": doctor['office_location']
            },
            "appointment_time": appointment_time,
            "duration": duration,
            "is_emergency": is_emergency
        }

    def close(self):
        """Close the database connection"""
        self.conn.close()

if __name__ == '__main__':
    db = ClinicDB()
    print("Database initialized and sample data inserted (if empty).")
