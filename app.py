from datetime import datetime
from functools import wraps
from pathlib import Path
from secrets import token_hex

from flask import Flask, flash, redirect, render_template, request, session, url_for
from sqlalchemy import inspect, text
from sqlalchemy.sql import func

from models import Admin, Customer, Employee, Vehicle, WorkOrder, db, seed_data


# Basispaden voor instance-data (database en secret key).
BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
DATABASE_PATH = INSTANCE_DIR / "garage.db"
SECRET_KEY_PATH = INSTANCE_DIR / "secret_key.txt"


def ensure_workorder_columns():
    # Simpele migratie: voeg ontbrekende kolommen toe aan bestaande tabel.
    inspector = inspect(db.engine)
    existing_columns = {column["name"] for column in inspector.get_columns("workorders")}
    migrations = {
        "car_brand": "ALTER TABLE workorders ADD COLUMN car_brand VARCHAR(100)",
        "car_model": "ALTER TABLE workorders ADD COLUMN car_model VARCHAR(100)",
        "license_plate": "ALTER TABLE workorders ADD COLUMN license_plate VARCHAR(20)",
        "appointment_date": "ALTER TABLE workorders ADD COLUMN appointment_date DATE",
        "appointment_time": "ALTER TABLE workorders ADD COLUMN appointment_time TIME",
    }

    for column_name, statement in migrations.items():
        if column_name not in existing_columns:
            db.session.execute(text(statement))

    db.session.commit()


def load_or_create_secret_key():
    # Hergebruik bestaande secret key of maak er een nieuwe aan.
    if SECRET_KEY_PATH.exists():
        return SECRET_KEY_PATH.read_text(encoding="utf-8").strip()

    secret_key = token_hex(32)
    SECRET_KEY_PATH.write_text(secret_key, encoding="utf-8")
    return secret_key


