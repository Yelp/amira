from io import BytesIO
from io import StringIO
from typing import List
from typing import NamedTuple
from typing import Union


class FileMetaInfo(NamedTuple):
    name: str
    content: Union[StringIO, BytesIO]
    content_type: str


class ResultsUploader:
    """Parent class for the AMIRA results uploaders. Results uploaders
    should expose a single method, ``upload_results()``, that should
    take a list of ``FileMetaInfo`` tuples.
    """

    def upload_results(self, results: List[FileMetaInfo]) -> None:
        """Uploads the analysis results to a desired destination.

        :param results: The list containing the meta info (name,
                        content and content-type) of the files which
                        needs to be uploaded.
        :type results: list of ``FileMetaInfo`` tuples
        """
        raise NotImplementedError(
            'Derived classes must implement "upload_results()".',
        )
