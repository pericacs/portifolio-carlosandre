from alembic import context
from sqlalchemy import create_engine, pool, text
from app.config import get_settings
from app.models import metadata

url = get_settings().database_url
if context.is_offline_mode():
    context.configure(url=url, target_metadata=metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=metadata, compare_type=True)
        with context.begin_transaction():
            connection.execute(text("SET LOCAL lock_timeout = '10s'"))
            connection.execute(text("SET LOCAL statement_timeout = '5min'"))
            connection.execute(text("SELECT pg_advisory_xact_lock(734018230)"))
            context.run_migrations()
