"""
GitHub stars and release-download sync, shared by the scheduler job and POST /dev_tracking/github_sync
GitHub is read with httpx. Public repos work without a token (60 requests/hour per IP), `GITHUB_TOKEN` lifts the
limit to 5000/hour and is required for private repos (fine-grained PAT with Metadata + Contents read). The token is never logged.
"""
import asyncio
import re
from datetime import date, datetime, timezone
from traceback import format_exc

import httpx
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.log_module import system_log
from app.models.dev_tracking import GithubRepo, ProjectDownload

GITHUB_API = 'https://api.github.com'  # Base URL for all GitHub REST API requests
GITHUB_API_VERSION = '2026-03-10'  # API version sent in the X-GitHub-Api-Version request header
GITHUB_PLATFORM = 'github'  # Platform identifier stored in ProjectDownload rows
USER_AGENT = 'carzinomax-dev-github-sync/0.1'  # User-Agent header required by the GitHub REST API
TIMEOUT_SECONDS = 10.0  # Per-request HTTP timeout in seconds for the httpx client
PER_PAGE = 100  # Number of releases requested per page when paginating the releases endpoint
MAX_RELEASE_PAGES = 50  # Upper bound on release pages fetched per repo (caps at 5,000 releases)
GITHUB_URL_PREFIX = re.compile(r'^(?:https?://)?(?:www\.)?github\.com/', re.IGNORECASE)  # Strips leading github.com URL prefix when normalising repo inputs
FULL_NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}$')  # Validates normalized 'owner/name' repository identifiers
# One sync at a time per process, the scheduler job and the manual endpoint must not write the same daily snapshot together (dev_project_downloads has no unique key)
sync_lock = asyncio.Lock()  # In-process mutex preventing concurrent GitHub sync runs

system_log = system_log()  # Module-level system logger instance


class GithubRepoStats(BaseModel):
    full_name: str
    star_count: int
    download_count: int


class GithubSyncResult(BaseModel):
    synced: list[dict] = []  # GithubRepo.to_dict() rows refreshed in this run
    failed: list[dict] = []  # rows whose fetch failed, `last_error` set and old numbers kept


def parse_repo_full_name(value: str) -> str:
    """
    Normalise a repository reference to 'owner/name'
    Args:
        value: 'owner/name' or a github.com URL, with or without scheme, www and a trailing .git

    Returns:
        The 'owner/name' string

    Raises:
        ValueError: Not a GitHub repository reference
    """
    cleaned = GITHUB_URL_PREFIX.sub('', value.strip()).strip('/')
    if cleaned.endswith('.git'):
        cleaned = cleaned[:-4]
    repo_name = cleaned.rsplit('/', 1)[-1]
    if not FULL_NAME_RE.fullmatch(cleaned) or repo_name in ('.', '..'):
        raise ValueError(f"'{value}' is not a GitHub repository in the form owner/name")
    return cleaned


async def github_get(client: httpx.AsyncClient, path: str, params: dict | None = None) -> dict | list:
    """
    GET one GitHub API path and return the decoded JSON body
    Args:
        client: Client built by `sync_github_repos` (base URL, headers, timeout)
        path: API path, e.g. '/repos/owner/name'
        params: Query parameters, None if not needed

    Returns:
        Decoded JSON body, dict or list

    Raises:
        ValueError: GitHub could not be reached, refused the request or returned no JSON, the message is safe to store in `GithubRepo.last_error`
    """
    try:
        response = await client.get(path, params=params)
    except httpx.HTTPError as err:
        raise ValueError(f'request failed ({err.__class__.__name__}: {err})')
    if response.is_success:
        try:
            body = response.json()
        except ValueError:
            raise ValueError('GitHub returned a non-JSON body')
        return body

    try:
        detail = response.json().get('message') or response.text[:200]
    except (ValueError, AttributeError):
        detail = response.text[:200]
    code = response.status_code
    if code == 404:
        message = 'not found, or private and GITHUB_TOKEN is missing or lacks access'
    elif code == 401:
        message = f'GitHub rejected GITHUB_TOKEN ({detail})'
    elif code in (403, 429) and response.headers.get('x-ratelimit-remaining') == '0':
        reset = response.headers.get('x-ratelimit-reset', '')
        reset_at = datetime.fromtimestamp(int(reset), tz=timezone.utc).isoformat() if reset.isdigit() else 'unknown'
        message = f'GitHub rate limit exhausted, resets at {reset_at}'
    elif code == 403:
        message = f'GitHub refused access ({detail})'
    elif code == 410:
        message = f'GitHub API version {GITHUB_API_VERSION} is no longer supported'
    else:
        message = f'GitHub API error {code} ({detail})'
    raise ValueError(message)


