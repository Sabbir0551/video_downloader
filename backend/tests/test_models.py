import uuid
from app.models.job import DownloadJob, JobStatus
from app.models.takedown import TakedownRecord, TakedownStatus
from app.models.abuse import AbuseLog


def test_download_job_model_instantiation():
    """Verify DownloadJob model attributes and defaults."""
    job = DownloadJob(
        url_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        original_url="https://youtube.com/watch?v=test",
        format_id="137+140",
        ip_hash="abc123hashedip",
    )
    assert job.status == JobStatus.QUEUED
    assert job.progress == 0.0
    assert job.is_audio_only is False
    assert job.url_hash.startswith("e3b0c")


def test_takedown_model_instantiation():
    """Verify TakedownRecord attributes and defaults."""
    record = TakedownRecord(
        url_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        target_url="https://youtube.com/watch?v=infringing",
        copyrighted_work_url="https://original.com/work",
        requester_name="Owner",
        requester_email="owner@test.com",
    )
    assert record.status == TakedownStatus.BLOCKED_PENDING_REVIEW
    assert record.requester_name == "Owner"


def test_abuse_log_instantiation():
    """Verify AbuseLog attributes."""
    log = AbuseLog(
        ip_hash="abc123hashedip",
        event_type="SSRF_ATTEMPT",
        details="Attempted access to 169.254.169.254",
    )
    assert log.event_type == "SSRF_ATTEMPT"
    assert "169.254" in log.details

