import shutil
from typing import Dict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.job import DownloadJob, JobStatus

# In-memory runtime metrics counters
_cache_hits = 0
_cache_misses = 0


def record_cache_hit() -> None:
    global _cache_hits
    _cache_hits += 1


def record_cache_miss() -> None:
    global _cache_misses
    _cache_misses += 1


async def generate_prometheus_metrics(db: AsyncSession) -> str:
    """
    Renders Prometheus Exposition Format (text/plain; version=0.0.4) metrics
    covering job lifecycle counts, disk space, and cache efficiency.
    """
    lines = []

    # 1. Disk usage
    try:
        usage = shutil.disk_usage(settings.STORAGE_DIR)
        lines.append("# HELP anystream_disk_free_bytes Free storage disk space in bytes")
        lines.append("# TYPE anystream_disk_free_bytes gauge")
        lines.append(f"anystream_disk_free_bytes {usage.free}")

        lines.append("# HELP anystream_disk_total_bytes Total storage disk space in bytes")
        lines.append("# TYPE anystream_disk_total_bytes gauge")
        lines.append(f"anystream_disk_total_bytes {usage.total}")
    except Exception:
        pass

    # 2. Cache hits / misses
    lines.append("# HELP anystream_cache_hits_total Total metadata cache hits")
    lines.append("# TYPE anystream_cache_hits_total counter")
    lines.append(f"anystream_cache_hits_total {_cache_hits}")

    lines.append("# HELP anystream_cache_misses_total Total metadata cache misses")
    lines.append("# TYPE anystream_cache_misses_total counter")
    lines.append(f"anystream_cache_misses_total {_cache_misses}")

    # 3. Database Job Metrics
    status_counts: Dict[str, int] = {st.value: 0 for st in JobStatus}
    total_bytes = 0

    try:
        stmt = select(DownloadJob.status, func.count(DownloadJob.id)).group_by(DownloadJob.status)
        res = await db.execute(stmt)
        for row in res.all():
            status_val = row[0].value if hasattr(row[0], "value") else str(row[0])
            status_counts[status_val] = row[1]

        bytes_stmt = select(func.coalesce(func.sum(DownloadJob.file_size), 0)).where(
            DownloadJob.status == JobStatus.COMPLETED
        )
        total_bytes = (await db.execute(bytes_stmt)).scalar() or 0
    except Exception:
        pass

    lines.append("# HELP anystream_jobs_total Total download jobs by status")
    lines.append("# TYPE anystream_jobs_total counter")
    for status_name, count in status_counts.items():
        lines.append(f'anystream_jobs_total{{status="{status_name.lower()}"}} {count}')

    active_count = status_counts.get(JobStatus.QUEUED.value, 0) + status_counts.get(
        JobStatus.PROCESSING.value, 0
    )
    lines.append("# HELP anystream_jobs_active Current queued or active download jobs")
    lines.append("# TYPE anystream_jobs_active gauge")
    lines.append(f"anystream_jobs_active {active_count}")

    lines.append("# HELP anystream_downloaded_bytes_total Total bytes downloaded across completed jobs")
    lines.append("# TYPE anystream_downloaded_bytes_total counter")
    lines.append(f"anystream_downloaded_bytes_total {total_bytes}")

    lines.append("")
    return "\n".join(lines)