async def fetch_repo_stats(client: httpx.AsyncClient, full_name: str) -> GithubRepoStats:
    """
    Fetch the star count and the release-asset download total of one repository
    Args:
        client: Client built by `sync_github_repos`
        full_name: Repository 'owner/name'

    Returns:
        `GithubRepoStats`, `download_count` is summed over every asset of every published release

    Raises:
        ValueError: GitHub could not be reached, refused the request or answered with an unexpected payload
    """
    repo = await github_get(client, f'/repos/{full_name}')
    if not isinstance(repo, dict) or 'stargazers_count' not in repo:
        raise ValueError('repository payload has no stargazers_count')
    star_count = int(repo['stargazers_count'])

    download_count = 0
    page = 1
    while True:
        releases = await github_get(client, f'/repos/{full_name}/releases', params={'per_page': PER_PAGE, 'page': page})
        if not isinstance(releases, list):
            raise ValueError('unexpected releases payload')
        for release in releases:
            download_count += sum(int(asset.get('download_count', 0)) for asset in release.get('assets', []))
        if len(releases) < PER_PAGE:
            break
        page += 1
        if page > MAX_RELEASE_PAGES:
            raise ValueError(f'more than {MAX_RELEASE_PAGES * PER_PAGE} releases, giving up')
    stats = GithubRepoStats(full_name=full_name, star_count=star_count, download_count=download_count)
    return stats


async def save_project_snapshots(db: AsyncSession, project_ids: set[int], day: date) -> None:
    """
    Write the latest-known github totals of each project into its `ProjectDownload` row for `day`, created or updated in place
    Totals are summed over all repos of the project, stale rows included, so a repo whose fetch failed keeps contributing its last numbers.
    Args:
        db: Database session, flushed first so the aggregate sees the numbers written in this run (SessionLocal has autoflush=False)
        project_ids: Projects whose repos were refreshed
        day: Snapshot date (UTC)
    """
    if not project_ids:
        return
    await db.flush()
    totals_stmt = (
        select(GithubRepo.project_id, func.coalesce(func.sum(GithubRepo.download_count), 0), func.sum(GithubRepo.star_count))
        .where(GithubRepo.project_id.in_(project_ids))
        .group_by(GithubRepo.project_id)
    )
    for project_id, downloads, stars in (await db.execute(totals_stmt)).all():
        snapshot_stmt = select(ProjectDownload).where(
            ProjectDownload.project_id == project_id, ProjectDownload.platform == GITHUB_PLATFORM, ProjectDownload.date == day
        ).order_by(ProjectDownload.id)
        snapshots = (await db.scalars(snapshot_stmt)).all()
        star_total = None if stars is None else int(stars)
        if len(snapshots) > 1:
            system_log.warning(f'GitHub sync: project {project_id} has {len(snapshots)} github snapshots for {day}, updating the oldest (id {snapshots[0].id})')
        if snapshots:
            snapshots[0].download_count = int(downloads)
            snapshots[0].star_count = star_total
        else:
            db.add(ProjectDownload(project_id=project_id, date=day, platform=GITHUB_PLATFORM, download_count=int(downloads), star_count=star_total))


async def sync_github_repos(db: AsyncSession, repo_id: int | None = None) -> GithubSyncResult:
    """
    Refresh tracked GitHub repos and write today's per-project `github` snapshot, one run at a time per process
    Args:
        db: Database session, committed on success and rolled back on an unexpected error
        repo_id: Tracked repo to refresh, None for all

    Returns:
        `GithubSyncResult`, refreshed rows in `synced`, rows whose fetch failed in `failed` (`last_error` set, old numbers kept)
    """
    headers = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': GITHUB_API_VERSION, 'User-Agent': USER_AGENT}
    if settings.GITHUB_TOKEN:
        headers['Authorization'] = f'Bearer {settings.GITHUB_TOKEN}'

    async with sync_lock:
        stmt = select(GithubRepo).order_by(GithubRepo.id)
        if repo_id is not None:
            stmt = stmt.where(GithubRepo.id == repo_id)
        repos = (await db.scalars(stmt)).all()
        now = datetime.now(timezone.utc)
        synced: list[GithubRepo] = []
        failed: list[GithubRepo] = []

        async with httpx.AsyncClient(base_url=GITHUB_API, headers=headers, timeout=TIMEOUT_SECONDS, follow_redirects=True) as client:
            for repo in repos:
                try:
                    stats = await fetch_repo_stats(client, repo.full_name)
                except ValueError as err:
                    repo.last_error = str(err)
                    system_log.warning(f'GitHub sync {repo.full_name}: {err}')
                    failed.append(repo)
                    continue
                except Exception as err:
                    repo.last_error = f'unexpected error: {err}'
                    system_log.error(f'GitHub sync {repo.full_name} crashed: {format_exc()}')
                    failed.append(repo)
                    continue
                repo.star_count = stats.star_count
                repo.download_count = stats.download_count
                repo.last_synced_at = now
                repo.last_error = None
                system_log.info(f'GitHub sync {repo.full_name}: {stats.star_count} stars, {stats.download_count} downloads')
                synced.append(repo)

        try:
            await save_project_snapshots(db, {repo.project_id for repo in synced}, now.date())
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    result = GithubSyncResult(synced=[repo.to_dict() for repo in synced], failed=[repo.to_dict() for repo in failed])
    system_log.info(f'GitHub sync finished: {len(result.synced)} synced, {len(result.failed)} failed')
    return result
