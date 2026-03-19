"""
Integration tests for AWS S3.

Mocked via unittest.mock to simulate responses without network calls or AWS credentials.
"""
import pytest
from unittest.mock import patch

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

class DummyS3Client:
    def __init__(self):
        self.storage = {}

    def head_bucket(self, Bucket):
        return {}

    def put_object(self, Bucket, Key, Body, ContentType, **kwargs):
        if hasattr(Body, 'read'):
            body_bytes = Body.read()
        else:
            body_bytes = Body
        self.storage[Key] = {
            'Body': body_bytes,
            'ContentType': ContentType,
            'ContentLength': len(body_bytes),
            'Metadata': kwargs.get('Metadata', {}),
            'LastModified': __import__('datetime').datetime.now()
        }
        return {}

    def get_object(self, Bucket, Key):
        if Key not in self.storage:
            from botocore.exceptions import ClientError
            raise ClientError({'Error': {'Code': 'NoSuchKey'}}, 'GetObject')
        item = self.storage[Key]
        
        class DummyBody:
            def read(self):
                return item['Body']
        
        return {
            'Body': DummyBody(),
            'ContentType': item['ContentType'],
            'ContentLength': item['ContentLength'],
            'Metadata': item['Metadata'],
            'LastModified': item['LastModified']
        }

    def delete_object(self, Bucket, Key):
        if Key in self.storage:
            del self.storage[Key]
        return {}
        
    def head_object(self, Bucket, Key):
        if Key not in self.storage:
            from botocore.exceptions import ClientError
            raise ClientError({'Error': {'Code': '404'}}, 'HeadObject')
        item = self.storage[Key]
        return {
            'ContentType': item['ContentType'],
            'ContentLength': item['ContentLength'],
            'Metadata': item['Metadata'],
            'LastModified': item['LastModified']
        }

@patch.dict('os.environ', {'AWS_BUCKET_NAME': 'test-bucket', 'AWS_ACCESS_KEY_ID': 'fake', 'AWS_SECRET_ACCESS_KEY': 'fake'})
@patch('s3_service.boto3.client')
class TestS3Connectivity:
    def test_service_initialises(self, mock_boto3):
        mock_boto3.return_value = DummyS3Client()
        from s3_service import S3Service
        service = S3Service()
        assert service.bucket_name == 'test-bucket'


@patch.dict('os.environ', {'AWS_BUCKET_NAME': 'test-bucket', 'AWS_ACCESS_KEY_ID': 'fake', 'AWS_SECRET_ACCESS_KEY': 'fake'})
@patch('s3_service.boto3.client')
class TestS3UploadDownloadDelete:
    
    def _get_service(self, mock_boto3):
        client = DummyS3Client()
        mock_boto3.return_value = client
        from s3_service import S3Service
        return S3Service()

    def test_upload_returns_key(self, mock_boto3):
        service = self._get_service(mock_boto3)
        key = service.upload_file_to_s3(TINY_PDF, "integration-test-1.pdf", user_id="ci-test")
        assert key.startswith("resumes/ci-test/")
        service.delete_file_from_s3(key)

    def test_download_matches_upload(self, mock_boto3):
        service = self._get_service(mock_boto3)
        key = service.upload_file_to_s3(TINY_PDF, "integration-test-2.pdf", user_id="ci-test")
        try:
            content, filename = service.download_file_from_s3(key)
            assert content == TINY_PDF
            assert filename == "integration-test-2.pdf"
        finally:
            service.delete_file_from_s3(key)

    def test_delete_removes_file(self, mock_boto3):
        service = self._get_service(mock_boto3)
        key = service.upload_file_to_s3(TINY_PDF, "integration-test-3.pdf", user_id="ci-test")
        result = service.delete_file_from_s3(key)
        assert result is True
        with pytest.raises(Exception):
            service.download_file_from_s3(key)

    def test_get_file_info(self, mock_boto3):
        service = self._get_service(mock_boto3)
        key = service.upload_file_to_s3(TINY_PDF, "integration-test-4.pdf", user_id="ci-test")
        try:
            info = service.get_file_info(key)
            assert info["size"] == len(TINY_PDF)
            assert info["content_type"] == "application/pdf"
        finally:
            service.delete_file_from_s3(key)

    def test_download_missing_key_raises(self, mock_boto3):
        service = self._get_service(mock_boto3)
        with pytest.raises(Exception):
            service.download_file_from_s3("resumes/ci-test/does-not-exist.pdf")