def create_app():
    # App-factory zodat Flask de app netjes kan opstarten.
    INSTANCE_DIR.mkdir(exist_ok=True)

    app = Flask(
        __name__,
        instance_path=str(INSTANCE_DIR),
        template_folder=str(BASE_DIR / "pages"),
    )
    app.config["SECRET_KEY"] = load_or_create_secret_key()
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DATABASE_PATH}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        # Zorg dat tabellen bestaan en seed-data klaarstaat.
        db.create_all()
        ensure_workorder_columns()
        seed_data()

    def parse_appointment(form_data):
        # Zet datum- en tijdvelden uit het formulier om naar Python types.
        appointment_date = datetime.strptime(
            form_data["appointment_date"], "%Y-%m-%d"
        ).date()
        appointment_time = datetime.strptime(
            form_data["appointment_time"], "%H:%M"
        ).time()
        return appointment_date, appointment_time

    def login_required(view_func):
        # Decorator voor pagina's die medewerker- of admin-login vereisen.
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if "employee_id" not in session and "admin_id" not in session:
                flash("Log in als medewerker of admin om deze pagina te bekijken.", "warning")
                return redirect(url_for("login"))
            return view_func(*args, **kwargs)

        return wrapped_view

    def admin_required(view_func):
        # Decorator voor pagina's die alleen admins mogen zien.
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if "admin_id" not in session:
                flash("Log in als admin om deze pagina te bekijken.", "warning")
                return redirect(url_for("admin_login"))
            return view_func(*args, **kwargs)

        return wrapped_view

    @app.context_processor
    def inject_session_data():
        # Maak sessiedata beschikbaar in alle templates.
        return {
            "logged_in": "employee_id" in session or "admin_id" in session,
            "admin_logged_in": "admin_id" in session,
            "admin_name": session.get("admin_username"),
            "employee_name": session.get("employee_name"),
        }

    @app.route("/")
    def home():
        # Publieke homepagina.
        return render_template("home.html")

    @app.route("/diensten")
    def diensten():
        # Publieke dienstenpagina.
        return render_template("diensten.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        # Medewerker login (en admin login via gebruikersnaam).
        if request.method == "POST":
            identifier = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            employee = Employee.query.filter_by(email=identifier).first()
            admin = Admin.query.filter_by(username=identifier).first()

            if admin and admin.check_password(password):
                session.pop("employee_id", None)
                session.pop("employee_name", None)
                session["admin_id"] = admin.id
                session["admin_username"] = admin.username
                flash("Je bent ingelogd als admin.", "success")
                return redirect(url_for("admin_portal"))

            if employee and employee.check_password(password):
                session.pop("admin_id", None)
                session.pop("admin_username", None)
                session["employee_id"] = employee.id
                session["employee_name"] = employee.name
                flash("Je bent ingelogd als medewerker.", "success")
                return redirect(url_for("klanten_overzicht"))

            flash("Ongeldige inloggegevens.", "danger")

        return render_template("login.html")

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        # Specifieke admin-loginpagina.
        if request.method == "POST":
            username = request.form.get("username", "").strip().lower()
            password = request.form.get("password", "")
            admin = Admin.query.filter_by(username=username).first()

            if admin and admin.check_password(password):
                session.pop("employee_id", None)
                session.pop("employee_name", None)
                session["admin_id"] = admin.id
                session["admin_username"] = admin.username
                flash("Je bent ingelogd als admin.", "success")
                return redirect(url_for("admin_portal"))

            flash("Ongeldige gebruikersnaam of wachtwoord.", "danger")

        return render_template("admin_login.html")

    @app.route("/logout")
    def logout():
        # Uitloggen voor zowel medewerker als admin.
        session.pop("employee_id", None)
        session.pop("employee_name", None)
        session.pop("admin_id", None)
        session.pop("admin_username", None)
        flash("Je bent uitgelogd.", "info")
        return redirect(url_for("home"))

    @app.route("/admin")
    @admin_required
    def admin_portal():
        # Admin-dashboard met statistieken en medewerkerbeheer.
        total_customers = Customer.query.count()
        total_vehicles = Vehicle.query.count()
        total_workorders = WorkOrder.query.count()
        workorder_statuses = (
            db.session.query(WorkOrder.status, func.count(WorkOrder.id))
            .group_by(WorkOrder.status)
            .order_by(WorkOrder.status)
            .all()
        )
        status_counts = {status: count for status, count in workorder_statuses}

        current_date = datetime.today().date()
        year_value = request.args.get("year") or str(current_date.year)
        month_value = request.args.get("month") or ""

        # Filter voor omzetberekening op jaar/maand.
        revenue_label = year_value
        start_date = None
        end_date = None
        try:
            year_int = int(year_value)
            if month_value:
                month_int = int(month_value)
                start_date = datetime(year_int, month_int, 1).date()
                if month_int == 12:
                    end_date = datetime(year_int + 1, 1, 1).date()
                else:
                    end_date = datetime(year_int, month_int + 1, 1).date()
                revenue_label = start_date.strftime("%B %Y")
            else:
                start_date = datetime(year_int, 1, 1).date()
                end_date = datetime(year_int + 1, 1, 1).date()
                revenue_label = f"{year_int}"
        except ValueError:
            revenue_label = year_value

        revenue_total = 0.0
        if start_date and end_date:
            # Sommeer geschatte kosten binnen de gekozen periode.
            revenue_total = (
                db.session.query(func.coalesce(func.sum(WorkOrder.estimated_cost), 0.0))
                .filter(WorkOrder.appointment_date >= start_date)
                .filter(WorkOrder.appointment_date < end_date)
                .scalar()
                or 0.0
            )

        medewerkers = Employee.query.order_by(Employee.name).all()
        return render_template(
            "admin_portal.html",
            medewerkers=medewerkers,
            total_customers=total_customers,
            total_vehicles=total_vehicles,
            total_workorders=total_workorders,
            status_counts=status_counts,
            year_value=year_value,
            month_value=month_value,
            revenue_label=revenue_label,
            revenue_total=revenue_total,
        )

    @app.route("/admin/medewerkers/nieuw", methods=["GET", "POST"])
    @admin_required
    def medewerker_nieuw():
        # Nieuwe medewerker aanmaken via aparte beheerpagina.
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            password_repeat = request.form.get("password_repeat", "")

            if not name or not email or not password or not password_repeat:
                flash("Vul alle velden in om een medewerker toe te voegen.", "warning")
            elif password != password_repeat:
                flash("De wachtwoorden komen niet overeen.", "danger")
            elif Employee.query.filter_by(email=email).first():
                flash("Er bestaat al een medewerker met dit e-mailadres.", "danger")
            else:
                employee = Employee(name=name, email=email)
                employee.set_password(password)
                db.session.add(employee)
                db.session.commit()
                flash("Medewerker toegevoegd.", "success")
                return redirect(url_for("admin_portal"))

        return render_template("employee_form.html", medewerker=None)

    @app.route("/admin/medewerkers/<int:id>/bewerken", methods=["GET", "POST"])
    @admin_required
    def medewerker_bewerken(id):
        # Bestaande medewerker aanpassen.
        medewerker = Employee.query.get_or_404(id)

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            password_repeat = request.form.get("password_repeat", "")

            existing_employee = Employee.query.filter_by(email=email).first()

            if not name or not email:
                flash("Naam en e-mail zijn verplicht.", "warning")
            elif password and password != password_repeat:
                flash("De wachtwoorden komen niet overeen.", "danger")
            elif password_repeat and not password:
                flash("Vul eerst een nieuw wachtwoord in.", "warning")
            elif existing_employee and existing_employee.id != medewerker.id:
                flash("Er bestaat al een medewerker met dit e-mailadres.", "danger")
            else:
                medewerker.name = name
                medewerker.email = email
                if password:
                    medewerker.set_password(password)
                db.session.commit()
                flash("Medewerker bijgewerkt.", "success")
                return redirect(url_for("admin_portal"))

        return render_template("employee_form.html", medewerker=medewerker)

    @app.route("/admin/medewerkers/<int:id>/verwijderen", methods=["POST"])
    @admin_required
    def medewerker_verwijderen(id):
        # Verwijder een medewerker vanuit het admin-portaal.
        medewerker = Employee.query.get_or_404(id)
        db.session.delete(medewerker)
        db.session.commit()
        flash("Medewerker verwijderd.", "info")
        return redirect(url_for("admin_portal"))

    @app.route("/klanten")
    @login_required
    def klanten_overzicht():
        # Overzicht van alle klanten.
        klanten = Customer.query.order_by(Customer.last_name, Customer.first_name).all()
        return render_template("klanten_overzicht.html", klanten=klanten)

    @app.route("/klanten/nieuw", methods=["GET", "POST"])
    @login_required
    def klant_nieuw():
        # Nieuwe klant aanmaken.
        if request.method == "POST":
            klant = Customer(
                first_name=request.form["first_name"].strip(),
                last_name=request.form["last_name"].strip(),
                email=request.form["email"].strip(),
                phone=request.form["phone"].strip(),
                notes=request.form.get("notes", "").strip(),
            )
            db.session.add(klant)
            db.session.commit()
            flash("Klant toegevoegd.", "success")
            return redirect(url_for("klant_detail", id=klant.id))

        return render_template("klant_form.html", klant=None)

    @app.route("/klanten/<int:id>")
    @login_required
    def klant_detail(id):
        # Detailpagina van een klant.
        klant = Customer.query.get_or_404(id)
        return render_template("klant_detail.html", klant=klant)

    @app.route("/klanten/<int:id>/bewerken", methods=["GET", "POST"])
    @login_required
    def klant_bewerken(id):
        # Bestaande klant bijwerken.
        klant = Customer.query.get_or_404(id)
        if request.method == "POST":
            klant.first_name = request.form["first_name"].strip()
            klant.last_name = request.form["last_name"].strip()
            klant.email = request.form["email"].strip()
            klant.phone = request.form["phone"].strip()
            klant.notes = request.form.get("notes", "").strip()
            db.session.commit()
            flash("Klant bijgewerkt.", "success")
            return redirect(url_for("klant_detail", id=klant.id))

        return render_template("klant_form.html", klant=klant)

    @app.route("/klanten/<int:id>/verwijderen", methods=["POST"])
    @login_required
    def klant_verwijderen(id):
        # Verwijder klant en gekoppelde data.
        klant = Customer.query.get_or_404(id)
        db.session.delete(klant)
        db.session.commit()
        flash("Klant verwijderd.", "info")
        return redirect(url_for("klanten_overzicht"))

    @app.route("/voertuigen/nieuw", methods=["GET", "POST"])
    @login_required
    def voertuig_nieuw():
        # Nieuw voertuig toevoegen aan een klant.
        klanten = Customer.query.order_by(Customer.last_name, Customer.first_name).all()
        if request.method == "POST":
            voertuig = Vehicle(
                customer_id=int(request.form["customer_id"]),
                brand=request.form["brand"].strip(),
                model=request.form["model"].strip(),
                year=int(request.form["year"]),
                license_plate=request.form["license_plate"].strip().upper(),
                vin=request.form.get("vin", "").strip(),
            )
            db.session.add(voertuig)
            db.session.commit()
            flash("Voertuig toegevoegd.", "success")
            return redirect(url_for("klant_detail", id=voertuig.customer_id))

        return render_template("voertuig_form.html", voertuig=None, klanten=klanten)

    @app.route("/voertuigen/<int:id>/bewerken", methods=["GET", "POST"])
    @login_required
    def voertuig_bewerken(id):
        # Voertuiggegevens aanpassen.
        voertuig = Vehicle.query.get_or_404(id)
        klanten = Customer.query.order_by(Customer.last_name, Customer.first_name).all()
        if request.method == "POST":
            voertuig.customer_id = int(request.form["customer_id"])
            voertuig.brand = request.form["brand"].strip()
            voertuig.model = request.form["model"].strip()
            voertuig.year = int(request.form["year"])
            voertuig.license_plate = request.form["license_plate"].strip().upper()
            voertuig.vin = request.form.get("vin", "").strip()
            db.session.commit()
            flash("Voertuig bijgewerkt.", "success")
            return redirect(url_for("klant_detail", id=voertuig.customer_id))

        return render_template("voertuig_form.html", voertuig=voertuig, klanten=klanten)

    @app.route("/voertuigen/<int:id>/verwijderen", methods=["POST"])
    @login_required
    def voertuig_verwijderen(id):
        # Voertuig verwijderen.
        voertuig = Vehicle.query.get_or_404(id)
        klant_id = voertuig.customer_id
        db.session.delete(voertuig)
        db.session.commit()
        flash("Voertuig verwijderd.", "info")
        return redirect(url_for("klant_detail", id=klant_id))

    @app.route("/werkorders")
    @login_required
    def werkorders_overzicht():
        # Overzicht van alle werkorders.
        werkorders = WorkOrder.query.order_by(WorkOrder.id.desc()).all()
        return render_template("werkorders_overzicht.html", werkorders=werkorders)

    @app.route("/werkorders/nieuw", methods=["GET", "POST"])
    @login_required
    def werkorder_nieuw():
        # Nieuwe werkorder aanmaken.
        klanten = Customer.query.order_by(Customer.last_name, Customer.first_name).all()
        voertuigen = Vehicle.query.order_by(Vehicle.license_plate).all()
        if request.method == "POST":
            customer_id = int(request.form["customer_id"])
            vehicle = Vehicle.query.get_or_404(int(request.form["vehicle_id"]))
            if vehicle.customer_id != customer_id:
                flash("Het gekozen voertuig hoort niet bij deze klant.", "danger")
                return render_template(
                    "werkorder_form.html",
                    werkorder=None,
                    klanten=klanten,
                    voertuigen=voertuigen,
                )
            appointment_date, appointment_time = parse_appointment(request.form)
            werkorder = WorkOrder(
                customer_id=customer_id,
                vehicle_id=vehicle.id,
                car_brand=vehicle.brand,
                car_model=vehicle.model,
                license_plate=vehicle.license_plate,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                complaint=request.form["complaint"].strip(),
                work_description=request.form["work_description"].strip(),
                estimated_cost=float(request.form["estimated_cost"]),
                status=request.form["status"],
            )
            db.session.add(werkorder)
            db.session.commit()
            flash("Werkorder aangemaakt.", "success")
            return redirect(url_for("werkorder_detail", id=werkorder.id))

        return render_template(
            "werkorder_form.html",
            werkorder=None,
            klanten=klanten,
            voertuigen=voertuigen,
        )

    @app.route("/werkorders/<int:id>")
    @login_required
    def werkorder_detail(id):
        # Detailpagina van een werkorder.
        werkorder = WorkOrder.query.get_or_404(id)
        return render_template("werkorder_detail.html", werkorder=werkorder)

    @app.route("/werkorders/<int:id>/bewerken", methods=["GET", "POST"])
    @login_required
    def werkorder_bewerken(id):
        # Bestaande werkorder bijwerken.
        werkorder = WorkOrder.query.get_or_404(id)
        klanten = Customer.query.order_by(Customer.last_name, Customer.first_name).all()
        voertuigen = Vehicle.query.order_by(Vehicle.license_plate).all()
        if request.method == "POST":
            customer_id = int(request.form["customer_id"])
            vehicle = Vehicle.query.get_or_404(int(request.form["vehicle_id"]))
            if vehicle.customer_id != customer_id:
                flash("Het gekozen voertuig hoort niet bij deze klant.", "danger")
                return render_template(
                    "werkorder_form.html",
                    werkorder=werkorder,
                    klanten=klanten,
                    voertuigen=voertuigen,
                )
            appointment_date, appointment_time = parse_appointment(request.form)
            werkorder.customer_id = customer_id
            werkorder.vehicle_id = vehicle.id
            werkorder.car_brand = vehicle.brand
            werkorder.car_model = vehicle.model
            werkorder.license_plate = vehicle.license_plate
            werkorder.appointment_date = appointment_date
            werkorder.appointment_time = appointment_time
            werkorder.complaint = request.form["complaint"].strip()
            werkorder.work_description = request.form["work_description"].strip()
            werkorder.estimated_cost = float(request.form["estimated_cost"])
            werkorder.status = request.form["status"]
            db.session.commit()
            flash("Werkorder bijgewerkt.", "success")
            return redirect(url_for("werkorder_detail", id=werkorder.id))

        return render_template(
            "werkorder_form.html",
            werkorder=werkorder,
            klanten=klanten,
            voertuigen=voertuigen,
        )

    @app.route("/werkorders/<int:id>/verwijderen", methods=["POST"])
    @login_required
    def werkorder_verwijderen(id):
        # Werkorder verwijderen.
        werkorder = WorkOrder.query.get_or_404(id)
        db.session.delete(werkorder)
        db.session.commit()
        flash("Werkorder verwijderd.", "info")
        return redirect(url_for("werkorders_overzicht"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
