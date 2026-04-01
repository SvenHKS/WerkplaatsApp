from datetime import date, time

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


class Admin(db.Model):
    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Employee(db.Model):
    __tablename__ = "employees"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    notes = db.Column(db.Text)

    vehicles = db.relationship(
        "Vehicle",
        back_populates="customer",
        cascade="all, delete-orphan",
        order_by="Vehicle.license_plate",
    )
    workorders = db.relationship(
        "WorkOrder",
        back_populates="customer",
        cascade="all, delete-orphan",
        order_by="WorkOrder.id.desc()",
    )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Vehicle(db.Model):
    __tablename__ = "vehicles"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    license_plate = db.Column(db.String(20), unique=True, nullable=False)
    vin = db.Column(db.String(50))

    customer = db.relationship("Customer", back_populates="vehicles")
    workorders = db.relationship(
        "WorkOrder",
        back_populates="vehicle",
        cascade="all, delete-orphan",
        order_by="WorkOrder.id.desc()",
    )

    @property
    def display_name(self):
        return f"{self.brand} {self.model} ({self.license_plate})"


class WorkOrder(db.Model):
    __tablename__ = "workorders"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.id"), nullable=False)
    car_brand = db.Column(db.String(100), nullable=True)
    car_model = db.Column(db.String(100), nullable=True)
    license_plate = db.Column(db.String(20), nullable=True)
    appointment_date = db.Column(db.Date, nullable=True)
    appointment_time = db.Column(db.Time, nullable=True)
    complaint = db.Column(db.Text, nullable=False)
    work_description = db.Column(db.Text, nullable=False)
    estimated_cost = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(30), nullable=False, default="nieuw")

    customer = db.relationship("Customer", back_populates="workorders")
    vehicle = db.relationship("Vehicle", back_populates="workorders")

    @property
    def appointment_summary(self):
        if self.appointment_date and self.appointment_time:
            return (
                f"{self.appointment_date.strftime('%d-%m-%Y')} om "
                f"{self.appointment_time.strftime('%H:%M')}"
            )
        return "Nog niet ingepland"

    def sync_vehicle_snapshot(self):
        if self.vehicle:
            self.car_brand = self.vehicle.brand
            self.car_model = self.vehicle.model
            self.license_plate = self.vehicle.license_plate


def seed_data():
    if Admin.query.count() == 0:
        admin = Admin(username="admin")
        admin.set_password("welkomadmin")
        db.session.add(admin)

    if Employee.query.count() == 0:
        employee = Employee(
            name="Gerard Garage",
            email="medewerker@garage.local",
        )
        employee.set_password("welkom123")
        db.session.add(employee)

    test_customers = [
        {
            "first_name": "Sanne",
            "last_name": "Jansen",
            "email": "sanne@example.com",
            "phone": "0612345678",
            "notes": "Voorkeur voor contact per e-mail.",
            "vehicles": [
                {
                    "brand": "Volkswagen",
                    "model": "Golf",
                    "year": 2018,
                    "license_plate": "AB-123-C",
                    "vin": "WVWZZZ1KZJW000001",
                },
                {
                    "brand": "Toyota",
                    "model": "Yaris",
                    "year": 2020,
                    "license_plate": "KL-456-D",
                    "vin": "JTDBR32E302000002",
                },
            ],
        },
        {
            "first_name": "Tim",
            "last_name": "de Vries",
            "email": "tim.devries@example.com",
            "phone": "0611122233",
            "notes": "Liever contact via telefoon.",
            "vehicles": [
                {
                    "brand": "Peugeot",
                    "model": "208",
                    "year": 2019,
                    "license_plate": "MN-789-E",
                    "vin": "VF3CCBHZ0KT000003",
                },
                {
                    "brand": "Hyundai",
                    "model": "i20",
                    "year": 2022,
                    "license_plate": "UV-135-J",
                    "vin": "KMHBC81AAKU000007",
                }
            ],
        },
        {
            "first_name": "Fatima",
            "last_name": "El Amrani",
            "email": "fatima.elamrani@example.com",
            "phone": "0622233344",
            "notes": "Afspraak altijd in de middag.",
            "vehicles": [
                {
                    "brand": "Renault",
                    "model": "Clio",
                    "year": 2017,
                    "license_plate": "PQ-321-F",
                    "vin": "VF1B7A6A555000004",
                }
            ],
        },
        {
            "first_name": "Lars",
            "last_name": "van Dijk",
            "email": "lars.vandijk@example.com",
            "phone": "0633344455",
            "notes": "Wil vooraf een kosteninschatting.",
            "vehicles": [
                {
                    "brand": "Ford",
                    "model": "Focus",
                    "year": 2016,
                    "license_plate": "RS-654-G",
                    "vin": "WF0AXXWPMAG000005",
                }
            ],
        },
        {
            "first_name": "Nina",
            "last_name": "Bakker",
            "email": "nina.bakker@example.com",
            "phone": "0644455566",
            "notes": "Geen bijzonderheden.",
            "vehicles": [
                {
                    "brand": "Opel",
                    "model": "Corsa",
                    "year": 2021,
                    "license_plate": "TU-987-H",
                    "vin": "W0L0SDL08M6000006",
                }
            ],
        },
    ]

    existing_customers = {customer.email: customer for customer in Customer.query.all()}
    existing_vehicles = {
        vehicle.license_plate: vehicle for vehicle in Vehicle.query.all()
    }

    for entry in test_customers:
        customer = existing_customers.get(entry["email"])
        if not customer:
            customer = Customer(
                first_name=entry["first_name"],
                last_name=entry["last_name"],
                email=entry["email"],
                phone=entry["phone"],
                notes=entry["notes"],
            )
            db.session.add(customer)
            db.session.flush()
            existing_customers[entry["email"]] = customer

        for vehicle_data in entry["vehicles"]:
            license_plate = vehicle_data["license_plate"]
            if license_plate in existing_vehicles:
                continue
            vehicle = Vehicle(
                customer_id=customer.id,
                brand=vehicle_data["brand"],
                model=vehicle_data["model"],
                year=vehicle_data["year"],
                license_plate=license_plate,
                vin=vehicle_data["vin"],
            )
            db.session.add(vehicle)
            db.session.flush()
            existing_vehicles[license_plate] = vehicle

    if WorkOrder.query.count() == 0:
        sanne = existing_customers.get("sanne@example.com")
        first_vehicle = None
        if sanne:
            first_vehicle = (
                Vehicle.query.filter_by(customer_id=sanne.id)
                .order_by(Vehicle.id.asc())
                .first()
            )
        if first_vehicle:
            workorder = WorkOrder(
                customer_id=sanne.id,
                vehicle_id=first_vehicle.id,
                car_brand=first_vehicle.brand,
                car_model=first_vehicle.model,
                license_plate=first_vehicle.license_plate,
                appointment_date=date(2026, 3, 30),
                appointment_time=time(9, 0),
                complaint="Rammelend geluid bij het remmen.",
                work_description="Controle van remblokken en remschijven, plus proefrit.",
                estimated_cost=245.0,
                status="in uitvoering",
            )
            db.session.add(workorder)

    for workorder in WorkOrder.query.all():
        if not workorder.car_brand or not workorder.car_model or not workorder.license_plate:
            workorder.sync_vehicle_snapshot()
        if workorder.appointment_date is None:
            workorder.appointment_date = date(2026, 3, 30)
        if workorder.appointment_time is None:
            workorder.appointment_time = time(9, 0)

    db.session.commit()
