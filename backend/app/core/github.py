"""GitHub stars / release-download sync shared by the scheduler job and the Dev Tracking router.

GitHub is read with httpx. Unauthenticated calls work for public repos (60 requests/hour
per IP); ``GITHUB_TOKEN`` lifts the limit to 5000/hour and is required for private repos
(fine-grained PAT with Metadata read + Contents read). The token is never logged.
"""
import asyncio
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from traceback import format_exc
from typing import TYPE_CHECKING, Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.log_module import system_log
from app.models.dev_tracking import GithubRepo, ProjectDownload

if TYPE_CHECKING:
    from loguru import Logger

GITHUB_API = "https://api.github.com"
GITHUB_API_VERSION = "2026-03-10"
GITHUB_PLATFORM = "github"
_USER_AGENT = "CarzinomaxERP-github-sync/0.1"
_TIMEOUT_SECONDS = 10.0
_PER_PAGE = 100
_MAX_RELEASE_PAGES = 50
_GITHUB_URL_PREFIX = re.compile(r"^(?:https?://)?(?:www\.)?github\.com/", re.IGNORECASE)
_FULL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}$")
# One sync at a time per process: the scheduler job and the manual endpoint must never
# upsert the same daily snapshot concurrently (dev_project_downloads has no unique key).
_sync_lock = asyncio.Lock()


class GithubApiError(Exception):
    """A GitHub API call failed; the message is safe to store in ``GithubRepo.last_error``."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class GithubRepoStats:
    """Numbers fetched from GitHub for one repository."""

    full_name: str
    star_count: int
    download_count: int


@dataclass
class GithubSyncResult:
    """Outcome of one sync run; both lists hold ``GithubRepo.to_dict()`` rows."""

    synced: list[dict[str, Any]] = field(default_factory=list)
    failed: list[dict[str, Any]] = field(default_factory=list)


def parse_repo_full_name(value: str) -> str:
    """Normalise a repository reference to ``owner/name``.

    Args:
        value: ``owner/name`` or a ``https://github.com/owner/name[.git]`` URL.

    Returns:
        The ``owner/name`` string.

    Raises:
        ValueError: If the value is not a GitHub repository reference.
    """
    cleaned = _GITHUB_URL_PREFIX.sub("", value.strip()).strip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]
    repo_name = cleaned.rsplit("/", 1)[-1]
    if not _FULL_NAME_RE.fullmatch(cleaned) or repo_name in {".", ".."}:
        raise ValueError(f"'{value}' is not a GitHub repository in the form owner/name")
    return cleaned


def _headers() -> dict[str, str]:
    """Build the request headers; the token is attached only when configured."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
        "User-Agent": _USER_AGENT,
    }
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
    return headers


def _github_message(response: httpx.Response) -> str:
    """Return GitHub's JSON ``message`` for an error response, or the start of the body."""
    try:
        message = response.json().get("message")
    except (ValueError, AttributeError):
        message = None
    return str(message) if message else response.text[:200]


def _rate_limit_reset(response: httpx.Response) -> str:
    """Return the ``x-ratelimit-reset`` header as an ISO UTC timestamp, or ``unknown``."""
    try:
        reset_epoch = int(response.headers["x-ratelimit-reset"])
    except (KeyError, ValueError):
        return "unknown"
    return datetime.fromtimestamp(reset_epoch, tz=timezone.utc).isoformat()


def _api_error(response: httpx.Response, full_name: str) -> GithubApiError:
    """Map a non-2xx GitHub response to a ``GithubApiError`` with an actionable message."""
    code = response.status_code
    detail = _github_message(response)
    if code == 404:
        message = f"{full_name}: not found, or private and GITHUB_TOKEN is missing or lacks access"
    elif code == 401:
        message = f"{full_name}: GitHub rejected GITHUB_TOKEN ({detail})"
    elif code in (403, 429) and response.headers.get("x-ratelimit-remaining") == "0":
        message = f"{full_name}: GitHub rate limit exhausted, resets at {_rate_limit_reset(response)}"
    elif code == 403:
        message = f"{full_name}: GitHub refused access ({detail})"
    elif code == 410:
        message = f"{full_name}: GitHub API version {GITHUB_API_VERSION} is no longer supported"
    else:
        message = f"{full_name}: GitHub API error {code} ({detail})"
    return GithubApiError(message, code)


async def _get_json(client: httpx.AsyncClient, path: str, full_name: str,
                    params: dict[str, int] | None = None) -> Any:
    """GET a GitHub API path and return the decoded JSON body.

    Raises:
        GithubApiError: On transport errors, non-2xx responses or a non-JSON body.
    """
    try:
        response = await client.get(path, params=params)
    except httpx.HTTPError as err:
        raise GithubApiError(f"{full_name}: request failed ({err.__class__.__name__}: {err})") from err
    if not response.is_success:
        raise _api_error(response, full_name)
    try:
        return response.json()
    except ValueError as err:
        raise GithubApiError(f"{full_name}: GitHub returned a non-JSON body", response.status_code) from err


async def _fetch_download_total(client: httpx.AsyncClient, full_name: str) -> int:
    """Sum ``download_count`` over every asset of every published release (paginated)."""
    total = 0
    for page in range(1, _MAX_RELEASE_PAGES + 1):
        releases = await _get_json(client, f"/repos/{full_name}/releases", full_name,
                                   params={"per_page": _PER_PAGE, "page": page})
        if not isinstance(releases, list):
            raise GithubApiError(f"{full_name}: unexpected releases payload")
        for release in releases:
            total += sum(int(asset.get("download_count", 0)) for asset in release.get("assets", []))
        if len(releases) < _PER_PAGE:
            return total
    raise GithubApiError(f"{full_name}: more than {_MAX_RELEASE_PAGES * _PER_PAGE} releases, giving up")


