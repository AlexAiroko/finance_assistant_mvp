from logging.config import fileConfig

from alembic import context

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine

# Импортируем модели, чтобы все они зарегистрировались в Base.metadata.
# Порядок импортов не важен: SQLAlchemy 2.x сам разрешает FK-зависимости
# при построении метаданных.
from app.modules.accounts import models as _accounts_models  # noqa: F401
from app.modules.auth import models as _auth_models  # noqa: F401
from app.modules.categories import models as _categories_models  # noqa: F401
from app.modules.operations import models as _operations_models  # noqa: F401
from app.modules.planned_expenses import models as _planned_expenses_models  # noqa: F401
from app.modules.reserve import models as _reserve_models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Для offline-режима (alembic upgrade --sql). Знак "%" в пароле Alembic
# использует как интерполяцию, поэтому экранируем.
_settings = get_settings()
config.set_main_option(
    "sqlalchemy.url",
    _settings.database_url.render_as_string(hide_password=False).replace("%", "%%"),
)

target_metadata = Base.metadata

# Индекс с DESC-сортировкой создан вручную (op.execute). Alembic плохо
# сравнивает expression-индексы, поэтому исключаем его из autogenerate-diff.
_IGNORED_INDEXES = {"ix_operations_user_occurred"}


def _include_object(obj, name, type_, reflected, compare_to):
    return not (type_ == "index" and name in _IGNORED_INDEXES)


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_object=_include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
