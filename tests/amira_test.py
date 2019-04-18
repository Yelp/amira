# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import tarfile

import pytest
from mock import ANY
from mock import call
from mock import MagicMock
from mock import patch

import amira
from amira.amira import AMIRA
from amira.amira import OSXCollectorOutputExtractionError
from amira.s3 import S3Handler
from amira.sqs import CreatedObject
from amira.sqs import SqsHandler


@pytest.fixture
def tar_gz_mock():
    """Mocks tar.gz file content."""
    tarfile.open = MagicMock()
    tarinfo_mock = MagicMock()
    tarinfo_mock.name = 'lorem_ipsum.json'

    tar_mock = tarfile.open.return_value
    tar_mock.__iter__.return_value = [tarinfo_mock]

    return tarinfo_mock


@pytest.fixture
def run_filter_mock():
    """Mocks `amira.amira._run_filter()`."""
    mock_run_filter = MagicMock()
    amira.amira._run_filter = mock_run_filter
    amira.amira.AnalyzeFilter = MagicMock()
    return mock_run_filter


class TestAmira():

    """Tests ``amira.amira.AMIRA`` class."""

    def _patch_and_run_amira(
            self, region_name, queue_name, contents, created_objects,
    ):
        """Patches all the external dependencies and runs AMIRA."""
        self._results_uploader_mock = MagicMock()

        with patch.object(
            S3Handler, '__init__', autospec=True, return_value=None,
        ), patch.object(
            S3Handler, 'get_contents_as_string', autospec=True, side_effect=contents,
        ) as self._patched_get_contents_as_string, patch.object(
            SqsHandler, '__init__', autospec=True, return_value=None,
        ), patch(
            'os.path.exists', return_value=True,
        ), patch.object(
            SqsHandler, 'get_created_objects', autospec=True, side_effect=created_objects,
        ) as self._patched_get_created_objects:
            amira = AMIRA(region_name, queue_name)
            amira.register_results_uploader(self._results_uploader_mock)
            amira.run()

    def test_run(self, tar_gz_mock, run_filter_mock):
        contents = [
            b'New Petitions Against Tax',
            b'Building Code Under Fire',
        ]
        created_objects = [[
            CreatedObject(
                bucket_name='amira-test', key_name='AMIRA-301.tar.gz',
            ),
            CreatedObject(
                bucket_name='amira-test', key_name='AMIRA-302.tar.gz',
            ),
        ]]

        region_name, queue_name = 'us-west-2', 'etaoin-shrdlu'
        self._patch_and_run_amira(
            region_name, queue_name, contents, created_objects,
        )

        assert 1 == self._patched_get_created_objects.call_count
        assert self._patched_get_contents_as_string.call_args_list == [
            call(ANY, 'amira-test', 'AMIRA-301.tar.gz'),
            call(ANY, 'amira-test', 'AMIRA-302.tar.gz'),
        ]
        assert 2 == run_filter_mock.call_count

        # assert that the results uploader was called
        # with the expected arguments
        assert [
            call([
                ('AMIRA-301.tar.gz', ANY, 'application/gzip'),
                ('AMIRA-301_analysis.json', ANY, 'application/json'),
                ('AMIRA-301_summary.txt', ANY, 'text/plain'),
                ('AMIRA-301_summary.html', ANY, 'text/html; charset=UTF-8'),
            ]),
            call([
                ('AMIRA-302.tar.gz', ANY, 'application/gzip'),
                ('AMIRA-302_analysis.json', ANY, 'application/json'),
                ('AMIRA-302_summary.txt', ANY, 'text/plain'),
                ('AMIRA-302_summary.html', ANY, 'text/html; charset=UTF-8'),
            ]),
        ] == self._results_uploader_mock.upload_results.call_args_list

    def test_run_wrong_key_name_suffix(self, tar_gz_mock, run_filter_mock):
        created_objects = [[
            CreatedObject(bucket_name='amira-test', key_name='MALWARE-301.txt'),
        ]]

        region_name, queue_name = 'us-west-2', 'cmfwyp-vbgkqj'
        self._patch_and_run_amira(
            region_name, queue_name, None, created_objects,
        )

        assert 1 == self._patched_get_created_objects.call_count
        assert not self._patched_get_contents_as_string.called
        assert not self._results_uploader_mock.upload_results.called
        assert not tar_gz_mock.called
        assert not run_filter_mock.called

    def test_fetch_and_process_osxcollector_no_json_file_in_tar_gz(
            self, tar_gz_mock, run_filter_mock,
    ):
        contents = [b'ETAOIN! SHRDLU! CMFWYP!']
        created_objects = [[
            CreatedObject(
                bucket_name='amira-test', key_name='MALWARE-302.tar.gz',
            ),
        ]]
        # change the filename inside the tar gz mock
        tar_gz_mock.name = 'lorem_ipsum.txt'

        region_name, queue_name = 'us-west-2', 'etaoin-shrdlu'

        with pytest.raises(OSXCollectorOutputExtractionError) as exc_info:
            self._patch_and_run_amira(
                region_name, queue_name, contents, created_objects,
            )

        assert 'Expected 1 JSON file inside the OSXCollector output archive, '\
            'but found 0 instead.' in str(exc_info.value)

        assert not run_filter_mock.called

    def test_run_analyze_filter_exception(
            self, tar_gz_mock, run_filter_mock,
    ):
        """Tests the exception handling while running the Analyze
        Filter.
        """
        contents = [b'The European languages are members of the same family.']
        created_objects = [[
            CreatedObject(
                bucket_name='amira-test', key_name='MALWARE-303.tar.gz',
            ),
        ]]

        run_filter_mock.side_effect = Exception

        region_name, queue_name = 'us-west-2', 'li-europan-lingues'
        self._patch_and_run_amira(
            region_name, queue_name, contents, created_objects,
        )

        assert self._results_uploader_mock.upload_results.called
        assert run_filter_mock.called
