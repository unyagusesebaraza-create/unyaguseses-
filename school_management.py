"""School management desktop app (Tkinter + SQLite).

First run: create an administrator account. Data is stored locally in
school_management.db. CSV export uses the standard library; Excel export
requires the optional openpyxl package (python -m pip install openpyxl).
"""

import csv
import hashlib
import hmac
import os
import sqlite3
import tkinter as tk
from datetime import date, datetime
from tkinter import filedialog, messagebox, simpledialog, ttk

DATABASE = "school_management.db"
PASSWORD_ITERATIONS = 310_000


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
                max_score REAL NOT NULL CHECK (max_score > 0),
                exam_date TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(id)
            );
            CREATE TABLE IF NOT EXISTS administrators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                salt BLOB NOT NULL,
                password_hash BLOB NOT NULL,
                created_at TEXT NOT NULL
            );
        """)


def password_digest(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )


def date_is_valid(value):
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


class LoginDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.username = None
        self.title("School Management System — Admin login")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", parent.destroy)
        self.transient(parent)
        self.grab_set()
        self.container = ttk.Frame(self, padding=20)
        self.container.grid(sticky="nsew")
        self.refresh()
        self.update_idletasks()
        self.geometry(f"+{parent.winfo_rootx() + 100}+{parent.winfo_rooty() + 80}")

    def refresh(self):
        for child in self.container.winfo_children():
            child.destroy()
        with connect() as db:
            count = db.execute("SELECT COUNT(*) FROM administrators").fetchone()[0]
        if count == 0:
            self.show_setup()
        else:
            self.show_login()

    def show_setup(self):
        ttk.Label(self.container, text="Create the first administrator",
                  font=("TkDefaultFont", 12, "bold")).grid(
                      row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        ttk.Label(self.container, text="Username").grid(row=1, column=0, sticky="w", pady=4)
        username = ttk.Entry(self.container, width=30)
        username.grid(row=1, column=1, pady=4)
        ttk.Label(self.container, text="Password (at least 10 characters)").grid(
            row=2, column=0, sticky="w", pady=4)
        password = ttk.Entry(self.container, width=30, show="•")
        password.grid(row=2, column=1, pady=4)
        ttk.Label(self.container, text="Confirm password").grid(
            row=3, column=0, sticky="w", pady=4)
        confirm = ttk.Entry(self.container, width=30, show="•")
        confirm.grid(row=3, column=1, pady=4)
        ttk.Button(self.container, text="Create administrator",
                   command=lambda: self.create_admin(username.get(), password.get(),
                                                     confirm.get())).grid(
                       row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        password.bind("<Return>", lambda _event: self.create_admin(
            username.get(), password.get(), confirm.get()))
        username.focus_set()

    def create_admin(self, username, password, confirmation):
        username = username.strip()
        if not username:
            messagebox.showerror("Invalid username", "Enter a username.", parent=self)
            return
        if len(password) < 10:
            messagebox.showerror("Weak password", "Use at least 10 characters.", parent=self)
            return
        if password != confirmation:
            messagebox.showerror("Password mismatch", "Passwords do not match.", parent=self)
            return
        salt = os.urandom(16)
        with connect() as db:
            db.execute("INSERT INTO administrators (username, salt, password_hash, created_at) "
                       "VALUES (?, ?, ?, ?)",
                       (username, salt, password_digest(password, salt),
                        datetime.now().isoformat(timespec="seconds")))
        self.username = username
        self.destroy()

    def show_login(self):
        ttk.Label(self.container, text="Administrator login",
                  font=("TkDefaultFont", 12, "bold")).grid(
                      row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        ttk.Label(self.container, text="Username").grid(row=1, column=0, sticky="w", pady=4)
        username = ttk.Entry(self.container, width=30)
        username.grid(row=1, column=1, pady=4)
        ttk.Label(self.container, text="Password").grid(row=2, column=0, sticky="w", pady=4)
        password = ttk.Entry(self.container, width=30, show="•")
        password.grid(row=2, column=1, pady=4)
        ttk.Button(self.container, text="Log in",
                   command=lambda: self.authenticate(username.get(), password.get())).grid(
                       row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        password.bind("<Return>", lambda _event: self.authenticate(
            username.get(), password.get()))
        username.focus_set()

    def authenticate(self, username, password):
        with connect() as db:
            admin = db.execute("SELECT * FROM administrators WHERE username = ?",
                               (username.strip(),)).fetchone()
        if admin and hmac.compare_digest(
                password_digest(password, admin["salt"]), admin["password_hash"]):
            self.username = admin["username"]
            self.destroy()
        else:
            messagebox.showerror("Login failed", "Invalid username or password.", parent=self)


class SchoolManagementApp:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()
        self.root.title("School Management System")
        self.root.minsize(900, 560)
        login = LoginDialog(root)
        root.wait_window(login)
        if not login.username:
            root.destroy()
            return
        self.username = login.username
        self.root.deiconify()
        self.create_menu()
        self.create_ui()
        self.refresh_all()

    def create_menu(self):
        menu = tk.Menu(self.root)
        account = tk.Menu(menu, tearoff=False)
        account.add_command(label="Change password…", command=self.change_password)
        account.add_separator()
        account.add_command(label="Log out", command=self.logout)
        account.add_command(label="Exit", command=self.root.destroy)
        menu.add_cascade(label="Account", menu=account)
        self.root.config(menu=menu)

    def create_ui(self):
        header = ttk.Frame(self.root, padding=(12, 10))
        header.pack(fill="x")
        ttk.Label(header, text="School Management System",
                  font=("TkDefaultFont", 16, "bold")).pack(side="left")
        ttk.Label(header, text=f"Administrator: {self.username}").pack(side="right")
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.dashboard_tab = ttk.Frame(self.notebook, padding=12)
        self.students_tab = ttk.Frame(self.notebook, padding=10)
        self.payments_tab = ttk.Frame(self.notebook, padding=10)
        self.exams_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.dashboard_tab, text="Dashboard")
        self.notebook.add(self.students_tab, text="Students")
        self.notebook.add(self.payments_tab, text="Fee payments")
        self.notebook.add(self.exams_tab, text="Exams")
        self.build_dashboard()
        self.build_data_tab(self.students_tab, "students")
        self.build_data_tab(self.payments_tab, "payments")
        self.build_data_tab(self.exams_tab, "exams")

    def build_dashboard(self):
        ttk.Label(self.dashboard_tab, text="Overview",
                  font=("TkDefaultFont", 14, "bold")).pack(anchor="w")
        self.stats = ttk.Frame(self.dashboard_tab)
        self.stats.pack(fill="x", pady=12)
        self.summary_labels = {}
        for index, key in enumerate(("Students", "Fees collected", "Exam results", "Average score")):
            card = ttk.LabelFrame(self.stats, text=key, padding=12)
            card.grid(row=0, column=index, sticky="nsew", padx=(0, 8))
            label = ttk.Label(card, text="—", font=("TkDefaultFont", 16, "bold"))
            label.pack()
            self.summary_labels[key] = label
            self.stats.columnconfigure(index, weight=1)
        ttk.Label(self.dashboard_tab, text="Fee collections by term",
                  font=("TkDefaultFont", 11, "bold")).pack(anchor="w", pady=(12, 4))
        self.term_tree = self.make_tree(self.dashboard_tab,
                                        ("term", "payments", "total"),
                                        ("Term", "Payment count", "Amount collected"))
        self.term_tree.pack(fill="both", expand=True)
        buttons = ttk.Frame(self.dashboard_tab)
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="Refresh dashboard", command=self.refresh_dashboard).pack(side="left")
        ttk.Button(buttons, text="Export dashboard CSV", command=self.export_csv).pack(side="right")

    @staticmethod
    def make_tree(parent, columns, headings):
        frame = ttk.Frame(parent)
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=14)
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        for col, heading in zip(columns, headings):
            tree.heading(col, text=heading)
            tree.column(col, width=135, minwidth=90, anchor="w")
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        tree._frame = frame
        return tree

    def build_data_tab(self, tab, kind):
        configs = {
            "students": (("admission", "name", "class", "guardian", "phone", "admitted"),
                         ("Admission #", "Student", "Class", "Guardian", "Phone", "Admission date")),
            "payments": (("date", "admission", "student", "term", "amount", "method", "reference"),
                         ("Date", "Admission #", "Student", "Term", "Amount", "Method", "Reference")),
            "exams": (("date", "admission", "student", "exam", "subject", "score", "max", "percent"),
                      ("Date", "Admission #", "Student", "Exam", "Subject", "Score", "Out of", "Percent")),
        }
        columns, headings = configs[kind]
        tree = self.make_tree(tab, columns, headings)
        tree._frame.pack(fill="both", expand=True)
        setattr(self, f"{kind}_tree", tree)
        controls = ttk.Frame(tab)
        controls.pack(fill="x", pady=(10, 0))
        if kind == "students":
            ttk.Button(controls, text="Admit student…", command=self.add_student).pack(side="left", padx=(0, 6))
        elif kind == "payments":
            ttk.Button(controls, text="Record payment…", command=self.add_payment).pack(side="left", padx=(0, 6))
        else:
            ttk.Button(controls, text="Record exam result…", command=self.add_exam).pack(side="left", padx=(0, 6))
        ttk.Button(controls, text="Refresh", command=lambda: self.refresh_tab(kind)).pack(side="left")
        ttk.Button(controls, text="Export CSV", command=self.export_csv).pack(side="right", padx=(6, 0))
        ttk.Button(controls, text="Export Excel…", command=self.export_excel).pack(side="right")

    def get_data(self, kind):
        queries = {
            "students": ("SELECT admission_number, first_name || ' ' || last_name AS name, "
                         "class_name, guardian_name, guardian_phone, admission_date "
                         "FROM students ORDER BY last_name, first_name", ()),
            "payments": ("SELECT p.payment_date, s.admission_number, "
                         "s.first_name || ' ' || s.last_name AS student, p.term, p.amount, "
                         "p.method, p.reference FROM payments p JOIN students s ON s.id=p.student_id "
                         "ORDER BY p.payment_date DESC, p.id DESC", ()),
            "exams": ("SELECT e.exam_date, s.admission_number, "
                      "s.first_name || ' ' || s.last_name AS student, e.exam_name, e.subject, "
                      "e.score, e.max_score, ROUND(e.score * 100.0 / e.max_score, 1) AS percent "
                      "FROM exams e JOIN students s ON s.id=e.student_id "
                      "ORDER BY e.exam_date DESC, e.id DESC", ()),
        }
        with connect() as db:
            rows = db.execute(*queries[kind]).fetchall()
        return [tuple(row) for row in rows]

    def refresh_tab(self, kind):
        tree = getattr(self, f"{kind}_tree")
        tree.delete(*tree.get_children())
        for row in self.get_data(kind):
            tree.insert("", "end", values=tuple("" if value is None else value for value in row))

    def refresh_all(self):
        self.refresh_dashboard()
        for kind in ("students", "payments", "exams"):
            self.refresh_tab(kind)

    def refresh_dashboard(self):
        with connect() as db:
            students = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
            fees = db.execute("SELECT COALESCE(SUM(amount), 0) FROM payments").fetchone()[0]
            exams = db.execute("SELECT COUNT(*) FROM exams").fetchone()[0]
            avg = db.execute("SELECT AVG(score * 100.0 / max_score) FROM exams WHERE max_score > 0").fetchone()[0]
            by_term = db.execute("SELECT term, COUNT(*), SUM(amount) FROM payments "
                                 "GROUP BY term ORDER BY term").fetchall()
        self.summary_labels["Students"].config(text=str(students))
        self.summary_labels["Fees collected"].config(text=f"{fees:,.2f}")
        self.summary_labels["Exam results"].config(text=str(exams))
        self.summary_labels["Average score"].config(text=f"{avg:.1f}%" if avg is not None else "—")
        self.term_tree.delete(*self.term_tree.get_children())
        for row in by_term:
            self.term_tree.insert("", "end", values=(row[0], row[1], f"{row[2]:,.2f}"))

    def form_dialog(self, title, fields, on_submit):
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        form = ttk.Frame(dialog, padding=14)
        form.pack(fill="both", expand=True)
        entries = {}
        for index, (key, label, default) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=index, column=0, sticky="w", padx=(0, 12), pady=5)
            entry = ttk.Entry(form, width=34)
            entry.grid(row=index, column=1, sticky="ew", pady=5)
            if default is not None:
                entry.insert(0, default)
            entries[key] = entry
        form.columnconfigure(1, weight=1)
        def submit():
            values = {key: entry.get().strip() for key, entry in entries.items()}
            if on_submit(values):
                dialog.destroy()
        buttons = ttk.Frame(form)
        buttons.grid(row=len(fields), column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(buttons, text="Save", command=submit).pack(side="right")
        dialog.bind("<Return>", lambda _event: submit())
        entries[fields[0][0]].focus_set()

    def add_student(self):
        fields = [("admission", "Admission number *", ""), ("first", "First name *", ""),
                  ("last", "Last name *", ""), ("class", "Class/grade *", ""),
                  ("dob", "Date of birth (YYYY-MM-DD)", ""), ("gender", "Gender", ""),
                  ("guardian", "Guardian name", ""), ("phone", "Guardian phone", ""),
                  ("address", "Address", ""), ("admitted", "Admission date (YYYY-MM-DD)", date.today().isoformat())]
        def save(v):
            if not all(v[key] for key in ("admission", "first", "last", "class", "admitted")):
                messagebox.showerror("Missing information", "Fill all required fields.", parent=self.root)
                return False
            for key, label in (("dob", "Date of birth"), ("admitted", "Admission date")):
                if v[key] and not date_is_valid(v[key]):
                    messagebox.showerror("Invalid date", f"{label} must use YYYY-MM-DD.", parent=self.root)
                    return False
            try:
                with connect() as db:
                    db.execute("INSERT INTO students (admission_number, first_name, last_name, "
                               "class_name, date_of_birth, gender, guardian_name, guardian_phone, "
                               "address, admission_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                               (v["admission"], v["first"], v["last"], v["class"], v["dob"] or None,
                                v["gender"] or None, v["guardian"] or None, v["phone"] or None,
                                v["address"] or None, v["admitted"]))
            except sqlite3.IntegrityError:
                messagebox.showerror("Could not save", "Admission number already exists.", parent=self.root)
                return False
            self.refresh_all()
            return True
        self.form_dialog("Admit student", fields, save)

    def student_id(self, admission):
        with connect() as db:
            row = db.execute("SELECT id FROM students WHERE admission_number = ?", (admission,)).fetchone()
        return row[0] if row else None

    def add_payment(self):
        fields = [("admission", "Student admission number *", ""), ("amount", "Amount *", ""),
                  ("date", "Payment date (YYYY-MM-DD)", date.today().isoformat()),
                  ("term", "Term *", ""), ("method", "Payment method", ""), ("reference", "Receipt/reference", "")]
        def save(v):
            student_id = self.student_id(v["admission"])
            if student_id is None:
                messagebox.showerror("Student not found", "Check the admission number.", parent=self.root)
                return False
            try:
                amount = float(v["amount"])
                if amount <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid amount", "Enter an amount greater than zero.", parent=self.root)
                return False
            if not v["term"] or not date_is_valid(v["date"]):
                messagebox.showerror("Invalid details", "Enter a term and valid YYYY-MM-DD payment date.", parent=self.root)
                return False
            with connect() as db:
                db.execute("INSERT INTO payments (student_id, amount, payment_date, term, method, reference) "
                           "VALUES (?, ?, ?, ?, ?, ?)",
                           (student_id, amount, v["date"], v["term"], v["method"] or None, v["reference"] or None))
            self.refresh_all()
            return True
        self.form_dialog("Record fee payment", fields, save)

    def add_exam(self):
        fields = [("admission", "Student admission number *", ""), ("exam", "Exam name *", ""),
                  ("subject", "Subject *", ""), ("score", "Score *", ""), ("max", "Maximum score *", ""),
                  ("date", "Exam date (YYYY-MM-DD)", date.today().isoformat())]
        def save(v):
            student_id = self.student_id(v["admission"])
            if student_id is None:
                messagebox.showerror("Student not found", "Check the admission number.", parent=self.root)
                return False
            try:
                score, maximum = float(v["score"]), float(v["max"])
                if maximum <= 0 or score < 0 or score > maximum:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid score", "Enter a score from zero to a positive maximum score.", parent=self.root)
                return False
            if not v["exam"] or not v["subject"] or not date_is_valid(v["date"]):
                messagebox.showerror("Invalid details", "Enter exam, subject, and a valid YYYY-MM-DD date.", parent=self.root)
                return False
            with connect() as db:
                db.execute("INSERT INTO exams (student_id, exam_name, subject, score, max_score, exam_date) "
                           "VALUES (?, ?, ?, ?, ?, ?)",
                           (student_id, v["exam"], v["subject"], score, maximum, v["date"]))
            self.refresh_all()
            return True
        self.form_dialog("Record exam result", fields, save)

    def export_rows(self, kind):
        if kind == "dashboard":
            with connect() as db:
                return [("Metric", "Value"),
                        ("Students", db.execute("SELECT COUNT(*) FROM students").fetchone()[0]),
                        ("Fees collected", db.execute("SELECT COALESCE(SUM(amount), 0) FROM payments").fetchone()[0]),
                        ("Exam results", db.execute("SELECT COUNT(*) FROM exams").fetchone()[0]),
                        ("Average score (%)", db.execute("SELECT AVG(score * 100.0 / max_score) FROM exams WHERE max_score > 0").fetchone()[0] or 0)]
        headers = {
            "students": ("Admission number", "Student", "Class", "Guardian", "Guardian phone", "Admission date"),
            "payments": ("Payment date", "Admission number", "Student", "Term", "Amount", "Method", "Reference"),
            "exams": ("Exam date", "Admission number", "Student", "Exam", "Subject", "Score", "Maximum score", "Percent"),
        }
        return [headers[kind], *self.get_data(kind)]

    def current_kind(self):
        selected = self.notebook.index(self.notebook.select())
        return {0: "dashboard", 1: "students", 2: "payments", 3: "exams"}[selected]

    def export_csv(self):
        kind = self.current_kind()
        filename = filedialog.asksaveasfilename(
            parent=self.root, defaultextension=".csv", initialfile=f"{kind}_report.csv",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")))
        if not filename:
            return
        rows = self.export_rows(kind)
        if kind != "dashboard":
            headers = {
                "students": ("Admission number", "Student", "Class", "Guardian", "Guardian phone", "Admission date"),
                "payments": ("Payment date", "Admission number", "Student", "Term", "Amount", "Method", "Reference"),
                "exams": ("Exam date", "Admission number", "Student", "Exam", "Subject", "Score", "Maximum score", "Percent"),
            }
            rows.insert(0, headers[kind])
        try:
            with open(filename, "w", newline="", encoding="utf-8-sig") as output:
                csv.writer(output).writerows(rows)
            messagebox.showinfo("Export complete", f"CSV report saved to:\n{filename}", parent=self.root)
        except OSError as error:
            messagebox.showerror("Export failed", str(error), parent=self.root)

    def export_excel(self):
        try:
            from openpyxl import Workbook
        except ImportError:
            messagebox.showerror("Excel export unavailable",
                                 "Install the optional dependency first:\npython -m pip install openpyxl",
                                 parent=self.root)
            return
        filename = filedialog.asksaveasfilename(
            parent=self.root, defaultextension=".xlsx", initialfile="school_reports.xlsx",
            filetypes=(("Excel workbook", "*.xlsx"),))
        if not filename:
            return
        workbook = Workbook()
        workbook.remove(workbook.active)
        datasets = {
            "Dashboard": self.export_rows("dashboard"),
            "Students": self.export_rows("students"),
            "Payments": self.export_rows("payments"),
            "Exams": self.export_rows("exams"),
        }
        headers = {
            "Students": ("Admission number", "Student", "Class", "Guardian", "Guardian phone", "Admission date"),
            "Payments": ("Payment date", "Admission number", "Student", "Term", "Amount", "Method", "Reference"),
            "Exams": ("Exam date", "Admission number", "Student", "Exam", "Subject", "Score", "Maximum score", "Percent"),
        }
        try:
            for name, rows in datasets.items():
                sheet = workbook.create_sheet(name)
                if name in headers:
                    sheet.append(headers[name])
                for row in rows:
                    sheet.append(list(row))
                sheet.freeze_panes = "A2"
                sheet.auto_filter.ref = sheet.dimensions
                for column in sheet.columns:
                    letter = column[0].column_letter
                    width = min(max(max(len(str(cell.value or "")) for cell in column) + 2, 12), 36)
                    sheet.column_dimensions[letter].width = width
            workbook.save(filename)
            messagebox.showinfo("Export complete", f"Excel workbook saved to:\n{filename}", parent=self.root)
        except (OSError, PermissionError) as error:
            messagebox.showerror("Export failed", str(error), parent=self.root)

    def change_password(self):
        old = simpledialog.askstring("Change password", "Current password:", show="•", parent=self.root)
        if old is None:
            return
        with connect() as db:
            admin = db.execute("SELECT * FROM administrators WHERE username = ?", (self.username,)).fetchone()
        if not hmac.compare_digest(password_digest(old, admin["salt"]), admin["password_hash"]):
            messagebox.showerror("Password not changed", "Current password is incorrect.", parent=self.root)
            return
        new = simpledialog.askstring("Change password", "New password (at least 10 characters):",
                                     show="•", parent=self.root)
        if new is None:
            return
        if len(new) < 10:
            messagebox.showerror("Weak password", "Use at least 10 characters.", parent=self.root)
            return
        confirmation = simpledialog.askstring("Change password", "Confirm new password:",
                                              show="•", parent=self.root)
        if new != confirmation:
            messagebox.showerror("Password mismatch", "Passwords do not match.", parent=self.root)
            return
        salt = os.urandom(16)
        with connect() as db:
            db.execute("UPDATE administrators SET salt = ?, password_hash = ? WHERE id = ?",
                       (salt, password_digest(new, salt), admin["id"]))
        messagebox.showinfo("Password changed", "Your password was updated.", parent=self.root)

    def logout(self):
        self.root.withdraw()
        login = LoginDialog(self.root)
        self.root.wait_window(login)
        if not login.username:
            self.root.destroy()
            return
        self.username = login.username
        self.root.title("School Management System")
        # Update the displayed administrator name after logging in again.
        for child in self.root.winfo_children():
            if isinstance(child, ttk.Frame):
                for widget in child.winfo_children():
                    if isinstance(widget, ttk.Label) and str(widget.cget("text")).startswith("Administrator:"):
                        widget.config(text=f"Administrator: {self.username}")
        self.root.deiconify()


def main():
    initialize_database()
    root = tk.Tk()
    SchoolManagementApp(root)
    if root.winfo_exists():
        root.mainloop()


if __name__ == "__main__":
    main()
