from datetime import datetime, timezone

from sqlalchemy import select

from reposage.db.models import Repo, SessionLocal


def github_url_for(source: str) -> str | None:
    if not (source.startswith("http://github.com/") or source.startswith("https://github.com/")):
        return None

    url = source.rstrip("/")
    if url.endswith(".git"):
        url = url[: -len(".git")]
    return url


def save_summary(
    user_id: int,
    repo_name: str,
    source: str,
    summary: str,
    files_processed: int,
    chunks_created: int,
    language: str | None = None,
) -> None:
    with SessionLocal() as session:
        existing = session.scalar(
            select(Repo).where(Repo.user_id == user_id, Repo.repo_name == repo_name)
        )
        if existing is not None:
            existing.source_url = source
            existing.github_url = github_url_for(source)
            existing.summary = summary
            existing.files_processed = files_processed
            existing.chunks_created = chunks_created
            existing.language = language
            existing.tour_steps = None
            existing.ingested_at = datetime.now(timezone.utc)
        else:
            session.add(
                Repo(
                    user_id=user_id,
                    repo_name=repo_name,
                    source_url=source,
                    github_url=github_url_for(source),
                    summary=summary,
                    files_processed=files_processed,
                    chunks_created=chunks_created,
                    language=language,
                )
            )
        session.commit()


def get_summary(user_id: int, repo_name: str) -> dict | None:
    with SessionLocal() as session:
        repo = session.scalar(
            select(Repo).where(Repo.user_id == user_id, Repo.repo_name == repo_name)
        )
        if repo is None:
            return None
        return {
            "source": repo.source_url,
            "summary": repo.summary,
            "github_url": repo.github_url,
            "files_processed": repo.files_processed,
            "chunks_created": repo.chunks_created,
            "language": repo.language,
            "ingested_at": repo.ingested_at,
        }


def list_repos(user_id: int) -> list[dict]:
    with SessionLocal() as session:
        rows = session.scalars(select(Repo).where(Repo.user_id == user_id))
        return [
            {
                "repo_name": repo.repo_name,
                "summary": repo.summary,
                "language": repo.language,
                "files_processed": repo.files_processed,
                "chunks_created": repo.chunks_created,
                "ingested_at": repo.ingested_at,
                "source_url": repo.source_url,
            }
            for repo in rows
        ]


def get_tour_steps(user_id: int, repo_name: str) -> str | None:
    with SessionLocal() as session:
        repo = session.scalar(
            select(Repo).where(Repo.user_id == user_id, Repo.repo_name == repo_name)
        )
        return repo.tour_steps if repo is not None else None


def save_tour_steps(user_id: int, repo_name: str, tour_steps: str) -> None:
    with SessionLocal() as session:
        repo = session.scalar(
            select(Repo).where(Repo.user_id == user_id, Repo.repo_name == repo_name)
        )
        if repo is None:
            return
        repo.tour_steps = tour_steps
        session.commit()


def delete_repo(user_id: int, repo_name: str) -> bool:
    """Delete the DB row for this repo. Returns False if not found/not owned by user_id."""
    with SessionLocal() as session:
        existing = session.scalar(
            select(Repo).where(Repo.user_id == user_id, Repo.repo_name == repo_name)
        )
        if existing is None:
            return False
        session.delete(existing)
        session.commit()
        return True
