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
        }


def list_repos(user_id: int) -> list[str]:
    with SessionLocal() as session:
        rows = session.scalars(select(Repo.repo_name).where(Repo.user_id == user_id))
        return list(rows)
