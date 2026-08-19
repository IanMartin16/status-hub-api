from logging.config import fileConfig

from alembic import context

from app.db.base import Base

# Importamos el engine real de Status-Hub.
# Ajusta esta ruta al nombre real del archivo que me acabas de mostrar.
from app.db.session import engine

# Importar todos los modelos registrados en Base.metadata.
from app.models.service import Service
from app.models.service_status import ServiceStatusRecord
from app.models.service_check_event import ServiceCheckEvent
from app.models.maintenance_override import MaintenanceOverride
from app.models.service_health_daily import ServiceHealthDaily
from app.models.service_event import ServiceEvent

config = context.config


if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Ejecuta migraciones sin abrir una conexión activa.
    """

    url = engine.url.render_as_string(hide_password=False)

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Ejecuta migraciones usando el mismo engine que Status-Hub.
    """

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()