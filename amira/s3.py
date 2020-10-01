# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import logging

try:
    from cStringIO import StringIO as ByteBuffer
    from cStringIO import StringIO as StringBuffer
    IN_PY3 = False
except ImportError:
    from io import BytesIO as ByteBuffer
    from io import StringIO as StringBuffer
    IN_PY3 = True

import boto3

from amira.results_uploader import ResultsUploader


class S3Handler(object):
    """Handles the operations with S3, like retrieving the key
    (object) contents from a bucket and creating a new key
    (object) with the contents of a given file.
    AWS uses the ambiguous term "key" to describe the objects
    inside the S3 bucket. They are unrelated to AWS keys used to access
    the resources.
    """

    def __init__(self):
        self._s3_connection = boto3.client('s3')

    def get_contents_as_string(self, bucket_name, key_name):
        """Retrieves the S3 key (object) contents.

        :param bucket_name: The S3 bucket name.
        :type bucket_name: string
        :param key_name: The S3 key (object) name.
        :type key_name: string
        :returns: The key (object) contents as a bytes (str in py2).
        :rtype: bytes
        """
        response = self._s3_connection.get_object(Bucket=bucket_name, Key=key_name)
        return response['Body'].read()


class S3ResultsUploader(ResultsUploader):
    """Uploads the analysis results to an S3 bucket.

    :param bucket_name: The name of the S3 bucket where the analysis
                        results will be uploaded.
    :type bucket_name: string
    """

    def __init__(self, bucket_name):
        self._bucket_name = bucket_name
        self._s3_connection = boto3.client('s3')

    def upload_results(self, results):
        """Uploads the analysis results to an S3 bucket.

        :param results: The list containing the meta info (name,
                        content and content-type) of the files which
                        needs to be uploaded.
        :type results: list of ``FileMetaInfo`` tuples
        """
        for file_meta_info in results:
            logging.info(
                'Uploading the analysis results in the file "{0}" to the S3 '
                'bucket "{1}"'.format(file_meta_info.name, self._bucket_name),
            )
            body = (
                ByteBuffer(file_meta_info.content.getvalue().encode())
                if IN_PY3 and isinstance(file_meta_info.content, StringBuffer)
                else file_meta_info.content
            )
            self._s3_connection.put_object(
                Bucket=self._bucket_name,
                Key=file_meta_info.name,
                ContentType=file_meta_info.content_type,
                Body=body,
            )
