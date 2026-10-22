# Finance Assistant — Backend

Backend персонального финансового помощника (MVP).

Помогает вести личный финансовый учёт (доходы, расходы, переводы между своими
счетами) и автоматически рассчитывает **доступную сумму** — сколько денег
пользователь действительно может потратить с учётом остатков на счетах,
предстоящих платежей и финансового резерва.

## Стек

- Python 3.12+
- FastAPI, Uvicorn
- PostgreSQL 14+
- SQLAlchemy 2.x (синхронный режим), Alembic
- Pydantic 2.x, pydantic-settings
- Poetry (управление зависимостями)
- Argon2id (хеширование паролей), PyJWT (JWT в HttpOnly cookie)
- Ruff (линтинг и форматирование), Pytest (тесты)

## Формула доступной суммы

```
total_balance           = SUM(balance всех счетов пользователя)
upcoming_expenses_total = SUM(amount всех pending planned_expenses пользователя)
reserve_amount          = размер финансового резерва
available_amount        = total_balance − upcoming_expenses_total − reserve_amount
```

Доходы, расходы и переводы уже отражены в балансах счетов и в формулу
напрямую не входят. Переводы не меняют `total_balance`.

Все деньги считаются в `Decimal` (в Python) и `NUMERIC(12,2)` (в PostgreSQL).
В JSON возвращаются строками с двумя знаками после запятой: `"1250.00"`.
Валюта MVP — RUB.

## Требования к окружению

- Python 3.12+
- Poetry 2.x
- PostgreSQL (локально)
- ОС: Linux, macOS, Windows 10/11 (PowerShell)

## Установка

### 1. Клонировать репозиторий и установить зависимости

```powershell
git clone <repo-url> finance-assistant
cd finance-assistant
poetry install
```

### 2. Создать роль и базу в PostgreSQL

Через **psql** (или pgAdmin — см. ниже):

```powershell
psql -U postgres -c "CREATE ROLE finance_user WITH LOGIN PASSWORD 'strong_password_here';"
psql -U postgres -c "CREATE DATABASE finance_assistant OWNER finance_user;"
psql -U postgres -d finance_assistant -c "ALTER SCHEMA public OWNER TO finance_user;"
```

`ALTER SCHEMA public OWNER` нужен на PostgreSQL 15+: начиная с этой версии
схема `public` по умолчанию не даёт `CREATE` не-владельцу базы.

**Через pgAdmin:**

1. `Login/Group Roles` → `Create` → `Login/Group Role…`
   - Name: `finance_user`, Password: сильный пароль, Can login: **Yes**.
2. `Databases` → `Create` → `Database…`
   - Database: `finance_assistant`, Owner: `finance_user`.
3. Правой на `finance_assistant` → `Query Tool` → `ALTER SCHEMA public OWNER TO finance_user;`.

### 3. Настроить `.env`

```powershell
Copy-Item .env.example .env
```

Сгенерировать секрет для JWT:

```powershell
poetry run python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Отредактировать `.env`:

- `DB_PASS` — пароль роли `finance_user` из шага 2.
- `JWT_SECRET_KEY` — вставить сгенерированный секрет.
- `CORS_ORIGINS` — origin фронтенда через запятую, например
  `http://localhost:3000`. Для Swagger UI по умолчанию ничего добавлять не надо:
  self-origin разрешён автоматически.

`.env` **не коммитится** (уже в `.gitignore`). Если обязательные переменные
(`DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME`, `JWT_SECRET_KEY`) не заданы,
приложение не запустится — это осознанный fail-fast.

### 4. Применить миграции

```powershell
poetry run alembic upgrade head
```

Создаст 6 таблиц (`users`, `accounts`, `categories`, `operations`,
`planned_expenses`, `reserves`) и посеет 10 предустановленных категорий.

Структура БД меняется **только** через Alembic. `Base.metadata.create_all()`
в приложении не вызывается.

### 5. Запустить

```powershell
poetry run uvicorn app.main:app --reload
```

- Swagger UI: <http://127.0.0.1:8000/docs>
- Health-check: <http://127.0.0.1:8000/api/health>

В логах появится `Database connection OK (env=development)`.

## Cookie-аутентификация

JWT access token передаётся **исключительно** через HttpOnly cookie `access_token`
(`SameSite=Lax`, `Path=/`, `Secure` — по конфигурации для production).
JWT **не** возвращается в JSON. Refresh-токенов и отзыва токенов нет (MVP).

Для ручной проверки в Swagger UI:

1. Открыть <http://127.0.0.1:8000/docs> (именно `127.0.0.1`, не `localhost` —
   CSRF-middleware сверяет Origin с URL приложения).
2. `POST /api/auth/register` — зарегистрировать пользователя.
3. `POST /api/auth/login` — войти. Cookie установится в браузере.
4. Любой защищённый эндпоинт (`GET /api/accounts`, `GET /api/dashboard`, …)
   работает без дополнительной настройки: Swagger отправляет cookie автоматически.

