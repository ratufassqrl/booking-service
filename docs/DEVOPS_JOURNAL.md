# Журнал DevOps: REST-сервис бронирования

**Автор:** <!-- ФИО, группа -->
**Репозиторий:** https://github.com/<ваш-логин>/booking-service
**Период работ:** <!-- даты -->

Журнал фиксирует, что сделано на каждом этапе, какими командами и чем это подтверждается. Строки «Результат» и скриншоты заполняются по мере выполнения. Описание компонентов — в `INFRASTRUCTURE.md`.

## Хронология

| Дата | Что сделано | Результат / ссылка |
|---|---|---|
| <!-- дд.мм --> | Установлены WSL 2, Docker Desktop, Git, Python 3.13, VS Code | `docker version`, `git --version` выполняются без ошибок |
| | Создан репозиторий на GitHub, первый push в `main` | ссылка на коммит |
| | Сервис запущен локально через Docker Compose | http://localhost:8000/docs открывается |
| | Настроен CI: тесты, сборка образа, публикация в GHCR | ссылка на зелёный запуск Actions |
| | Проверено падение CI на сломанном тесте | ссылка на красный запуск |
| | Выпущена версия `v0.1.0` | ссылка на пакет в GHCR |
| | Настроено согласование развертывания (environment `production`) | скриншот «Review deployments» |
| | Версия `0.1.0` развернута локально из GHCR | вывод `scripts/deploy.ps1` |
| | Проверены логи, метрики, трассировки в Grafana | скриншоты Explore |
| | Сработал алерт, заведена задача, выпущено исправление | ссылка на Issue и новую версию |

---

## 1. Основной поток разработки

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

**Как проверено**

```powershell
git add .
git commit -m "feat: booking service"
git push origin main
```

- Результат: в GitHub → Actions появился запуск **CI/CD**, jobs `test` и `build` зелёные.
- Ссылка на запуск: <!-- вставить -->
- Скриншот: <!-- вставить -->

## 2. Потоки данных и артефакты

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

**Как проверено**

| Поток | Подтверждение |
|---|---|
| Исходный код и версия → CI | в запуске Actions виден SHA коммита |
| CI → отчёт о тестах | в запуске скачивается артефакт `test-report` (`junit.xml`) |
| CI → проверенный артефакт → хранилище | GitHub → профиль → **Packages** → `booking-service`, теги `sha-…`, `latest` |
| Конфигурация → развертывание | `.env` с `BOOKING_IMAGE` и `IMAGE_TAG` |
| Развертывание → среда запуска | `docker compose ps` показывает `app`, `db`, `lgtm` в состоянии running |

Результат `docker compose ps`:

```text
<!-- вставить вывод -->
```

## 3. Версионирование и условия выпуска

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

**Как проверено**

1. Ветка «сборка/тесты не прошли»: в `tests/test_api.py` временно заменить `assert room["id"] == 1` на `assert room["id"] == 2`, закоммитить и отправить.
   - Результат: job `test` красный, job `build` не запускался, отчёт `test-report` сохранён.
   - Ссылка: <!-- вставить -->
2. Исправить тест и отправить снова — запуск зелёный.
3. Выпуск версии:
   ```powershell
   git tag v0.1.0
   git push origin v0.1.0
   ```
   - Результат: в GHCR появился тег `0.1.0`.
4. Ветка «развертывание не разрешено»: job `deploy` ждёт в статусе **Waiting**, пока не нажата кнопка **Review deployments → Approve and deploy**.
   - Скриншот ожидания: <!-- вставить -->
   - После одобрения: в Summary запуска строка «Развернута версия 0.1.0».

## 4. Наблюдаемость и обратная связь

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

**Как проверено**

```powershell
.\scripts\deploy.ps1 -Image ghcr.io/<ваш-логин>/booking-service -Version 0.1.0
.\scripts\traffic.ps1
.\scripts\traffic.ps1 -Errors 5
```

| Проверка | Где | Результат |
|---|---|---|
| Логи | Grafana → Explore → Loki, `{service_name="booking-service"}` | <!-- скриншот --> |
| Метрики | Explore → Prometheus, `bookings_created_total` | <!-- скриншот --> |
| Трассировка | Explore → Tempo → Search, Service Name `booking-service`, span `POST /bookings` | <!-- скриншот --> |
| Алерт | Alerting → Alert rules → «Booking: ответы 5xx» в состоянии Firing | <!-- скриншот --> |
| Задача | GitHub → Issues, шаблон «Инцидент / отклонение» | <!-- ссылка --> |

## 5. Разделение по этапам разработки и сопровождения

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

| Этап | Инструменты | Ответственный | Состояние |
|---|---|---|---|
| 1. Разработка | VS Code, Git, GitHub | <!-- ФИО --> | <!-- готово / в работе --> |
| 2. Сборка и доставка | GitHub Actions, Docker, GHCR, Environment `production` | | |
| 3. Эксплуатация | Docker Compose, PostgreSQL | | |
| 4. Наблюдаемость | OpenTelemetry, Grafana, Loki, Prometheus, Tempo | | |

## Проблемы и решения

| Проблема | Причина | Решение |
|---|---|---|
| <!-- пример: Docker Desktop не стартует --> | <!-- выключена виртуализация в BIOS --> | <!-- включил Intel VT-x / AMD-V --> |

## Выводы

<!-- 3–5 предложений: что получилось, что автоматизировано, что можно улучшить
     (например: развертывание на сервер вместо ноутбука, дашборд в Grafana, уведомления в Telegram). -->
