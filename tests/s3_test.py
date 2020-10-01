# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

try:
    from cStringIO import StringIO as ByteBuffer
except ImportError:
    from io import BytesIO as ByteBuffer

import pytest
from mock import MagicMock
from mock import patch
from mock import call

from amira.results_uploader import FileMetaInfo
from amira.s3 import S3Handler
from amira.s3 import S3ResultsUploader


class TestS3Handler(object):

    """Tests ``amira.s3.S3Handler`` class."""

    @pytest.fixture
    def s3_handler(self):
        with patch('amira.s3.boto3') as mock_boto3:
            handler = S3Handler()
            mock_boto3.client.assert_called_once_with('s3')
            yield handler

    def test_get_contents_as_string(self, s3_handler):
        mock_contents = 'test key contents'
        s3_connection_mock = s3_handler._s3_connection
        s3_connection_mock.get_object.return_value = {
            'Body': ByteBuffer(mock_contents.encode()),
        }
        contents = s3_handler.get_contents_as_string(
            'amira-test', 'MALWARE-1564-2016_01_11-10_55_12.tar.gz',
        )
        assert mock_contents == contents.decode()
        s3_connection_mock.get_object.assert_called_once_with(
            Bucket='amira-test', Key='MALWARE-1564-2016_01_11-10_55_12.tar.gz',
        )


class TestS3ResultsUploader():

    """Tests ``amira.s3.S3ResultsUploader`` class."""

    @pytest.fixture
    def s3_results_uploader(self):
        with patch('amira.s3.boto3') as mock_boto3:
            uploader = S3ResultsUploader('lorem-ipsum')
            mock_boto3.client.assert_called_once_with('s3')
            yield uploader

    def test_upload_results(self, s3_results_uploader):
        s3_connection_mock = s3_results_uploader._s3_connection
        fileobj_mock1 = MagicMock()
        fileobj_mock2 = MagicMock()
        results = [
            FileMetaInfo('etaoin', fileobj_mock1, 'text/html; charset=UTF-8'),
            FileMetaInfo('shrdlu', fileobj_mock2, 'application/json'),
        ]
        s3_results_uploader.upload_results(results)
        s3_connection_mock.put_object.assert_has_calls([
            call(
                Bucket='lorem-ipsum',
                Key='etaoin',
                ContentType='text/html; charset=UTF-8',
                Body=fileobj_mock1,
            ),
            call(
                Bucket='lorem-ipsum',
                Key='shrdlu',
                ContentType='application/json',
                Body=fileobj_mock2,
            ),
        ])