В DevTools → Application → Cookies → `http://127.0.0.1:8000` видно `access_token`
с флагом `HttpOnly`.

Отдельного «Authorize» в Swagger нет: cookie-auth не описывается через
`SecurityScheme` без BFF, а мы его не используем.

## Тесты

Тесты запускаются на **отдельной** базе `finance_assistant_test`. Она
создаётся автоматически при первом запуске (если роль `finance_user` имеет
право `CREATEDB` — в инструкции выше её владелец именно `finance_user`,
поэтому по умолчанию это так). Миграции накатываются автоматически,
данные очищаются перед каждым тестом.

```powershell
poetry run pytest -v
```

Ожидается ~112 тестов, все `PASSED`.

Запуск конкретного файла:

```powershell
poetry run pytest -v tests/test_operations.py
```

## Docker (опционально)

Если не хотите ставить PostgreSQL и Poetry локально.

### 1. Подготовить `.env`

```powershell
Copy-Item .env.example .env
```

Отредактируйте:
- `DB_PASS` — пароль PostgreSQL (используется и в контейнере `db`).
- `JWT_SECRET_KEY` — сгенерированный секрет.

`DB_HOST` в `.env` для Docker не важен: `docker-compose.yml` переопределяет его
на `db` (имя сервиса во внутренней сети Compose). Тот же `.env` продолжает
работать и для локального запуска с `uvicorn` — там `DB_HOST=localhost`.

### 2. Запустить

```powershell
docker compose up --build
```

- Swagger UI: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/api/health>
- PostgreSQL доступен с хоста на `localhost:5433` (для pgAdmin / psql).

Миграции Alembic применяются автоматически при старте контейнера `app`.

### 3. Остановка

```powershell
docker compose down           # остановить контейнеры, данные БД сохраняются
docker compose down -v        # остановить + удалить volume с данными БД
```

### Полезные команды

```powershell
docker compose logs -f app    # логи приложения
docker compose logs -f db     # логи PostgreSQL
docker compose exec db psql -U finance_user -d finance_assistant
docker compose exec app alembic current
```

Порты можно переопределить через переменные окружения хоста:

```powershell
$env:APP_PORT=9000; $env:DB_PORT_FORWARD=5532; docker compose up
```


## Линтер и форматирование

```powershell
poetry run ruff check .
poetry run ruff format --check .
```

Исправить автоформат:

```powershell
poetry run ruff format .
```

## Структура проекта

```
finance-assistant/
├── alembic.ini
├── pyproject.toml
├── poetry.lock
├── .env.example
├── README.md
│
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 0001_initial_schema.py
│       └── 0002_seed_categories.py
│
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py          # pydantic-settings
│   │   ├── security.py        # Argon2id, JWT
│   │   ├── cookies.py         # set/clear access_token
│   │   ├── csrf.py            # Origin/Referer middleware
│   │   ├── exceptions.py      # AppError + подклассы
│   │   ├── error_handlers.py  # единый формат ошибок
│   │   └── types.py           # Money, PositiveMoney, NonNegativeMoney
│   ├── db/
│   │   ├── base.py            # Base
│   │   └── session.py         # engine, sessionmaker, get_session
│   └── modules/
│       ├── auth/              # register/login/me/logout
│       ├── categories/        # GET /api/categories (read-only)
│       ├── accounts/          # CRUD счетов
│       ├── operations/        # income/expense/transfer + история
│       ├── planned_expenses/  # CRUD + pay/unpay
│       ├── reserve/           # GET/PUT /api/reserve
│       └── dashboard/         # GET /api/dashboard
│
└── tests/
    ├── conftest.py
    ├── test_health.py
    ├── test_auth.py
    ├── test_accounts.py
    ├── test_categories.py
    ├── test_operations.py
    ├── test_planned_expenses.py
    ├── test_reserve.py
    ├── test_dashboard.py
    └── test_database.py
```

Каждый модуль использует однотипную структуру: `router.py`, `schemas.py`,
`models.py`, `repository.py`, `service.py`. HTTP-логика — только в роутере,
SQL — только в репозитории, бизнес-правила — только в сервисе.

## Conventional Commits

```
feat: add operations module
fix: correct available amount calculation
refactor: extract dashboard service
docs: describe cookie authentication
test: cover reserve calculations
chore: initialize backend project
```

Коммиты создаются после завершённого логического этапа, когда код запускается
и результат проверки подтверждён.

## Границы MVP

В MVP входит: регистрация и вход по email/паролю, JWT в HttpOnly cookie,
CRUD счетов, операции (income/expense/transfer), planned_expenses с оплатой
и возвратом, финансовый резерв, Dashboard с расчётом доступной суммы,
предустановленные категории (10 штук), миграции Alembic, единый формат
ошибок, Swagger UI, тесты.

**Не входит** (не реализовывать без отдельного согласования): синхронизация
с банковскими API, мультивалютность, пользовательские категории, бюджеты
и прогнозирование, несколько целей/резервов, push- и email-уведомления,
refresh-токены, CSRF-токены (используется Origin/Referer), Docker на
начальном этапе.
