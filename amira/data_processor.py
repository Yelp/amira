# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import logging
import os
import tarfile

try:
    from cStringIO import StringIO as ByteBuffer
    from cStringIO import StringIO as StringBuffer
except ImportError:
    from io import BytesIO as ByteBuffer
    from io import StringIO as StringBuffer

from osxcollector.output_filters.analyze import AnalyzeFilter
from osxcollector.output_filters.base_filters import output_filter

from amira.results_uploader import FileMetaInfo


class DataProcessor(object):

    def __init__(self):
        # List to store processing outputs
        self._results = []

    def process_input(self, tardata):
        """Process input TAR file

        :param tardata: TAR byte stream
        :return: processed data file stream
        """
        raise NotImplementedError()

    def perform_analysis(self, input_stream, data_feeds=None):
        """Perform analysis of forensic input.
        Analysis results should be handled as internal object state

        :param input_stream: forensic data
        :param data_feeds: additional data feeds which may be required in the analysis
        """
        raise NotImplementedError()

    def upload_results(self, file_basename, result_uploaders):
        """Upload forensic results.
        These must be stored as FileMetaInfo objects in the `_results` list attribute

        :param file_basename: Basename used to generate output filenames (prepended)
        :param result_uploaders: List of Uploader objects to invoke
        """
        results = [
            FileMetaInfo(file_basename + res.name, res.content, res.content_type) for res in self._results
            if isinstance(res, FileMetaInfo) and DataProcessor.get_buffer_size(res.content) > 0
        ]
        if results:
            for res_uploader in result_uploaders:
                for res in results:
                    res.content.seek(0)
                res_uploader.upload_results(results)
        else:
            logging.warning('No results to upload for {}'.format(file_basename))

    @staticmethod
    def get_buffer_size(data_buffer):
        """Get byte size of file-like object

        :param data_buffer: file-like object
        :return: total size in bytes
        """
        data_buffer.seek(0, os.SEEK_END)
        size = data_buffer.tell()
        data_buffer.seek(0)
        return size


class OSXCollectorDataProcessor(DataProcessor):

    def process_input(self, tardata):
        """Extracts JSON file containing the OSXCollector output from
        tar.gz archive. It will look in the archive contents for the
        file with the extension ".json". If no file with this extension
        is found in the archive or more than one JSON file is found, it
        will raise `OSXCollectorOutputExtractionError`.

        :param tardata: Input TAR archive data
        """
        self._results = [FileMetaInfo('.tar.gz', ByteBuffer(tardata), 'application/gzip')]
        # create a file-like object based on the S3 object contents as string
        fileobj = ByteBuffer(tardata)
        tar = None
        try:
            tar = tarfile.open(mode='r:gz', fileobj=fileobj)
        except tarfile.ReadError as ter:
            logging.error('Failed to read the archive: {}'.format(ter))
            return

        json_tarinfo = [t for t in tar if t.name.endswith('.json')]

        if len(json_tarinfo) != 1:
            raise OSXCollectorOutputExtractionError(
                'Expected 1 JSON file inside the OSXCollector output archive, '
                'but found {0} instead.'.format(len(json_tarinfo)),
            )

        tarinfo = json_tarinfo[0]
        logging.info('Extracted OSXCollector output JSON file {0}'.format(tarinfo.name))
        return tar.extractfile(tarinfo)

    def perform_analysis(self, input_stream, data_feeds=None):
        """Runs Analyze Filter on the OSXCollector output retrieved
        from an S3 bucket.

        :param input_stream: Input data stream on which filters should be ran
        :param data_feeds: black/whitelist data feeds
        """
        analysis_output = StringBuffer()
        text_analysis_summary = ByteBuffer()
        html_analysis_summary = ByteBuffer()

        analyze_filter = AnalyzeFilter(
            monochrome=True,
            text_output_file=text_analysis_summary,
            html_output_file=html_analysis_summary,
            data_feeds=data_feeds or {},
        )

        output_filter._run_filter(
            analyze_filter,
            input_stream=input_stream,
            output_stream=analysis_output,
        )

        # rewind the output files
        analysis_output.seek(0)
        text_analysis_summary.seek(0)
        html_analysis_summary.seek(0)

        self._results += [
            FileMetaInfo('_analysis.json', analysis_output, 'application/json'),
            FileMetaInfo('_summary.txt', text_analysis_summary, 'text/plain'),
            FileMetaInfo('_summary.html', html_analysis_summary, 'text/html; charset=UTF-8'),
        ]


class OSXCollectorOutputExtractionError(Exception):
    """Raised when an unexpected number of JSON files is found in the
    OSXCollector output archive.
    """
    pass
