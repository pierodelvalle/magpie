# Magpie

A minimal, Tabbycat-style debate tabulation app: a Swiss-style, 2-team format with public draws and standings. See `docs/` for the build plan and rules.

## Stack

- Backend: Django 5.2, Django REST Framework, PostgreSQL 17
- Frontend: Vue 3, Vite, TypeScript
- Local environment: Docker Compose

## Running the app

Requires Docker with Compose.

1. Create your environment file and fill in the values:

   ```sh
   cp .env.example .env
   ```

   Generate a Django secret key with:

   ```sh
   python3 -c "import secrets; print(secrets.token_urlsafe(50))"
   ```

   `DATABASE_URL` must match the `POSTGRES_*` values.

2. Start everything:

   ```sh
   docker compose up --build
   ```

3. In another terminal, apply migrations and create an admin user:

   ```sh
   docker compose exec backend python manage.py migrate
   docker compose exec backend python manage.py createsuperuser
   ```

| Service  | URL                           |
|----------|-------------------------------|
| Frontend | http://localhost:5173         |
| Backend  | http://localhost:8000         |
| Admin    | http://localhost:8000/admin/  |

## Development

Run these from the repo root while the containers are up.

```sh
docker compose exec backend pytest
docker compose exec backend ruff check .
docker compose exec backend mypy .
docker compose exec frontend npm run test:unit
docker compose exec frontend npm run lint
```

## Environment variables

| Variable               | Purpose                                                   |
|------------------------|-----------------------------------------------------------|
| `POSTGRES_DB`          | Database name                                             |
| `POSTGRES_USER`        | Database user                                             |
| `POSTGRES_PASSWORD`    | Database password                                         |
| `DATABASE_URL`         | Connection string the backend uses                        |
| `DJANGO_SECRET_KEY`    | Django secret key (required, no default)                  |
| `DJANGO_DEBUG`         | `1` to enable debug mode                                  |
