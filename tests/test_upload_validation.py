"""Tests for the upload validation helpers added in the security hardening PR."""
import pytest
from fastapi import HTTPException

from app import _reject_bad_content_type, _enforce_upload_size, MAX_UPLOAD_BYTES


class TestRejectBadContentType:
    def test_mismatched_content_type_rejected(self):
        with pytest.raises(HTTPException) as exc:
            _reject_bad_content_type("image/png", "pdf")
        assert exc.value.status_code == 400

    def test_matching_content_type_allowed(self):
        _reject_bad_content_type("application/pdf", "pdf")
        _reject_bad_content_type("image/jpeg", "jpg")
        _reject_bad_content_type("image/jpeg", "jpeg")
        _reject_bad_content_type("image/png", "png")

    def test_content_type_with_charset_suffix_allowed(self):
        _reject_bad_content_type("application/pdf; charset=utf-8", "pdf")

    def test_missing_content_type_is_lenient(self):
        _reject_bad_content_type(None, "pdf")
        _reject_bad_content_type("", "pdf")

    def test_unknown_extension_is_lenient(self):
        # Extensions outside the allowlist are validated elsewhere.
        _reject_bad_content_type("application/octet-stream", "docx")


class TestEnforceUploadSize:
    def test_oversized_upload_rejected(self):
        with pytest.raises(HTTPException) as exc:
            _enforce_upload_size(b"x" * (MAX_UPLOAD_BYTES + 1))
        assert exc.value.status_code == 413

    def test_size_at_limit_allowed(self):
        _enforce_upload_size(b"x" * MAX_UPLOAD_BYTES)

    def test_small_upload_allowed(self):
        _enforce_upload_size(b"%PDF-1.4 tiny")
