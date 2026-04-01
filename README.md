# Garage Webapp met Flask

Een eenvoudige webapp voor een autowerkplaats met:

- publieke pagina's voor gasten
- medewerker-login via sessies
- beheer van klanten, voertuigen en werkorders
- SQLite-database via SQLAlchemy

## Installatie

```bash
cd <projectmap>
python -m venv .venv
```

Activeer daarna de virtuele omgeving:

```bash
# macOS / Linux
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Installeer en start vervolgens de app:

```bash
pip install -r requirements.txt
python app.py
```

Open daarna `http://localhost:5000`.

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
