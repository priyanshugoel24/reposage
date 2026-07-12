from datetime import datetime, timezone
import os
from pathlib import Path

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DB_PATH = Path(os.getenv("REPOSAGE_DATA_DIR", ".")) / "reposage.db"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class Repo(Base):
    __tablename__ = "repos"
    __table_args__ = (UniqueConstraint("user_id", "repo_name", name="uq_repo_user_reponame"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    repo_name: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str] = mapped_column(String, nullable=False)
    github_url: Mapped[str | None] = mapped_column(String, nullable=True)
    files_processed: Mapped[int] = mapped_column(Integer, nullable=False)
    chunks_created: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str | None] = mapped_column(String, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


# SQLite file, matching the REPOSAGE_DATA_DIR pattern used by vectorstore.py and call_graph.py.
# No migration framework yet — create_all() handles new tables; _add_missing_columns
# below is a minimal stopgap for adding columns to a table that already exists on disk.
engine = create_engine(f"sqlite:///{DB_PATH}")
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def _add_missing_columns() -> None:
    with engine.begin() as conn:
        existing_columns = {
            row[1] for row in conn.execute(text("PRAGMA table_info(repos)")).fetchall()
        }
        if "language" not in existing_columns:
            conn.execute(text("ALTER TABLE repos ADD COLUMN language VARCHAR"))


def init_db() -> None:
    Base.metadata.create_all(engine)
    _add_missing_columns()
