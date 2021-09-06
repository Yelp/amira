# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import logging

from amira.data_processor import OSXCollectorDataProcessor
from amira.s3 import S3Handler
from amira.sqs import SqsHandler


class AMIRA(object):
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
        self._data_feeds = {}
        self._data_processor = OSXCollectorDataProcessor()

    def register_results_uploader(self, results_uploader):
        """Registers results uploader.

        Results uploader will upload the analysis results and the
        summary to a specific destination after the analysis is
        finished.
        """
        self._results_uploader.append(results_uploader)

    def register_data_feed(self, feed_name, generator):
        """Register data input which to be used by the OsXCollector filters

        :param feed_name: Name of the data feed
        :param generator: Generator function providing the data
        """
        self._data_feeds[feed_name] = generator

    def register_data_processor(self, processor):
        """Registers DataProcessor object to process and analyze input data from S3.
        If no processor is registered Amira will fall back using the default
        OSXCollector result processor.

        :param processor: DataProcessor object instance
        """
        self._data_processor = processor

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
        # fetch forensic data from the S3 bucket
        forensic_output = self._s3_handler.get_contents_as_string(
            created_object.bucket_name, created_object.key_name,
        )

        try:
            processed_input = self._data_processor.process_input(forensic_output)
            if processed_input:
                self._data_processor.perform_analysis(processed_input, self._data_feeds)
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
            self._data_processor.upload_results(
                created_object.key_name[:-7], self._results_uploader,
            )
        except Exception:
            logging.exception(
                'Unexpected error while uploading results for the '
                'object: {0}'.format(created_object.key_name),
            )
