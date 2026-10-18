# Инфраструктура REST-сервиса бронирования

Документ описывает, из каких компонентов состоит инфраструктура, какими инструментами реализован каждый узел диаграмм и где это лежит в репозитории.

## Сводная таблица компонентов

| Узел на диаграммах | Инструмент | Где в репозитории | Адрес / порт |
|---|---|---|---|
| Разработчик | ноутбук: Windows 11 + WSL 2, VS Code, Git | — | — |
| Git-репозиторий | GitHub (`<ваш-логин>/booking-service`, ветка `main`) | весь проект | github.com |
| Система CI: сборка и тесты | GitHub Actions, job `test`: ruff + pytest | `.github/workflows/ci.yml` | вкладка **Actions** |
| Результат проверки / отчёт о тестах | JUnit XML `reports/junit.xml`, артефакт сборки `test-report` | `.github/workflows/ci.yml` | страница запуска в Actions |
| Собранное приложение / артефакт | Docker-образ | `Dockerfile` | — |
| Хранилище артефактов | GitHub Container Registry (GHCR) | job `build` | `ghcr.io/<ваш-логин>/booking-service` |
| Конфигурация развертывания | `.env` + переменные окружения в `docker-compose.yml` | `.env.example`, `docker-compose.yml` | — |
| Развертывание разрешено? / ожидание согласования | GitHub Environment `production` с обязательным одобрением | job `deploy` | Settings → Environments |
| Этап доставки / развертывания | job `deploy` (проверочный запуск образа) + `scripts/deploy.ps1` (локальная среда) | `.github/workflows/ci.yml`, `scripts/deploy.ps1` | — |
| Среда запуска | Docker Desktop + Docker Compose на ноутбуке | `docker-compose.yml` | — |
| REST-сервис бронирования | Python 3.13, FastAPI, Uvicorn | `app/` | http://localhost:8000 (`/docs`) |
| База данных | PostgreSQL 17 (в тестах — SQLite в памяти) | сервис `db` в `docker-compose.yml` | внутри сети compose, порт 5432 |
| Логи | Python `logging` → OpenTelemetry → Loki | `app/main.py` | Grafana → Explore → Loki |
| Метрики | OpenTelemetry → Prometheus | `app/main.py` | Grafana → Explore → Prometheus, http://localhost:9090 |
| Трассировки | OpenTelemetry → Tempo | автоинструментация FastAPI и SQLAlchemy | Grafana → Explore → Tempo |
| Система наблюдаемости | `grafana/otel-lgtm` (OTel Collector, Grafana, Loki, Tempo, Prometheus) | сервис `lgtm` в `docker-compose.yml` | http://localhost:3000 (admin / admin) |
| Обнаружение отклонения | правило алерта Grafana «Booking: ответы 5xx» | `observability/grafana-alerts.yaml` | Grafana → Alerting → Alert rules |
| Задача на расследование | GitHub Issues, шаблон «Инцидент / отклонение» | `.github/ISSUE_TEMPLATE/incident.md` | вкладка **Issues** |

## Основной поток разработки

```mermaid
flowchart
    DEV["Разработчик<br/>VS Code + Git"] --->|"Изменение кода<br/>git push"| GIT["Git-репозиторий<br/>GitHub"]
    GIT --->|"Коммит/событие<br/>push, pull request, tag"| CI["Система CI<br/>GitHub Actions"]
    CI --->|"Сборка и проверка<br/>ruff + pytest + docker build"| BUILD["Собранное приложение<br/>Docker-образ"]
    BUILD --->|"Публикация версии<br/>docker push"| REG["Хранилище артефактов<br/>GHCR"]
    REG --->|"Получение версии<br/>docker compose pull"| ENV["Среда запуска<br/>Docker Compose"]
    ENV ---> APP["REST-сервис бронирования<br/>FastAPI :8000"]

    classDef source fill:#e8f0fe,stroke:#4776b4,color:#17365d
    classDef process fill:#fff2cc,stroke:#bf9000,color:#594300
    classDef artifact fill:#e2f0d9,stroke:#548235,color:#274e13
    classDef runtime fill:#fce4d6,stroke:#c65911,color:#783f04
    class DEV,GIT source
    class CI,BUILD process
    class REG artifact
    class ENV,APP runtime
```

## Потоки данных и артефакты

