# EECE 439 Assignment 3: Expense Tracker

Django expense tracker (register/login, expenses CRUD, monthly budgets, filters).

Live on Azure App Service: https://eece439-expenses-kn1116.azurewebsites.net

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DJANGO_DEBUG=True
python manage.py migrate
python manage.py runserver
```

## Tests

```bash
DJANGO_DEBUG=True python manage.py test
```
