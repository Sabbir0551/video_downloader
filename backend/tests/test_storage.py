import os
import tempfile
import uuid
from unittest.mock import MagicMock, patch
import pytest

from app.core.config import settings
from app.services.storage import (
    LocalStorage,
    R2Storage,
    build_content_disposition,
    get_media_content_type,
    get_storage,
)


def test_content_type_mapping():
    assert get_media_content_type("mp4") == "video/mp4"
    assert get_media_content_type(".mp3") == "audio/mpeg"
    assert get_media_content_type("m4a") == "audio/mp4"
    assert get_media_content_type("webm") == "video/webm"
    assert get_media_content_type("xyz") == "application/octet-stream"


def test_build_content_disposition():
    cd = build_content_disposition("My Video Test", "mp4")
    assert 'attachment; filename="My Video Test.mp4"' in cd
    assert "filename*=UTF-8''My%20Video%20Test.mp4" in cd

    # Test Unicode / Bengali characters
    cd_unicode = build_content_disposition("ভিডিও টেস্ট", "mp4")
    assert 'filename="media_download.mp4"' in cd_unicode  # ASCII fallback
    assert "filename*=UTF-8''" in cd_unicode  # UTF-8 encoded


def test_local_storage_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorage(storage_dir=tmpdir)

        # Create dummy file
        src_file = os.path.join(tmpdir, "source.mp4")
        with open(src_file, "wb") as f:
            f.write(b"dummy video data 12345")

        random_key = f"{uuid.uuid4()}.mp4"
        stored_path = storage.upload(src_file, random_key)

        assert os.path.exists(stored_path)
        assert storage.exists(random_key)
        assert storage.get_file_size(random_key) == 22
        assert storage.get_presigned_url(random_key, "download.mp4") is None

        # Delete
        assert storage.delete(random_key) is True
        assert not storage.exists(random_key)


def test_r2_storage_initialization_error():
    with pytest.raises(ValueError, match="R2_ACCOUNT_ID must be configured"):
        R2Storage(account_id="", access_key_id="key", secret_access_key="secret", bucket="b")

    with pytest.raises(ValueError, match="R2_ACCESS_KEY_ID"):
        R2Storage(account_id="acc", access_key_id="", secret_access_key="secret", bucket="b")


@patch("boto3.client")
def test_r2_storage_lifecycle(mock_boto_client):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3

    r2 = R2Storage(
        account_id="test-account-id",
        access_key_id="test-key",
        secret_access_key="test-secret",
        bucket="test-bucket",
    )

    assert r2.endpoint_url == "https://test-account-id.r2.cloudflarestorage.com"
    mock_boto_client.assert_called_once_with(
        service_name="s3",
        endpoint_url="https://test-account-id.r2.cloudflarestorage.com",
        aws_access_key_id="test-key",
        aws_secret_access_key="test-secret",
        region_name="auto",
        config=pytest.approx(mock_boto_client.call_args[1]["config"]),
    )

    # 1. Test Upload (Random ID Key only, never title)
    random_key = f"{uuid.uuid4()}.mp4"
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"video stream content")
        local_path = f.name

    try:
        res_key = r2.upload(local_path, random_key, content_type="video/mp4")
        assert res_key == random_key
        mock_s3.upload_file.assert_called_once_with(
            Filename=local_path,
            Bucket="test-bucket",
            Key=random_key,
            ExtraArgs={"ContentType": "video/mp4"},
        )
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)

    # 2. Test Exists
    mock_s3.head_object.return_value = {"ContentLength": 1024}
    assert r2.exists(random_key) is True
    assert r2.get_file_size(random_key) == 1024

    from botocore.exceptions import ClientError
    mock_s3.head_object.side_effect = ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "head_object")
    assert r2.exists("non-existent-key") is False
    assert r2.get_file_size("non-existent-key") is None

    # 3. Test Delete
    assert r2.delete(random_key) is True
    mock_s3.delete_object.assert_called_once_with(Bucket="test-bucket", Key=random_key)

    # 4. Test Presigned URL generation
    mock_s3.generate_presigned_url.return_value = "https://r2.test/download-link"
    url = r2.get_presigned_url(random_key, "My Safe Video Title.mp4", expiry_seconds=900)
    assert url == "https://r2.test/download-link"
    mock_s3.generate_presigned_url.assert_called_once()
    call_args = mock_s3.generate_presigned_url.call_args[1]
    assert call_args["ClientMethod"] == "get_object"
    assert call_args["Params"]["Bucket"] == "test-bucket"
    assert call_args["Params"]["Key"] == random_key
    assert "ResponseContentDisposition" in call_args["Params"]
    assert "My Safe Video Title.mp4" in call_args["Params"]["ResponseContentDisposition"]
    assert call_args["ExpiresIn"] == 900


