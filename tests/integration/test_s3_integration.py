"""
Integration tests for AWS S3.

Requires real AWS credentials and bucket in the environment:
  AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME, AWS_REGION

Run via: pytest tests/integration/ -v
"""
import os
import uuid
import pytest

PLACEHOLDER_VALUES = {"", "test-key-id", "test-secret", "test-bucket", "placeholder"}


def _has_real_s3_config() -> bool:
    required = [
        os.getenv("AWS_ACCESS_KEY_ID", ""),
        os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        os.getenv("AWS_BUCKET_NAME", ""),
    ]
    return all(value and value not in PLACEHOLDER_VALUES for value in required)


SKIP_IF_NO_S3 = pytest.mark.skipif(
    not _has_real_s3_config(),
    reason="Real AWS S3 credentials and bucket not configured",
)

# Minimal valid single-page PDF (no real content needed for upload tests)
TINY_PDF = (
    b"%PDF-1.0\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj "
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj "
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj "
    b"xref\n0 4\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000058 00000 n \n"
    b"0000000115 00000 n \n"
    b"trailer<</Size 4/Root 1 0 R>>\n"
    b"startxref\n190\n%%EOF"
)


@SKIP_IF_NO_S3
class TestS3Connectivity:
    def test_service_initialises(self):
        """S3Service connects to the bucket without error."""
        from s3_service import S3Service
        service = S3Service()
        assert service.bucket_name == os.getenv("AWS_BUCKET_NAME")


@SKIP_IF_NO_S3
class TestS3UploadDownloadDelete:
    """Full round-trip: upload → download → verify → delete."""

    @pytest.fixture(autouse=True)
    def service(self):
        from s3_service import S3Service
        self._service = S3Service()

    def test_upload_returns_key(self):
        unique_name = f"integration-test-{uuid.uuid4().hex[:8]}.pdf"
        key = self._service.upload_file_to_s3(TINY_PDF, unique_name, user_id="ci-test")
        assert key.startswith("resumes/ci-test/")
        # Clean up
        self._service.delete_file_from_s3(key)

    def test_download_matches_upload(self):
        unique_name = f"integration-test-{uuid.uuid4().hex[:8]}.pdf"
        key = self._service.upload_file_to_s3(TINY_PDF, unique_name, user_id="ci-test")
        try:
            content, filename = self._service.download_file_from_s3(key)
            assert content == TINY_PDF
            assert filename == unique_name
        finally:
            self._service.delete_file_from_s3(key)

    def test_delete_removes_file(self):
        unique_name = f"integration-test-{uuid.uuid4().hex[:8]}.pdf"
        key = self._service.upload_file_to_s3(TINY_PDF, unique_name, user_id="ci-test")
        result = self._service.delete_file_from_s3(key)
        assert result is True

        # Verify it's gone
        with pytest.raises(Exception, match="File not found in S3"):
            self._service.download_file_from_s3(key)

    def test_get_file_info(self):
        unique_name = f"integration-test-{uuid.uuid4().hex[:8]}.pdf"
        key = self._service.upload_file_to_s3(TINY_PDF, unique_name, user_id="ci-test")
        try:
            info = self._service.get_file_info(key)
            assert info["size"] == len(TINY_PDF)
            assert info["content_type"] == "application/pdf"
        finally:
            self._service.delete_file_from_s3(key)

    def test_download_missing_key_raises(self):
        with pytest.raises(Exception, match="File not found in S3"):
            self._service.download_file_from_s3("resumes/ci-test/does-not-exist.pdf")
