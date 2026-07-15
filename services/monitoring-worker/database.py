# Sets up the connection to the same Postgres database platform-api uses.
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

DATABASE_URL = "postgresql+asyncpg://nexus:nexus_dev_password@localhost:5433/nexus"

engine = create_async_engine(DATABASE_URL)
async_session = async_sessionmaker(engine, expire_on_commit=False)
