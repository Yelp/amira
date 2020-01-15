# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import types

from mock import ANY
from mock import call
from mock import MagicMock
from mock import patch
try:
    from cStringIO import StringIO as ByteBuffer
except ImportError:
    from io import BytesIO as ByteBuffer

from amira.amira import AMIRA
from amira.data_processor import DataProcessor
from amira.results_uploader import FileMetaInfo
from amira.s3 import S3Handler
from amira.sqs import CreatedObject
from amira.sqs import SqsHandler


class TestAmira(object):

    """Tests ``amira.amira.AMIRA`` class."""

    def _patch_and_run_amira(
        self, region_name, queue_name, contents, created_objects, data_processor,
    ):
        """Patches all the external dependencies and runs AMIRA."""
        self._results_uploader_mock = MagicMock()

        with patch.object(
            S3Handler, '__init__', autospec=True, return_value=None,
        ), patch.object(
            S3Handler, 'get_contents_as_string', autospec=True, side_effect=contents,
        ) as self._patched_get_contents_as_string, patch.object(
            SqsHandler, '__init__', autospec=True, return_value=None,
        ), patch.object(
            DataProcessor, 'get_buffer_size', return_value=1,
        ), patch.object(
            SqsHandler, 'get_created_objects', autospec=True, side_effect=created_objects,
        ) as self._patched_get_created_objects:
            amira_instance = AMIRA(region_name, queue_name)
            amira_instance.register_results_uploader(self._results_uploader_mock)
            amira_instance.register_data_processor(data_processor)
            amira_instance.run()

    def test_run(self):
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

        mock_processor = DataProcessor()

        def mock_process_input(o, _):
            o._results = [FileMetaInfo('.tar.gz', ByteBuffer(b'1'), 'application/gzip')]
        mock_processor.process_input = types.MethodType(mock_process_input, mock_processor)
        mock_processor.perform_analysis = MagicMock()
        region_name, queue_name = 'us-west-2', 'etaoin-shrdlu'
        self._patch_and_run_amira(
            region_name, queue_name, contents, created_objects, mock_processor,
        )

        assert self._patched_get_created_objects.call_count == 1
        assert self._patched_get_contents_as_string.call_args_list == [
            call(ANY, 'amira-test', 'AMIRA-301.tar.gz'),
            call(ANY, 'amira-test', 'AMIRA-302.tar.gz'),
        ]
        assert mock_processor.perform_analysis.call_count == 2

        # assert that the results uploader was called
        # with the expected arguments
        assert self._results_uploader_mock.upload_results.call_args_list == [
            call([FileMetaInfo('AMIRA-301.tar.gz', ANY, 'application/gzip')]),
            call([FileMetaInfo('AMIRA-302.tar.gz', ANY, 'application/gzip')]),
        ]

    def test_run_wrong_key_name_suffix(self):
        created_objects = [[
            CreatedObject(bucket_name='amira-test', key_name='MALWARE-301.txt'),
        ]]

        mock_processor = MagicMock()
        region_name, queue_name = 'us-west-2', 'cmfwyp-vbgkqj'
        self._patch_and_run_amira(
            region_name, queue_name, None, created_objects, mock_processor,
        )

        assert 1 == self._patched_get_created_objects.call_count
        assert not self._patched_get_contents_as_string.called
        assert not self._results_uploader_mock.upload_results.called
        assert not mock_processor.perform_analysis.called
        assert not mock_processor.process_input.called

    def test_run_analyze_filter_exception(self):
        """Tests the exception handling while running the Analyze Filter."""
        contents = [b'The European languages are members of the same family.']
        created_objects = [[
            CreatedObject(
                bucket_name='amira-test', key_name='MALWARE-303.tar.gz',
            ),
        ]]
        data_processor_mock = MagicMock()
        data_processor_mock.perform_analysis.side_effect = Exception
        region_name, queue_name = 'us-west-2', 'li-europan-lingues'
        self._patch_and_run_amira(
            region_name, queue_name, contents, created_objects, data_processor_mock,
        )
        assert data_processor_mock.perform_analysis.called
        assert data_processor_mock.upload_results.called
