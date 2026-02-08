# Healthy Mentoring

A Django-based mentoring platform with:

- Custom user authentication (Email-based)
- Dashboard for mentors
- Landing page
- Docker support for production

## Development

1. Copy `.env.example` to `.env`
2. `python -m venv .venv`
3. `source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. `python manage.py migrate`
6. `python manage.py runserver`
7. `python manage.py reset_templates --confirm`
  ----- This will:
        Delete all existing templates (custom and default)
        Delete all questionnaires and questions
        Create 4 new default templates with questionnaires and questions
8. `python manage.py generate_guides`  


.venv\Scripts\python.exe create_superuser.py
.venv\Scripts\python.exe manage.py runserver

## Production

The project is designed to be run with Docker Compose behind a host-level reverse proxy (e.g., Caddy).

### Architecture

- **Django Container**: Runs Gunicorn on internal port `8000`.
- **Port Mapping**: Exposes container port `8000` to host port `8001`.
- **Reverse Proxy**: An external Caddy (or Nginx) on the host should proxy traffic from the domain to `localhost:8001`.
- **Static Files**: Collected to `/srv/static` inside the container (volume `static_volume`).

### Running in Production

1. Set `DEVELOPMENT_MODE=prod` in `.env`.
2. Run build script:
  ```bash
    python setup.py
  ```
    (This runs `docker-compose -f docker-compose.yml up -d`)

### Host Caddy Example

If you are using Caddy on the host, your `Caddyfile` should look something like this:

```caddy
mentoring.marianadamus.com {
    reverse_proxy localhost:8001
}
```

