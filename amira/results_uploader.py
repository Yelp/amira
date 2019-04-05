# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from collections import namedtuple


FileMetaInfo = namedtuple('FileMetaInfo', ['name', 'content', 'content_type'])


class ResultsUploader():

    """Parent class for the AMIRA results uploaders. Results uploaders
    should expose a single method, ``upload_results()``, that should
    take a list of ``FileMetaInfo`` tuples.
    """

    def upload_results(self, results):
        """Uploads the analysis results to a desired destination.

        :param results: The list containing the meta info (name,
                        content and content-type) of the files which
                        needs to be uploaded.
        :type results: list of ``FileMetaInfo`` tuples
        """
        raise NotImplementedError(
            'Derived classes must implement "upload_results()".',
        )
