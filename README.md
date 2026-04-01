# Garage Webapp met Flask

Een eenvoudige webapp voor een autowerkplaats met:

- publieke pagina's voor gasten
- medewerker-login via sessies
- beheer van klanten, voertuigen en werkorders
- SQLite-database via SQLAlchemy

## Installatie & opstarten

```bash
cd <projectmap>
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

### Windows (PowerShell)

Aanbevolen (zonder activeren):

```powershell
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python app.py
```

Als je wél wilt activeren maar scripts zijn geblokkeerd:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open daarna `http://localhost:5000` of `http://127.0.0.1:5000`.

De app gebruikt alleen bestanden binnen de eigen projectmap. De SQLite-database staat in `instance/garage.db` en de geheime sessiesleutel in `instance/secret_key.txt`. Daardoor zijn er geen vaste paden nodig die alleen op een specifieke computer werken.

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