async def fetch_repo_stats(client: httpx.AsyncClient, full_name: str) -> GithubRepoStats:
    """Fetch stars and release-asset downloads for one repository.

    Args:
        client: Client configured by ``sync_github_repos`` (base URL, headers, timeout).
        full_name: ``owner/name``.

    Returns:
        The fetched numbers.

    Raises:
        GithubApiError: If GitHub cannot be reached, refuses the request or answers oddly.
    """
    repo = await _get_json(client, f"/repos/{full_name}", full_name)
    try:
        star_count = int(repo["stargazers_count"])
    except (KeyError, TypeError, ValueError) as err:
        raise GithubApiError(f"{full_name}: repository payload has no stargazers_count") from err
    download_count = await _fetch_download_total(client, full_name)
    stats = GithubRepoStats(full_name=full_name, star_count=star_count, download_count=download_count)
    return stats


async def _load_repos(db: AsyncSession, repo_id: int | None) -> list[GithubRepo]:
    """Load every tracked repo, or only ``repo_id`` when given, ordered by id."""
    stmt = select(GithubRepo).order_by(GithubRepo.id)
    if repo_id is not None:
        stmt = stmt.where(GithubRepo.id == repo_id)
    repos = list((await db.scalars(stmt)).all())
    return repos


async def _sync_one(client: httpx.AsyncClient, repo: GithubRepo, now: datetime, log: "Logger") -> bool:
    """Refresh one repo in place; on failure keep the old numbers and set ``last_error``."""
    try:
        stats = await fetch_repo_stats(client, repo.full_name)
    except GithubApiError as err:
        repo.last_error = str(err)
        log.warning(f"GitHub sync {repo.full_name}: {err}")
        return False
    except Exception as err:
        repo.last_error = f"unexpected error: {err}"
        log.error(f"GitHub sync {repo.full_name} crashed: {format_exc()}")
        return False
    repo.star_count = stats.star_count
    repo.download_count = stats.download_count
    repo.last_synced_at = now
    repo.last_error = None
    log.info(f"GitHub sync {repo.full_name}: {stats.star_count} stars, {stats.download_count} downloads")
    return True


async def _project_totals(db: AsyncSession, project_ids: set[int]) -> list[tuple[int, int, int | None]]:
    """Latest-known totals per project over all of its repos (stale rows included)."""
    if not project_ids:
        return []
    stmt = (
        select(GithubRepo.project_id,
               func.coalesce(func.sum(GithubRepo.download_count), 0),
               func.sum(GithubRepo.star_count))
        .where(GithubRepo.project_id.in_(project_ids))
        .group_by(GithubRepo.project_id)
    )
    rows = (await db.execute(stmt)).all()
    totals = [(int(project_id), int(downloads), None if stars is None else int(stars))
              for project_id, downloads, stars in rows]
    return totals


async def _upsert_daily_row(db: AsyncSession, project_id: int, day: date,
                            downloads: int, stars: int | None, log: "Logger") -> None:
    """Write the project's github totals for ``day`` into exactly one ``ProjectDownload`` row."""
    stmt = (
        select(ProjectDownload)
        .where(ProjectDownload.project_id == project_id,
               ProjectDownload.platform == GITHUB_PLATFORM,
               ProjectDownload.date == day)
        .order_by(ProjectDownload.id)
    )
    rows = (await db.scalars(stmt)).all()
    if len(rows) > 1:
        log.warning(f"GitHub sync: project {project_id} has {len(rows)} github snapshots for {day}; "
                    f"updating the oldest (id {rows[0].id})")
    if rows:
        rows[0].download_count = downloads
        rows[0].star_count = stars
        return
    db.add(ProjectDownload(project_id=project_id, date=day, platform=GITHUB_PLATFORM,
                           download_count=downloads, star_count=stars))


async def _store_results(db: AsyncSession, ok_repos: list[GithubRepo], day: date, log: "Logger") -> None:
    """Flush the repo updates, upsert the daily rows of the affected projects and commit."""
    try:
        await db.flush()  # SessionLocal has autoflush=False: the aggregate must see the new numbers
        totals = await _project_totals(db, {repo.project_id for repo in ok_repos})
        for project_id, downloads, stars in totals:
            await _upsert_daily_row(db, project_id, day, downloads, stars, log)
        await db.commit()
    except Exception:
        await db.rollback()
        raise


async def sync_github_repos(db: AsyncSession, repo_id: int | None = None,
                            log: "Logger | None" = None) -> GithubSyncResult:
    """Refresh tracked GitHub repos and upsert today's per-project snapshot (one run at a time).

    Args:
        db: Async session; committed on success, rolled back on an unexpected error.
        repo_id: Limit the run to one tracked repo; None syncs every repo.
        log: Logger to report to (``user_log`` from the router); defaults to ``system_log()``.

    Returns:
        The refreshed rows and the rows whose fetch failed (``last_error`` set, old numbers kept).
    """
    log = log or system_log()
    async with _sync_lock:
        repos = await _load_repos(db, repo_id)
        now = datetime.now(timezone.utc)
        ok_repos: list[GithubRepo] = []
        async with httpx.AsyncClient(base_url=GITHUB_API, headers=_headers(),
                                     timeout=_TIMEOUT_SECONDS, follow_redirects=True) as client:
            for repo in repos:
                if await _sync_one(client, repo, now, log):
                    ok_repos.append(repo)
        await _store_results(db, ok_repos, now.date(), log)
    result = GithubSyncResult(
        synced=[repo.to_dict() for repo in ok_repos],
        failed=[repo.to_dict() for repo in repos if repo not in ok_repos],
    )
    log.info(f"GitHub sync finished: {len(result.synced)} synced, {len(result.failed)} failed")
    return result
