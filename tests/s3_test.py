# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import boto
import pytest
from boto.s3.key import Key
from mock import ANY
from mock import MagicMock
from mock import patch

from amira.results_uploader import FileMetaInfo
from amira.s3 import S3Handler
from amira.s3 import S3ResultsUploader


class TestS3Handler():

    """Tests ``amira.s3.S3Handler`` class."""

    @pytest.fixture
    def s3_handler(self):
        boto.connect_s3 = MagicMock()
        return S3Handler()

    def test_get_contents_as_string(self, s3_handler):
        s3_connection_mock = boto.connect_s3.return_value
        bucket_mock = s3_connection_mock.get_bucket.return_value
        key_mock = bucket_mock.get_key.return_value
        key_mock.get_contents_as_string.return_value = 'test key contents'

        contents = s3_handler.get_contents_as_string(
            'amira-test', 'MALWARE-1564-2016_01_11-10_55_12.tar.gz',
        )

        assert 'test key contents' == contents
        s3_connection_mock.get_bucket.assert_called_once_with(
            'amira-test', validate=False,
        )
        bucket_mock.get_key.assert_called_once_with(
            'MALWARE-1564-2016_01_11-10_55_12.tar.gz',
        )
        key_mock.get_contents_as_string.assert_called_once_with()


class TestS3ResultsUploader():

    """Tests ``amira.s3.S3ResultsUploader`` class."""

    @pytest.fixture
    def s3_results_uploader(self):
        boto.connect_s3 = MagicMock()
        return S3ResultsUploader('lorem-ipsum')

    def test_upload_results(self, s3_results_uploader):
        s3_connection_mock = boto.connect_s3.return_value

        fileobj_mock1 = MagicMock()
        fileobj_mock2 = MagicMock()

        results = [
            FileMetaInfo('etaoin', fileobj_mock1, 'text/html; charset=UTF-8'),
            FileMetaInfo('shrdlu', fileobj_mock2, 'application/json'),
        ]

        with patch.object(Key, 'set_contents_from_file', autospec=True) \
                as patched_set_contents_from_file:
            s3_results_uploader.upload_results(results)

        s3_connection_mock.get_bucket.assert_called_once_with(
            'lorem-ipsum', validate=False,
        )
        assert [
            (
                (ANY, fileobj_mock1), {
                    'headers': {
                        'Content-Type': 'text/html; charset=UTF-8',
                    },
                },
            ),
            (
                (ANY, fileobj_mock2), {
                    'headers': {
                        'Content-Type': 'application/json',
                    },
                },
            ),
        ] == patched_set_contents_from_file.call_args_list
