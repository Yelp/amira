# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import tarfile

import pytest
from mock import ANY
from mock import MagicMock
from mock import patch

try:
    from cStringIO import StringIO as ByteBuffer
except ImportError:
    from io import BytesIO as ByteBuffer

from amira.results_uploader import FileMetaInfo
from amira.data_processor import DataProcessor
from amira.data_processor import OSXCollectorDataProcessor
from amira.data_processor import OSXCollectorOutputExtractionError


class TestDataProcessor(object):

    def test_get_buffer_size(self):
        assert DataProcessor.get_buffer_size(ByteBuffer(b'123' * 111)) == 333

    def test_upload_results(self):
        data = ByteBuffer(b'123')
        processor = DataProcessor()
        processor._results = [FileMetaInfo('_suff.txt', data, 'text/plain')]
        uploaders = [MagicMock(), MagicMock()]
        processor.upload_results('filename', uploaders)
        for u in uploaders:
            u.upload_results.assert_called_once_with(
                [FileMetaInfo('filename_suff.txt', data, 'text/plain')],
            )


class TestOSXCollectorDataProcessor(object):

    @pytest.fixture
    def tar_gz_mock(self):
        """Mocks tar.gz file content."""
        tarfile.open = MagicMock()
        tarinfo_mock = MagicMock()
        tarinfo_mock.name = 'lorem_ipsum.json'
        tar_mock = tarfile.open.return_value
        tar_mock.__iter__.return_value = [tarinfo_mock]
        return tarinfo_mock

    def test_process_input(self):
        processor = OSXCollectorDataProcessor()
        with open('tests/data/mock_input.tar.gz', 'rb') as f:
            input_data = f.read()
        output = processor.process_input(input_data)
        assert output.read() == b'{"a":2}\n'
        assert len(processor._results) == 1

    def test_process_input_no_json(self, tar_gz_mock):
        processor = OSXCollectorDataProcessor()
        tar_gz_mock.name = 'lorem_ipsum.txt'

        with pytest.raises(OSXCollectorOutputExtractionError) as exc_info:
            processor.process_input(b'things')

        assert 'Expected 1 JSON file inside the OSXCollector output archive, ' \
               'but found 0 instead.' in str(exc_info.value)

    def test_perform_analysis(self):
        with patch('amira.data_processor.AnalyzeFilter') as mock_filter, \
                patch('amira.data_processor.output_filter') as mock_run_filter:
            processor = OSXCollectorDataProcessor()
            processor.perform_analysis(b'123', {'a': 'b'})
            mock_filter.assert_called_once_with(
                monochrome=True,
                html_output_file=ANY,
                text_output_file=ANY,
                data_feeds={'a': 'b'},
            )
            mock_run_filter._run_filter.assert_called_once_with(
                mock_filter.return_value,
                input_stream=b'123',
                output_stream=ANY,
            )
            assert len(processor._results) == 3
