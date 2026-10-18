# Booking service

Учебный REST-сервис бронирования номеров с полным циклом DevOps:
Git → CI (тесты) → Docker-образ с версией → GitHub Container Registry → согласование → развертывание → логи, метрики, трассировки, алерты.

| Что | Где |
|---|---|
| Код сервиса | `app/` (FastAPI + SQLAlchemy) |
| Тесты | `tests/` (pytest) |
| Артефакт | `Dockerfile` |
| Среда запуска | `docker-compose.yml` (сервис + PostgreSQL + Grafana LGTM) |
| Конфигурация развертывания | `.env` (шаблон — `.env.example`) |
| CI/CD | `.github/workflows/ci.yml` |
| Алерт | `observability/grafana-alerts.yaml` |
| Задача по инциденту | `.github/ISSUE_TEMPLATE/incident.md` |
| Скрипты | `scripts/deploy.ps1`, `scripts/traffic.ps1` |
| Описание инфраструктуры | `docs/INFRASTRUCTURE.md` |
| Журнал работ | `docs/DEVOPS_JOURNAL.md` |

## Быстрый старт (Windows, PowerShell)

```powershell
copy .env.example .env
docker compose up -d --build
.\scripts\traffic.ps1
```

- API и документация: http://localhost:8000/docs
- Grafana: http://localhost:3000 (admin / admin)

## Эндпоинты

| Метод | Путь | Что делает |
|---|---|---|
| GET | `/health` | проверка живости |
| GET | `/version` | развернутая версия артефакта |
| POST | `/rooms` | создать номер `{"name": "101", "capacity": 2}` |
| GET | `/rooms` | список номеров |
| POST | `/bookings` | забронировать `{"room_id": 1, "guest_name": "Анна", "check_in": "2026-11-01", "check_out": "2026-11-03"}`; пересечение дат → 409 |
| GET | `/bookings?room_id=1` | список броней |
| GET | `/bookings/{id}` | одна бронь |
| DELETE | `/bookings/{id}` | отменить бронь |
| GET | `/debug/error` | специально возвращает 500 — для проверки алерта |

## Локальные тесты без Docker

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
ruff check .
pytest -v
```