```mermaid
flowchart
    DEV["Разработчик"]
    GIT["Git-репозиторий<br/>GitHub"]
    CI["Система CI: сборка и тесты<br/>GitHub Actions, job test"]
    REPORT["Результат проверки<br/>reports/junit.xml"]
    ART["Артефакт приложения<br/>Docker-образ"]
    REG["Хранилище артефактов<br/>ghcr.io"]
    CFG["Конфигурация развертывания<br/>.env, docker-compose.yml"]
    CD["Этап доставки/развертывания<br/>job deploy, deploy.ps1"]
    ENV["Среда запуска<br/>Docker Compose"]

    DEV --->|"Изменение кода"| GIT
    GIT --->|"Исходный код и версия<br/>commit SHA, tag vX.Y.Z"| CI
    CI --->|"Отчёт о тестах"| REPORT
    CI --->|"Проверенный артефакт<br/>job build"| ART
    ART --->|"Публикация версии<br/>теги X.Y.Z, sha-xxxxxxx, latest"| REG
    REG --->|"Образ по версии"| CD
    CFG --->|"Параметры запуска<br/>DATABASE_URL, OTEL_*, IMAGE_TAG"| CD
    CD --->|"Развертывание"| ENV

    classDef source fill:#e8f0fe,stroke:#4776b4,color:#17365d
    classDef process fill:#fff2cc,stroke:#bf9000,color:#594300
    classDef artifact fill:#e2f0d9,stroke:#548235,color:#274e13
    classDef config fill:#fce4d6,stroke:#c65911,color:#783f04
    class DEV,GIT source
    class CI,CD process
    class ART,REG,REPORT artifact
    class CFG,ENV config
```

## Версионирование и условия выпуска

```mermaid
flowchart
    A["Изменение в git<br/>push в main или tag vX.Y.Z"] ---> B["Сборка<br/>pip install"]
    B ---> C{"Сборка успешна?"}
    C -- Нет --> F["Зафиксировать ошибку<br/>красный запуск в Actions"]
    F ---> G["Исправить код или конфигурацию"]
    G ---> A
    C -- Да --> D["Автоматические тесты<br/>ruff + pytest"]
    D --> E{"Тесты пройдены?"}
    E -- Нет --> H["Сохранить отчёт об ошибках<br/>артефакт test-report"]
    H --> G
    E -- Да --> I["Создание версионированного артефакта<br/>docker build, APP_VERSION"]
    I --> J["Опубликовать в хранилище<br/>ghcr.io"]
    J --> K{"Развертывание разрешено?<br/>environment production"}
    K -- Нет --> L["Ожидание согласования<br/>Review deployments"]
    L -- Одобрено --> M
    K -- Да --> M["Развернуть на целевой среде<br/>проверка /health и /version"]

    classDef decision fill:#fff2cc,stroke:#bf9000,color:#594300
    classDef error fill:#f4cccc,stroke:#cc0000,color:#660000
    classDef success fill:#d9ead3,stroke:#38761d,color:#274e13
    class C,E,K decision
    class F,G,H error
    class I,J,M success
```

### Правила версий

| Событие | Теги образа в GHCR | Что вернёт `GET /version` |
|---|---|---|
| `git push` в `main` | `sha-<7 символов коммита>`, `latest` | `sha-xxxxxxx` |
| `git tag v0.1.0` + `git push --tags` | `0.1.0`, `sha-xxxxxxx` | `0.1.0` |
| Pull request | образ не собирается, только тесты | — |

Версия «зашивается» в образ при сборке (`--build-arg APP_VERSION`), поэтому по ответу `/version` всегда видно, какой именно артефакт запущен.

## Наблюдаемость и обратная связь

```mermaid
flowchart
   GIT["Git-репозиторий<br/>GitHub"] --> CI["Система CI: сборка и тесты<br/>GitHub Actions"]
   CI --> REG["Хранилище артефактов<br/>GHCR"]
   REG --> DEPLOY["Развертывание<br/>docker compose"]
   DEPLOY --> APP["REST-сервис бронирования"]

   APP --> LOGS["Логи<br/>logging → OTLP"]
   APP --> METRICS["Метрики<br/>HTTP + bookings_created, booking_errors"]
   APP --> TRACES["Трассировка<br/>FastAPI + SQL-запросы"]

   LOGS --> OBS["Система наблюдаемости<br/>grafana/otel-lgtm: Loki, Prometheus, Tempo"]
   METRICS --> OBS
   TRACES --> OBS

   OBS --> ALERT["Обнаружение отклонения<br/>алерт Grafana: ответы 5xx"]
   ALERT --> ISSUE["Задача на расследование<br/>GitHub Issue"]
   ISSUE --> GIT

    classDef process fill:#fff2cc,stroke:#bf9000,color:#594300
    classDef runtime fill:#fce4d6,stroke:#c65911,color:#783f04
    classDef observe fill:#d9ead3,stroke:#38761d,color:#274e13
    class CI,DEPLOY process
    class APP runtime
    class LOGS,METRICS,TRACES,OBS,ALERT observe
```

### Что собирается

