# Garage Webapp met Flask

Een eenvoudige webapp voor een autowerkplaats met:

- publieke pagina's voor gasten
- medewerker-login via sessies
- beheer van klanten, voertuigen en werkorders
- SQLite-database via SQLAlchemy

## Installatie

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Open daarna `http://127.0.0.1:5000`.

## Demo-login

- E-mail: `medewerker@garage.local`
- Wachtwoord: `welkom123`

## Belangrijkste routes

- `/` homepagina
- `/diensten` overzicht van diensten
- `/login` medewerker-login
- `/logout` uitloggen
- `/klanten` beveiligd klantenoverzicht
- `/klanten/nieuw` nieuwe klant toevoegen
- `/klanten/<id>` klantdetails
- `/voertuigen/nieuw` voertuig toevoegen
- `/werkorders` beveiligd werkorderoverzicht
- `/werkorders/nieuw` nieuwe werkorder maken
- `/werkorders/<id>` werkorderdetails
