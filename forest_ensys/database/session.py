from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from forest_ensys.core import settings

engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    execution_options={"isolation_level": "AUTOCOMMIT"},
    pool_pre_ping=True,
    poolclass=StaticPool,
)
SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, expire_on_commit=False, bind=engine
)
