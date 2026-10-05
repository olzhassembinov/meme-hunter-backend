from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from .config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session

'''get_db is a FastAPI dependency — every route that needs the database declares db: AsyncSession = Depends(get_db) and gets its own session that closes automatically when the request finishes. You won't touch session lifecycle management again after this.'''