<div align="center">

<img src="https://raw.githubusercontent.com/Developer-Akademie-Backendkurs/project.Videoflix/main/assets/icons/logo_icon.svg" alt="Videoflix logo" width="80">

# Videoflix Backend

**A Django REST API for account management and HLS video streaming.**

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/Django-REST_Framework-A30000)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

[**Provided frontend**](https://github.com/Developer-Akademie-Backendkurs/project.Videoflix) · [**Backend repository**](https://github.com/JuliaKeller13/videoflix_backend)

</div>

## About

Videoflix is a video streaming backend developed as part of the **Developer Akademie Backend curriculum**. The frontend is supplied separately; this repository contains my implementation of the backend and its automated tests.

The application supports email-based registration and password reset, **JWT authentication with HttpOnly cookies**, and authenticated video playback. Uploaded MP4 files are processed asynchronously using **FFmpeg, Django RQ, and Redis** into HLS streams at **480p, 720p, and 1080p**.

**Tech stack:** Django REST Framework · PostgreSQL · Redis · Django RQ · FFmpeg · Docker Compose

## Quick Start

**Prerequisites:** Git and Docker Desktop with Docker Compose. Python, FFmpeg, and the RQ worker run inside Docker; no local installation or SMTP account is required for the default setup.

### 1. Clone and configure

```powershell
git clone https://github.com/JuliaKeller13/videoflix_backend.git
cd videoflix_backend
Copy-Item .env.template .env
```

On macOS/Linux, use `cp .env.template .env` instead.

Edit `.env` and provide:

| Configuration | Purpose |
|---|---|
| `SECRET_KEY` | A strong, unique Django secret key |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | PostgreSQL database credentials |
| `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_PASSWORD` | Django Admin login |
| `FRONTEND_ACTIVATION_URL` | Activation page of the supplied frontend |

Keep `FRONTEND_ACTIVATION_URL=http://127.0.0.1:5500/pages/auth/activate.html` when using the frontend with VS Code Live Server at port 5500. The backend uses this URL to generate email links and determine the allowed frontend origin.

**Never commit `.env` or real credentials.** The `.env.template` contains only example values; email delivery can be configured separately below.

### 2. Start Docker

```bash
docker compose up -d --build
```

Docker starts **Django, PostgreSQL, and Redis**. The backend startup script automatically runs migrations, creates the configured superuser if needed, and launches the **RQ worker**. No separate worker command is necessary.

- **API:** http://127.0.0.1:8000/api/
- **Django Admin:** http://127.0.0.1:8000/admin/

### 3. Add a video

Log in to Django Admin, open **Videos**, and create a video with a title, description, category, and MP4 file. A thumbnail is optional.

After saving, the background worker creates the HLS playlists and TS segments for all three resolutions and generates a thumbnail if one was not supplied. The processing status changes from `pending` to `processing` and finally to `ready` or `failed`.

**Only `ready` videos appear in the frontend and can be streamed.** A fresh clone has no preloaded videos, so upload at least one and allow processing to finish before evaluating the video dashboard.

Uploads are validated in Django Admin: **MP4 up to 200 MiB**, and optional **JPG/JPEG, PNG, or WebP thumbnails up to 5 MiB**.

### 4. Connect the frontend

Clone the [official Videoflix frontend](https://github.com/Developer-Akademie-Backendkurs/project.Videoflix), open its root `index.html` in **VS Code Live Server**, and use `http://127.0.0.1:5500`.

The provided frontend already sends requests to `http://127.0.0.1:8000/api/` with authentication cookies. No frontend source changes are required.

**To test registration:** Sign up in the frontend, retrieve the activation link from the Docker logs (or your email inbox when using SMTP), open it, and then log in. Password reset follows the same email-based workflow.

## Email Configuration

Videoflix supports two email backends for account activation and password resets:

**Console backend (default):** The `.env.template` sets `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend`. Emails are printed in the backend container logs instead of being delivered to an inbox. This allows reviewers to test activation and password reset without SMTP credentials:

```bash
docker compose logs -f web
```

**SMTP delivery (optional):** To send real emails, change the following values in your private `.env` file. This example uses Mailtrap Email Sending rather than its testing sandbox:

```dotenv
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=live.smtp.mailtrap.io
EMAIL_PORT=587
EMAIL_HOST_USER=api
EMAIL_HOST_PASSWORD=your_mailtrap_api_token
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL=hello@demomailtrap.co
```

The Mailtrap demo domain can deliver only to the email address associated with the Mailtrap account. Sending to other recipients requires a verified sending domain and an authorized sender address. Never commit SMTP tokens or your local `.env` file.

After changing `.env`, recreate the web container to apply the new environment variables:

```bash
docker compose up -d --force-recreate web
```

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/register/` | Register an inactive account and send activation email |
| GET | `/api/activate/{uid}/{token}/` | Activate account |
| POST | `/api/login/` | Log in and set JWT cookies |
| POST | `/api/logout/` | Log out, clear cookies, and revoke refresh token |
| POST | `/api/token/refresh/` | Renew access cookie |
| POST | `/api/password_reset/` | Request a password reset email |
| POST | `/api/password_confirm/{uid}/{token}/` | Confirm a new password |
| GET | `/api/video/` | List ready videos and thumbnail URLs |
| GET | `/api/video/{movie_id}/{resolution}/index.m3u8` | Get HLS playlist |
| GET | `/api/video/{movie_id}/{resolution}/{segment}/` | Get HLS TS segment |

Protected endpoints authenticate through the `access_token` **HttpOnly cookie**; the `refresh_token` cookie renews it. Supported HLS resolutions: `480p`, `720p`, `1080p`. The video list returns `id`, `created_at`, `title`, `description`, `thumbnail_url`, and `category`.

During local development, thumbnail URLs are publicly accessible under `/media/thumbnail/`. Original MP4 uploads and HLS files must be accessed through the protected API, not direct `/media/` URLs.

## Tests and Useful Commands

Run all tests:

```bash
docker compose exec web python manage.py test auth_app video_app --settings=core.test_settings
```

Run statement coverage:

```bash
docker compose exec web python -m coverage run --source=auth_app,video_app manage.py test auth_app video_app --settings=core.test_settings
docker compose exec web python -m coverage report -m
```

Check logs or stop the project:

```bash
docker compose logs -f web
docker compose down
```

The test suite covers registration, activation, JWT cookies, password reset, video uploads, HLS streaming, processing errors, and media cleanup. Database and uploaded media persist in Docker volumes between normal restarts; they are not included in Git.

## Project Structure

```text
core/               Django configuration and URL routing
auth_app/           Registration, authentication, email workflows
video_app/          Admin uploads, FFmpeg/HLS, RQ tasks, streaming API
*/tests/            Automated backend tests
docker-compose.yml  PostgreSQL, Redis, and backend services
.env.template       Local environment variable template
requirements.txt    Python dependencies
```

---

This project was developed for local assessment with the **Developer Akademie frontend**. Public deployment is not required.
