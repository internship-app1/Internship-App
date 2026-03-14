"""
Tests for s3_service.py

boto3 is fully mocked — no real AWS credentials needed.
"""
import re
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_s3_service():
    """Instantiate S3Service with a patched boto3 client."""
    with patch("s3_service.boto3.client") as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.return_value = mock_client
        # head_bucket succeeds (connection test)
        mock_client.head_bucket.return_value = {}
        from s3_service import S3Service
        service = S3Service()
        service.s3_client = mock_client  # expose for assertions
        return service, mock_client


# ---------------------------------------------------------------------------
# generate_s3_key
# ---------------------------------------------------------------------------

class TestGenerateS3Key:
    def test_includes_user_id(self):
        service, _ = _make_s3_service()
        key = service.generate_s3_key("resume.pdf", user_id="user123")
        assert key.startswith("resumes/user123/")
        assert "resume.pdf" in key

    def test_anonymous_when_no_user(self):
        service, _ = _make_s3_service()
        key = service.generate_s3_key("cv.pdf")
        assert key.startswith("resumes/anonymous/")

    def test_key_is_unique(self):
        service, _ = _make_s3_service()
        k1 = service.generate_s3_key("resume.pdf", "u1")
        k2 = service.generate_s3_key("resume.pdf", "u1")
        assert k1 != k2

    def test_unsafe_chars_stripped(self):
        service, _ = _make_s3_service()
        key = service.generate_s3_key("my resume (1).pdf", "u1")
        # Spaces and parentheses should be removed
        assert " " not in key
        assert "(" not in key
        assert ")" not in key


# ---------------------------------------------------------------------------
# _get_content_type
# ---------------------------------------------------------------------------

class TestGetContentType:
    def test_pdf(self):
        service, _ = _make_s3_service()
        assert service._get_content_type("resume.pdf") == "application/pdf"

    def test_png(self):
        service, _ = _make_s3_service()
        assert service._get_content_type("photo.PNG") == "image/png"

    def test_unknown(self):
        service, _ = _make_s3_service()
        assert service._get_content_type("file.xyz") == "application/octet-stream"

    def test_no_extension(self):
        service, _ = _make_s3_service()
        assert service._get_content_type("file") == "application/octet-stream"


# ---------------------------------------------------------------------------
# upload_file_to_s3
# ---------------------------------------------------------------------------

class TestUploadFile:
    def test_returns_s3_key(self):
        service, mock_client = _make_s3_service()
        mock_client.put_object.return_value = {}

        key = service.upload_file_to_s3(b"pdf-content", "resume.pdf", "user42")

        assert key.startswith("resumes/user42/")
        mock_client.put_object.assert_called_once()

    def test_raises_on_s3_error(self):
        service, mock_client = _make_s3_service()
        mock_client.put_object.side_effect = Exception("S3 down")

        with pytest.raises(Exception, match="S3 upload failed"):
            service.upload_file_to_s3(b"data", "resume.pdf", "user1")


# ---------------------------------------------------------------------------
# download_file_from_s3
# ---------------------------------------------------------------------------

class TestDownloadFile:
    def test_returns_bytes_and_filename(self):
        service, mock_client = _make_s3_service()
        mock_client.get_object.return_value = {
            "Body": MagicMock(read=lambda: b"pdf-bytes"),
            "Metadata": {"original_filename": "my_resume.pdf"},
        }

        content, filename = service.download_file_from_s3("resumes/u/key.pdf")

        assert content == b"pdf-bytes"
        assert filename == "my_resume.pdf"

    def test_raises_on_missing_key(self):
        from botocore.exceptions import ClientError

        service, mock_client = _make_s3_service()
        error_response = {"Error": {"Code": "NoSuchKey", "Message": "not found"}}
        mock_client.get_object.side_effect = ClientError(error_response, "GetObject")

        with pytest.raises(Exception, match="File not found in S3"):
            service.download_file_from_s3("resumes/u/missing.pdf")


# ---------------------------------------------------------------------------
# delete_file_from_s3
# ---------------------------------------------------------------------------

class TestDeleteFile:
    def test_returns_true_on_success(self):
        service, mock_client = _make_s3_service()
        mock_client.delete_object.return_value = {}

        result = service.delete_file_from_s3("resumes/u/key.pdf")

        assert result is True
        mock_client.delete_object.assert_called_once()

    def test_returns_false_on_error(self):
        service, mock_client = _make_s3_service()
        mock_client.delete_object.side_effect = Exception("network error")

        result = service.delete_file_from_s3("resumes/u/key.pdf")

        assert result is False
