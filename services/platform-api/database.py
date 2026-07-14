# Sets up the connection to Postgres and a way to have "conversations" with it.
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Connection string: postgresql+asyncpg://<user>:<password>@<host>:<port>/<database>
# These values match what we set in docker-compose.yml.
DATABASE_URL = "postgresql+asyncpg://nexus:nexus_dev_password@localhost:5433/nexus"

# The engine manages the actual connection(s) to Postgres.
engine = create_async_engine(DATABASE_URL, echo=True)

# A "session" is like a single conversation with the database - we open a
# fresh one per request and close it when we're done.
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
