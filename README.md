# USeP Marketplace

A Django-based university marketplace for the University of Southeastern Philippines.

---

## Requirements

Make sure you have installed:

* Python 3.12+
* Git
* MySQL
* pip

---

# Setup After Cloning

## 1. Clone the repository

```bash
git clone <repository-url>
cd USeP-Marketplace-2026
```

---

## 2. Create a virtual environment

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

---

## 3. Install project dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Create the ignored folders

The following folders are intentionally ignored by Git and must be created after cloning:

```text
logs/
media/
```

### Linux / macOS

```bash
mkdir -p logs media
```

### Windows PowerShell

```powershell
New-Item -ItemType Directory -Force logs
New-Item -ItemType Directory -Force media
```

---

## 5. Create the `.env` file

Create a `.env` file in the project root:

```text
USeP-Marketplace-2026/
├── manage.py
├── .env
├── apps/
├── config/
├── logs/
├── media/
├── static/
└── ...
```

Do not commit `.env` to Git.

Use the project's `.env.example` if one is provided.

---

# MySQL Database Setup

The project uses **MySQL** as its database.

Create a database in MySQL before running Django migrations.

For example:

```sql
CREATE DATABASE usep_marketplace;
```

Make sure the database name, MySQL username, password, and host/port match the values configured in your `.env` file.

Example:

```text
DB_NAME=usep_marketplace
DB_USER=your_mysql_user
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306
```

Do not use the example values as actual credentials.

---

# Database Migration

After configuring MySQL:

```bash
python manage.py migrate
```

This creates the tables required by Django in your MySQL database.

---

# Check the Project

Run:

```bash
python manage.py check
```

A successful check should show:

```text
System check identified no issues (0 silenced).
```

---

# Run the Development Server

```bash
python manage.py runserver
```

The website will normally be available at:

```text
http://127.0.0.1:8000/
```

---

# Common Django Commands

## Check for errors

```bash
python manage.py check
```

## Run the development server

```bash
python manage.py runserver
```

## Create migrations

Run this after changing Django models:

```bash
python manage.py makemigrations
```

## Apply migrations

```bash
python manage.py migrate
```

## Check migration status

```bash
python manage.py showmigrations
```

## Create an administrator account

```bash
python manage.py createsuperuser
```

## Open the Django shell

```bash
python manage.py shell
```

## Collect static files

```bash
python manage.py collectstatic
```

---

# After Pulling New Changes

After pulling changes from Git:

```bash
git pull
```

Activate your virtual environment if necessary.

Install any new dependencies:

```bash
pip install -r requirements.txt
```

Apply any new migrations:

```bash
python manage.py migrate
```

Check the project:

```bash
python manage.py check
```

Then start the server:

```bash
python manage.py runserver
```

### Quick version

For normal updates:

```bash
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py runserver
```

---

# Project Structure

```text
USeP-Marketplace-2026/
│
├── manage.py
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── ...
│
├── apps/
│   └── accounts/
│       ├── migrations/
│       ├── templates/
│       │   └── accounts/
│       ├── static/
│       │   └── accounts/
│       ├── admin.py
│       ├── apps.py
│       ├── models.py
│       ├── urls.py
│       └── views.py
│
├── templates/
│   └── base.html
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
├── logs/
│
├── media/
│
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

---

# Git Notes

The following files and folders should normally not be committed:

```text
.venv/
.env
logs/
media/
__pycache__/
*.pyc
```

The `logs/` and `media/` directories are ignored by Git, so they must be recreated when setting up the project on a new machine.

---

# Development Workflow

When starting work:

```bash
git pull
```

Activate your virtual environment.

Install dependencies if necessary:

```bash
pip install -r requirements.txt
```

Apply migrations:

```bash
python manage.py migrate
```

Check Django:

```bash
python manage.py check
```

Run the server:

```bash
python manage.py runserver
```

---

# Model Changes

Whenever you modify a Django model:

```bash
python manage.py makemigrations
python manage.py migrate
```

Commit the generated migration files to Git.

Do not delete existing migrations that have already been committed.

---

# First-Time Setup Summary

```bash
git clone <repository-url>
cd USeP-Marketplace-2026

python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
```

Create the required folders:

### Linux/macOS

```bash
mkdir -p logs media
```

### Windows PowerShell

```powershell
New-Item -ItemType Directory -Force logs
New-Item -ItemType Directory -Force media
```

Create and configure your `.env` file, then create the MySQL database.

Finally:

```bash
python manage.py migrate
python manage.py check
python manage.py runserver
```

The project should then be available at:

```text
http://127.0.0.1:8000/
```
