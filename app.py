from datetime import datetime
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from sqlalchemy import inspect, text

from models import Customer, Employee, Vehicle, WorkOrder, db, seed_data


def ensure_workorder_columns():
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


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "garage-geheim-voor-ontwikkeldoeleinden"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///garage.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()
        ensure_workorder_columns()
        seed_data()

    def parse_appointment(form_data):
        appointment_date = datetime.strptime(
            form_data["appointment_date"], "%Y-%m-%d"
        ).date()
        appointment_time = datetime.strptime(
            form_data["appointment_time"], "%H:%M"
        ).time()
        return appointment_date, appointment_time

    def login_required(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if "employee_id" not in session:
                flash("Log in als medewerker om deze pagina te bekijken.", "warning")
                return redirect(url_for("login"))
            return view_func(*args, **kwargs)

        return wrapped_view

    @app.context_processor
    def inject_session_data():
        return {"logged_in": "employee_id" in session}

    @app.route("/")
    def home():
        return render_template("home.html")

    @app.route("/diensten")
    def diensten():
        return render_template("diensten.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            employee = Employee.query.filter_by(email=email).first()

            if employee and employee.check_password(password):
                session["employee_id"] = employee.id
                session["employee_name"] = employee.name
                flash("Je bent ingelogd als medewerker.", "success")
                return redirect(url_for("klanten_overzicht"))

            flash("Ongeldige e-mail of wachtwoord.", "danger")

        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.pop("employee_id", None)
        session.pop("employee_name", None)
        flash("Je bent uitgelogd.", "info")
        return redirect(url_for("home"))

    @app.route("/klanten")
    @login_required
    def klanten_overzicht():
        klanten = Customer.query.order_by(Customer.last_name, Customer.first_name).all()
        return render_template("klanten_overzicht.html", klanten=klanten)

    @app.route("/klanten/nieuw", methods=["GET", "POST"])
    @login_required
    def klant_nieuw():
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
        klant = Customer.query.get_or_404(id)
        return render_template("klant_detail.html", klant=klant)

    @app.route("/klanten/<int:id>/bewerken", methods=["GET", "POST"])
    @login_required
    def klant_bewerken(id):
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
        klant = Customer.query.get_or_404(id)
        db.session.delete(klant)
        db.session.commit()
        flash("Klant verwijderd.", "info")
        return redirect(url_for("klanten_overzicht"))

    @app.route("/voertuigen/nieuw", methods=["GET", "POST"])
    @login_required
    def voertuig_nieuw():
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
        voertuig = Vehicle.query.get_or_404(id)
        klant_id = voertuig.customer_id
        db.session.delete(voertuig)
        db.session.commit()
        flash("Voertuig verwijderd.", "info")
        return redirect(url_for("klant_detail", id=klant_id))

    @app.route("/werkorders")
    @login_required
    def werkorders_overzicht():
        werkorders = WorkOrder.query.order_by(WorkOrder.id.desc()).all()
        return render_template("werkorders_overzicht.html", werkorders=werkorders)

    @app.route("/werkorders/nieuw", methods=["GET", "POST"])
    @login_required
    def werkorder_nieuw():
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
        werkorder = WorkOrder.query.get_or_404(id)
        return render_template("werkorder_detail.html", werkorder=werkorder)

    @app.route("/werkorders/<int:id>/bewerken", methods=["GET", "POST"])
    @login_required
    def werkorder_bewerken(id):
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
        werkorder = WorkOrder.query.get_or_404(id)
        db.session.delete(werkorder)
        db.session.commit()
        flash("Werkorder verwijderd.", "info")
        return redirect(url_for("werkorders_overzicht"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
