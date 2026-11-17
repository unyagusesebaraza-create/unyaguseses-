import sqlite3
from datetime import date, datetime

DATABASE = "school_management.db"


def connect():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def initialize_database():
    with connect() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admission_number TEXT NOT NULL UNIQUE,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                date_of_birth TEXT,
                gender TEXT,
                class_name TEXT NOT NULL,
                guardian_name TEXT,
                guardian_phone TEXT,
                address TEXT,
                admission_date TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                amount REAL NOT NULL CHECK (amount > 0),
                payment_date TEXT NOT NULL,
                term TEXT NOT NULL,
                method TEXT,
                reference TEXT,
                FOREIGN KEY (student_id) REFERENCES students(id)
            );

            CREATE TABLE IF NOT EXISTS exams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                exam_name TEXT NOT NULL,
                subject TEXT NOT NULL,
                score REAL NOT NULL,
                max_score REAL NOT NULL,
                exam_date TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(id)
            );
        """)


def ask_text(prompt, required=False, default=None):
    while True:
        suffix = f" [{default}]" if default is not None else ""
        value = input(f"{prompt}{suffix}: ").strip()

        if not value and default is not None:
            return default
        if value or not required:
            return value
        print("This field is required.")


def ask_date(prompt, default_today=False):
    default = date.today().isoformat() if default_today else None

    while True:
        value = ask_text(prompt, required=True, default=default)
        try:
            return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
        except ValueError:
            print("Enter a date in YYYY-MM-DD format.")


def ask_number(prompt, minimum=None, maximum=None):
    while True:
        try:
            value = float(input(f"{prompt}: ").strip())
            if minimum is not None and value < minimum:
                print(f"Enter a value of at least {minimum}.")
                continue
            if maximum is not None and value > maximum:
                print(f"Enter a value no greater than {maximum}.")
                continue
            return value
        except ValueError:
            print("Enter a valid number.")


def find_student():
    admission_number = ask_text("Student admission number", required=True)

    with connect() as db:
        student = db.execute(
            "SELECT * FROM students WHERE admission_number = ?",
            (admission_number,),
        ).fetchone()

    if student is None:
        print("No student found with that admission number.")
    return student


def add_student():
    print("\n--- Add student admission ---")
    admission_number = ask_text("Admission number", required=True)
    first_name = ask_text("First name", required=True)
    last_name = ask_text("Last name", required=True)
    date_of_birth = ask_date("Date of birth") if ask_text(
        "Enter date of birth? (y/n)", required=True
    ).lower() == "y" else None
    gender = ask_text("Gender")
    class_name = ask_text("Class/grade", required=True)
    guardian_name = ask_text("Guardian name")
    guardian_phone = ask_text("Guardian phone")
    address = ask_text("Address")
    admission_date = ask_date("Admission date", default_today=True)

    try:
        with connect() as db:
            db.execute("""
                INSERT INTO students (
                    admission_number, first_name, last_name, date_of_birth,
                    gender, class_name, guardian_name, guardian_phone,
                    address, admission_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                admission_number, first_name, last_name, date_of_birth,
                gender, class_name, guardian_name, guardian_phone,
                address, admission_date,
            ))
        print("Student admission record saved.")
    except sqlite3.IntegrityError:
        print("That admission number is already in use.")


def list_students():
    print("\n--- Students ---")
    with connect() as db:
        students = db.execute("""
            SELECT admission_number, first_name, last_name, class_name,
                   guardian_phone
            FROM students
            ORDER BY last_name, first_name
        """).fetchall()

    if not students:
        print("No students have been added yet.")
        return

    for student in students:
        print(
            f"{student['admission_number']} | "
            f"{student['first_name']} {student['last_name']} | "
            f"Class: {student['class_name']} | "
            f"Guardian phone: {student['guardian_phone'] or '-'}"
        )


def record_payment():
    print("\n--- Record fee payment ---")
    student = find_student()
    if student is None:
        return

    amount = ask_number("Amount", minimum=0.01)
    payment_date = ask_date("Payment date", default_today=True)
    term = ask_text("Term", required=True)
    method = ask_text("Payment method (cash, bank, mobile, etc.)")
    reference = ask_text("Receipt/reference number")

    with connect() as db:
        db.execute("""
            INSERT INTO payments (
                student_id, amount, payment_date, term, method, reference
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            student["id"], amount, payment_date, term, method, reference,
        ))

    print("Payment recorded.")


def show_payment_history():
    print("\n--- Student fee payment history ---")
    student = find_student()
    if student is None:
        return

    with connect() as db:
        payments = db.execute("""
            SELECT amount, payment_date, term, method, reference
            FROM payments
            WHERE student_id = ?
            ORDER BY payment_date DESC, id DESC
        """, (student["id"],)).fetchall()

    print(f"\n{student['first_name']} {student['last_name']} "
          f"({student['admission_number']})")

    if not payments:
        print("No payments recorded.")
        return

    total = 0
    for payment in payments:
        total += payment["amount"]
        print(
            f"{payment['payment_date']} | {payment['term']} | "
            f"Amount: {payment['amount']:.2f} | "
            f"Method: {payment['method'] or '-'} | "
            f"Reference: {payment['reference'] or '-'}"
        )
    print(f"Total payments recorded: {total:.2f}")


def record_exam_result():
    print("\n--- Record exam result ---")
    student = find_student()
    if student is None:
        return

    exam_name = ask_text("Exam name", required=True)
    subject = ask_text("Subject", required=True)
    max_score = ask_number("Maximum score", minimum=0.01)
    score = ask_number("Student score", minimum=0, maximum=max_score)
    exam_date = ask_date("Exam date", default_today=True)

    with connect() as db:
        db.execute("""
            INSERT INTO exams (
                student_id, exam_name, subject, score, max_score, exam_date
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            student["id"], exam_name, subject, score, max_score, exam_date,
        ))

    print("Exam result recorded.")


def show_exam_results():
    print("\n--- Student exam results ---")
    student = find_student()
    if student is None:
        return

    with connect() as db:
        results = db.execute("""
            SELECT exam_name, subject, score, max_score, exam_date
            FROM exams
            WHERE student_id = ?
            ORDER BY exam_date DESC, exam_name, subject
        """, (student["id"],)).fetchall()

    print(f"\n{student['first_name']} {student['last_name']} "
          f"({student['admission_number']})")

    if not results:
        print("No exam results recorded.")
        return

    for result in results:
        percentage = result["score"] / result["max_score"] * 100
        print(
            f"{result['exam_date']} | {result['exam_name']} | "
            f"{result['subject']} | {result['score']:g}/"
            f"{result['max_score']:g} ({percentage:.1f}%)"
        )


def main():
    initialize_database()

    actions = {
        "1": add_student,
        "2": list_students,
        "3": record_payment,
        "4": show_payment_history,
        "5": record_exam_result,
        "6": show_exam_results,
    }

    while True:
        print("""
=== School Management System ===
1. Add student admission
2. List students
3. Record fee payment
4. View student payment history
5. Record exam result
6. View student exam results
0. Exit
""")
        choice = input("Choose an option: ").strip()

        if choice == "0":
            print("Goodbye.")
            break

        action = actions.get(choice)
        if action:
            try:
                action()
            except sqlite3.Error as error:
                print(f"Database error: {error}")
        else:
            print("Choose one of the listed options.")


if __name__ == "__main__":
    main()
