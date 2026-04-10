import json
import logging
from typing import Any
from typing import Dict
from typing import Generator
from typing import Iterable
from typing import List
from typing import NamedTuple

import boto3


# 10 is the maximum number of messages to read at once:
# http://docs.aws.amazon.com/AWSSimpleQueueService/latest/APIReference/API_ReceiveMessage.html
MAX_NUMBER_MESSAGES = 10


class CreatedObject(NamedTuple):
    bucket_name: str
    key_name: str


class SqsHandler:
    """Retrieves the S3 event notifications about the objects created
    in the bucket for which the notifications were configured.

    :param region_name: The AWS region name where the SQS queue
                        containing the S3 event notifications is
                        configured.
    :type region_name: string
    :param queue_name: The name of the SQS queue containing the S3
                       event notifications.
    :type queue_name: string
    """

    def __init__(self, region_name: str, queue_name: str) -> None:
        """Connects to the SQS queue in a given AWS region.

        :param region_name: The AWS region name.
        :type region_name: string
        :param queue_name: The SQS queue name.
        :type queue_name: string
        """
        sqs_connection = boto3.resource("sqs", region_name=region_name)
        self.sqs_queue = sqs_connection.get_queue_by_name(QueueName=queue_name)
        logging.info(
            "Successfully connected to {} SQS queue".format(queue_name),
        )

    def get_created_objects(self) -> Generator[CreatedObject, None, None]:
        """Retrieves the S3 event notifications about the objects
        created in the OSXCollector output bucket yields the (bucket
        name, key name) pairs describing these objects.
        """
        messages = self.sqs_queue.receive_messages(
            MaxNumberOfMessages=MAX_NUMBER_MESSAGES,
        )
        logging.info(
            "Received {} message(s) from the SQS queue".format(len(messages)),
        )
        if messages:
            for message in messages:
                objects_created = self._retrieve_created_objects_from_message(message)
                yield from objects_created
                message.delete()

    def _retrieve_created_objects_from_message(
        self,
        message: Any,
    ) -> Iterable[CreatedObject]:
        """Retrieves the bucket name and the key name, describing the
        created object, from the `Records` array in the SQS message.

        Yields each (bucket name, key name) pair as an `CreatedObject`
        named tuple.

        :param message: The SQS message. It should be in the JSON
                        format.
        :type message: string
        """
        body = json.loads(message.body)
        if "Records" not in body:
            logging.warning(
                '"Records" field not found in the SQS message. '
                "Message body: {}".format(body),
            )
            return []
        return self._extract_created_objects_from_records(body["Records"])

    def _extract_created_objects_from_records(
        self,
        records: List[Dict[str, Any]],
    ) -> Generator[CreatedObject, None, None]:
        logging.info(
            "Found {} record(s) in the SQS message".format(len(records)),
        )
        for record in records:
            bucket_name = record["s3"]["bucket"]["name"]
            key_name = record["s3"]["object"]["key"]
            yield CreatedObject(bucket_name=bucket_name, key_name=key_name)