| Сигнал | Откуда | Примеры | Где смотреть |
|---|---|---|---|
| Логи | логгер `booking` в `app/main.py` | `booking created id=3 room=1`, `booking conflict ...`, `unhandled error ...` | Explore → Loki, `{service_name="booking-service"}` |
| Метрики HTTP | автоинструментация FastAPI | `http_server_duration_milliseconds_*`, `http_server_active_requests` | Explore → Prometheus |
| Бизнес-метрики | счётчики в `app/main.py` | `bookings_created_total`, `booking_conflicts_total`, `booking_errors_total` | Explore → Prometheus |
| Трассировки | автоинструментация FastAPI и SQLAlchemy | span `POST /bookings` → вложенные `SELECT`, `INSERT` | Explore → Tempo, Service Name = `booking-service` |

Точные имена метрик в Prometheus видно в Grafana: Explore → Prometheus → Metrics browser (поиск по `booking`).

### Правило алерта

- Запрос: `sum(increase(booking_errors_total[1m])) or vector(0)`
- Условие: значение больше 0, проверка каждые 30 секунд.
- Проверка: `.\scripts\traffic.ps1 -Errors 5` — через 30–60 секунд правило переходит в состояние **Firing**.
- Реакция: создать Issue по шаблону «Инцидент / отклонение», исправить, выпустить новую версию.

## Разделение по этапам разработки и сопровождения

```mermaid
flowchart TB
  subgraph STAGE_DEV["1. Разработка"]
    DEV1["Разработчик<br/>VS Code"]
    GIT["Git-репозиторий<br/>GitHub"]
    DEV1 -->|"Изменение кода"| GIT
  end

  subgraph DELIVERY["2. Сборка и доставка — GitHub Actions"]
    CI["CI: сборка и тесты<br/>job test"]
    CHECK{"Проверки пройдены?"}
    REG["Хранилище артефактов<br/>GHCR"]
    DEPLOY["Развёртывание<br/>job deploy + согласование"]
    GIT -->|"Версия исходного кода"| CI
    CI --> CHECK
    CHECK -->|"Нет"| FAIL["Отчёт об ошибке<br/>test-report"]
    FAIL --> DEV1
    CHECK -->|"Да"| REG
    REG -->|"Конкретная версия"| DEPLOY
  end

  subgraph RUN["3. Эксплуатация — Docker Compose"]
    APP["REST-сервис бронирования<br/>FastAPI"]
    DB[("База данных<br/>PostgreSQL")]
    APP --> DB
    DEPLOY --> APP
  end

  subgraph STAGE_OBS["4. Наблюдаемость — Grafana LGTM"]
    LOG["Логи<br/>Loki"]
    MET["Метрики<br/>Prometheus"]
    TRACE["Трассировки<br/>Tempo"]
    ALERT["Анализ отклонений<br/>Grafana Alerting"]
    APP --> LOG
    APP --> MET
    APP --> TRACE
    LOG --> ALERT
    MET --> ALERT
    TRACE --> ALERT
  end

  ALERT -->|"Инцидент / задача<br/>GitHub Issue"| DEV1

  classDef dev fill:#e8f0fe,stroke:#4776b4,color:#17365d
  classDef delivery fill:#fff2cc,stroke:#bf9000,color:#594300
  classDef runtime fill:#d9ead3,stroke:#38761d,color:#274e13
  classDef monitoring fill:#fce4d6,stroke:#c65911,color:#783f04
  class DEV1,GIT dev
  class CI,CHECK,REG,DEPLOY,FAIL delivery
  class APP,DB runtime
  class LOG,MET,TRACE,ALERT monitoring
```

## Конфигурация развертывания

| Переменная | Значение по умолчанию | Назначение |
|---|---|---|
| `BOOKING_IMAGE` | `booking-service` | имя образа; после настройки CI — `ghcr.io/<ваш-логин>/booking-service` |
| `IMAGE_TAG` | `local` | версия образа, которую запускаем |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `booking` | доступ к базе |
| `DATABASE_URL` | собирается из переменных выше | строка подключения сервиса к базе |
| `OTEL_SERVICE_NAME` | `booking-service` | имя сервиса в Grafana |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://lgtm:4318` | куда отправлять логи, метрики и трассировки |
| `APP_VERSION` | задаётся при сборке в CI | версия, которую показывает `/version` |

## Хранение данных и секреты

- Данные PostgreSQL — том `pgdata`, данные наблюдаемости — том `lgtm-data`. `docker compose down` их сохраняет, `docker compose down -v` удаляет.
- Файл `.env` не попадает в Git (`.gitignore`); в репозитории только шаблон `.env.example`.
- CI публикует образы с помощью встроенного `GITHUB_TOKEN`; личные пароли и токены в репозиторий не кладутся.
- `grafana/otel-lgtm` предназначен для разработки и учебных задач, не для продакшена.