def test_get_storage_factory():
    with patch.object(settings, "STORAGE_BACKEND", "local"):
        storage = get_storage()
        assert isinstance(storage, LocalStorage)

    with patch.object(settings, "STORAGE_BACKEND", "r2"), \
         patch.object(settings, "R2_ACCOUNT_ID", "acc"), \
         patch.object(settings, "R2_ACCESS_KEY_ID", "key"), \
         patch.object(settings, "R2_SECRET_ACCESS_KEY", "secret"), \
         patch("boto3.client"):
        storage = get_storage()
        assert isinstance(storage, R2Storage)


def test_download_endpoint_r2_redirect():
    import asyncio
    from unittest.mock import AsyncMock
    from fastapi.responses import RedirectResponse
    from app.api.v1.endpoints.downloads import download_file
    from app.core.security import generate_download_token
    from app.models.job import DownloadJob, JobStatus

    job_id = uuid.uuid4()
    mock_job = DownloadJob(
        id=job_id,
        url_hash="dummy_hash_r2",
        original_url="https://youtube.com/watch?v=sample_r2",
        title="My Special R2 Video",
        format_id="best",
        ip_hash="test_ip_hash",
        status=JobStatus.COMPLETED,
        progress=100.0,
        file_path=f"{job_id}.mp4",
        file_size=5000,
        file_ext="mp4",
    )

    token = generate_download_token(str(job_id), "My Special R2 Video.mp4", 1800)

    mock_storage = MagicMock()
    mock_storage.exists.return_value = True
    presigned_target = f"https://myaccount.r2.cloudflarestorage.com/anystream-files/{job_id}.mp4?signature=xyz"
    mock_storage.get_presigned_url.return_value = presigned_target

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_job
    mock_session.execute.return_value = mock_result

    with patch("app.api.v1.endpoints.downloads.get_storage", return_value=mock_storage):
        resp = asyncio.run(download_file(
            job_id=job_id,
            token=token,
            request=MagicMock(),
            db=mock_session,
        ))

        assert isinstance(resp, RedirectResponse)
        assert resp.status_code == 307
        assert resp.headers["location"] == presigned_target
        mock_storage.exists.assert_called_once_with(f"{job_id}.mp4")
        mock_storage.get_presigned_url.assert_called_once()


def test_worker_task_r2_upload_and_cleanup():
    from app.db.session import get_sync_db
    from app.models.job import DownloadJob, JobStatus
    from app.worker.tasks import download_media_task

    job_id = uuid.uuid4()
    with get_sync_db() as db:
        job = DownloadJob(
            id=job_id,
            url_hash="dummy_hash_worker_r2",
            original_url="https://youtube.com/watch?v=sample_worker_r2",
            title="Worker R2 Test Title",
            format_id="best",
            ip_hash="test_ip_hash",
            status=JobStatus.QUEUED,
        )
        db.add(job)
        db.commit()

    # Create dummy finalized file on disk
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    dummy_file = os.path.join(settings.STORAGE_DIR, f"{job_id}.mp4")
    with open(dummy_file, "wb") as f:
        f.write(b"simulated merged mp4 content")

    mock_storage = MagicMock()
    mock_storage.upload.return_value = f"{job_id}.mp4"

    with patch("yt_dlp.YoutubeDL") as mock_ydl_class, \
         patch("app.worker.tasks.get_storage", return_value=mock_storage), \
         patch.object(settings, "STORAGE_BACKEND", "r2"):

        mock_ydl_instance = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl_instance

        res = download_media_task(str(job_id), "https://youtube.com/watch?v=sample_worker_r2", "best")
        assert res["status"] == "COMPLETED"

        # Verify uploaded under random ID key only, NEVER video title!
        mock_storage.upload.assert_called_once()
        uploaded_path, uploaded_key = mock_storage.upload.call_args[0]
        assert uploaded_key == f"{job_id}.mp4"
        assert "Worker R2 Test Title" not in uploaded_key

        # Verify local temporary file was deleted
        assert not os.path.exists(dummy_file)

        # Verify job record in database stores only object key
        with get_sync_db() as db:
            updated_job = db.get(DownloadJob, job_id)
            assert updated_job.status == JobStatus.COMPLETED
            assert updated_job.file_path == f"{job_id}.mp4"
            assert "token=" in updated_job.download_url

