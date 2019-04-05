# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import logging

import boto
from boto.s3.key import Key

from amira.results_uploader import ResultsUploader


class S3Handler():
    """Handles the operations with S3, like retrieving the key
    (object) contents from a bucket and creating a new key
    (object) with the contents of a given file.
    AWS and boto use the ambiguous term "key" to describe the objects
    inside the S3 bucket. They are unrelated to AWS keys used to access
    the resources.
    """

    def __init__(self):
        self._s3_connection = boto.connect_s3()

    def get_contents_as_string(self, bucket_name, key_name):
        """Retrieves the S3 key (object) contents.

        :param bucket_name: The S3 bucket name.
        :type bucket_name: string

        :param key_name: The S3 key (object) name.
        :type key_name: string

        :returns: The key (object) contents as a string.
        :rtype: string
        """
        bucket = self._s3_connection.get_bucket(bucket_name, validate=False)
        key = bucket.get_key(key_name)
        contents = key.get_contents_as_string()
        return contents


class S3ResultsUploader(ResultsUploader):
    """Uploads the analysis results to an S3 bucket.

    :param bucket_name: The name of the S3 bucket where the analysis
                        results will be uploaded.
    :type bucket_name: string
    """

    def __init__(self, bucket_name):
        self._bucket_name = bucket_name

        logging.info(
            'Connecting to S3 to obtain access to {0} bucket.'.format(
                bucket_name,
            ),
        )
        s3_connection = boto.connect_s3()
        self._bucket = s3_connection.get_bucket(bucket_name, validate=False)
        logging.info(
            'S3 bucket {0} retrieved successfully.'.format(
                bucket_name,
            ),
        )

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
            self._create_object_from_file(file_meta_info)

    def _create_object_from_file(self, file_meta_info):
        """Creates a new key (object) in the S3 bucket with the
        contents of a given file.
        """
        key = Key(self._bucket)
        key.key = file_meta_info.name
        key.set_contents_from_file(
            file_meta_info.content,
            headers={'Content-Type': file_meta_info.content_type},
        )
