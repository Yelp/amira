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
from amira.s3 import S3Handler
from amira.sqs import SqsHandler


class AMIRA():
    """Runs the automated analysis based on the new elements in an S3
    bucket:
        1. Receives the messages from the SQS queue about the new
           objects in the S3 bucket.
        2. Retrieves the objects (OSXCollector output files) from the
           bucket.
        3. Runs the Analayze Filter on the retrieved OSXCollector
           output.
        4. Uploads the analysis results.

    JIRA integration is optional. If any of the JIRA parameters
    (`jira_server`, `jira_user`, `jira_password` or `jira_project`)
    is not supplied or `None`, attaching the analysis results to a JIRA
    issue will be skipped.

    :param region_name: The AWS region name where the SQS queue
                        containing the S3 event notifications is
                        configured.
    :type region_name: string
    :param queue_name: The name of the SQS queue containing the S3
                       event notifications.
    :type queue_name: string
    """

    def __init__(self, region_name, queue_name):
        self._sqs_handler = SqsHandler(region_name, queue_name)
        self._s3_handler = S3Handler()
        self._results_uploader = []

    def register_results_uploader(self, results_uploader):
        """Registers results uploader.

        Results uploader will upload the analysis results and the
        summary to a specific destination after the analysis is
        finished.
        """
        self._results_uploader.append(results_uploader)

    def run(self):
        """Fetches the OSXCollector output from an S3 bucket based on
        the S3 ObjectCreated event notifications and runs the Analyze
        Filter on the output file.
        Once the analysis is finished the output and the "very readable
        output" files are uploaded to the target S3 bucket.
        """
        created_objects = self._sqs_handler.get_created_objects()

        for created_object in created_objects:
            if created_object.key_name.endswith('.tar.gz'):
                self._process_created_object(created_object)
            else:
                logging.warning(
                    'S3 object {0} name should end with ".tar.gz"'
                    .format(created_object.key_name),
                )

    def _process_created_object(self, created_object):
        """Fetches the object from an S3 bucket and runs the analysis.
        Then it sends the results to the target S3 bucket and attaches
        them to the JIRA ticket.
        """
        # fetch the OSXCollector output from the S3 bucket
        self._osxcollector_output = self._s3_handler.get_contents_as_string(
            created_object.bucket_name, created_object.key_name,
        )
        self._extract_osxcollector_output_json_file()

        try:
            self._run_analyze_filter()
        except Exception as exc:
            # Log the exception and do not try any recovery.
            # The message that caused the exception will be deleted from the
            # SQS queue to prevent the same exception from happening in the
            # future.
            logging.warning(
                'Unexpected error while running the Analyze Filter for the '
                'object {}: {}'.format(created_object.key_name, exc),
            )
        try:
            self._upload_analysis_results(created_object.key_name)
        except Exception:
            logging.exception(
                'Unexpected error while uploading results for the '
                'object: {0}'.format(created_object.key_name),
            )

    def _extract_osxcollector_output_json_file(self):
        """Extracts JSON file containing the OSXCollector output from
        tar.gz archive. It will look in the archive contents for the
        file with the extension ".json". If no file with this extension
        is found in the archive or more than one JSON file is found, it
        will raise `OSXCollectorOutputExtractionError`.
        """
        # create a file-like object based on the S3 object contents as string
        fileobj = ByteBuffer(self._osxcollector_output)
        tar = tarfile.open(mode='r:gz', fileobj=fileobj)
        json_tarinfo = [t for t in tar if t.name.endswith('.json')]

        if 1 != len(json_tarinfo):
            raise OSXCollectorOutputExtractionError(
                'Expected 1 JSON file inside the OSXCollector output archive, '
                'but found {0} instead.'.format(len(json_tarinfo)),
            )

        tarinfo = json_tarinfo[0]
        self._osxcollector_output_json_file = tar.extractfile(tarinfo)
        logging.info(
            'Extracted OSXCollector output JSON file {0}'.format(tarinfo.name),
        )

    def _run_analyze_filter(self):
        """Runs Analyze Filter on the OSXCollector output retrieved
        from an S3 bucket.
        """
        self._analysis_output = StringBuffer()
        self._text_analysis_summary = ByteBuffer()
        self._html_analysis_summary = ByteBuffer()

        analyze_filter = AnalyzeFilter(
            monochrome=True,
            text_output_file=self._text_analysis_summary,
            html_output_file=self._html_analysis_summary,
        )

        output_filter._run_filter(
            analyze_filter,
            input_stream=self._osxcollector_output_json_file,
            output_stream=self._analysis_output,
        )

        # rewind the output files
        self._analysis_output.seek(0)
        self._text_analysis_summary.seek(0)
        self._html_analysis_summary.seek(0)

    @staticmethod
    def _check_buffer_size(buffer):
        buffer.seek(0, os.SEEK_END)
        size = buffer.tell()
        buffer.seek(0)
        return size

    def _upload_analysis_results(self, osxcollector_output_filename):
        # drop the file extension (".tar.gz")
        filename_without_extension = osxcollector_output_filename[:-7]

        analysis_output_filename = '{0}_analysis.json'.format(
            filename_without_extension,
        )
        text_analysis_summary_filename = '{0}_summary.txt'.format(
            filename_without_extension,
        )
        html_analysis_summary_filename = '{0}_summary.html'.format(
            filename_without_extension,
        )

        results = [
            FileMetaInfo(
                osxcollector_output_filename,
                ByteBuffer(self._osxcollector_output), 'application/gzip',
            ),
            FileMetaInfo(
                analysis_output_filename, self._analysis_output,
                'application/json',
            ),
            FileMetaInfo(
                text_analysis_summary_filename, self._text_analysis_summary,
                'text/plain',
            ),
            FileMetaInfo(
                html_analysis_summary_filename, self._html_analysis_summary,
                'text/html; charset=UTF-8',
            ),
        ]
        results = [res for res in results if AMIRA._check_buffer_size(res.content) > 0]

        for results_uploader in self._results_uploader:
            results_uploader.upload_results(results)


class OSXCollectorOutputExtractionError(Exception):
    """Raised when an unexpected number of JSON files is found in the
    OSXCollector output archive.
    """

    pass
