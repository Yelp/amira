# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import logging
from collections import namedtuple

import boto.sqs
import simplejson
from boto.sqs.message import RawMessage


# 10 is the maximum number of messages to read at once:
# http://docs.aws.amazon.com/AWSSimpleQueueService/latest/APIReference/API_ReceiveMessage.html
MAX_NUMBER_MESSAGES = 10


CreatedObject = namedtuple('ObjectCreated', ['bucket_name', 'key_name'])


class SqsHandler():
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

    def __init__(self, region_name, queue_name):
        self._setup_sqs_queue(region_name, queue_name)

    def _setup_sqs_queue(self, region_name, queue_name):
        """Connects to the SQS queue in a given AWS region.

        :param region_name: The AWS region name.
        :type region_name: string
        :param queue_name: The SQS queue name.
        :type queue_name: string
        """
        sqs_connection = boto.sqs.connect_to_region(region_name)
        self.sqs_queue = sqs_connection.get_queue(queue_name)

        if not self.sqs_queue:
            raise SqsQueueNotFoundException(queue_name)

        logging.info(
            'Successfully connected to {0} SQS queue'.format(
                queue_name,
            ),
        )

        self.sqs_queue.set_message_class(RawMessage)

    def get_created_objects(self):
        """Retrieves the S3 event notifications about the objects
        created in the OSXCollector output bucket yields the (bucket
        name, key name) pairs describing these objects.
        """
        messages = self.sqs_queue.get_messages(MAX_NUMBER_MESSAGES)
        logging.info(
            'Received {0} message(s) from the SQS queue'.format(
                len(messages),
            ),
        )

        if messages:
            for message in messages:
                objects_created = self._retrieve_created_objects_from_message(
                    message,
                )

                for object_created in objects_created:
                    yield object_created

            self.sqs_queue.delete_message_batch(messages)

    def _retrieve_created_objects_from_message(self, message):
        """Retrieves the bucket name and the key name, describing the
        created object, from the `Records` array in the SQS message.

        Yields each (bucket name, key name) pair as an `CreatedObject`
        named tuple.

        :param message: The SQS message. It should be in the JSON
                        format.
        :type message: string
        """
        json_body = message.get_body()
        body = simplejson.loads(json_body)

        if 'Records' not in body:
            logging.warn(
                '"Records" field not found in the SQS message. '
                'Message body: {0}'.format(body),
            )
            return []

        records = body['Records']
        return self._extract_created_objects_from_records(records)

    def _extract_created_objects_from_records(self, records):
        logging.info(
            'Found {0} record(s) in the SQS message'.format(len(records)),
        )

        for record in records:
            bucket_name = record['s3']['bucket']['name']
            key_name = record['s3']['object']['key']
            yield CreatedObject(bucket_name=bucket_name, key_name=key_name)


class SqsQueueNotFoundException(Exception):
    """An exception thrown when the SQS queue cannot be found."""

    def __init__(self, queue_name):
        self.queue_name = queue_name

    def __str__(self):
        return 'SQS queue {0} not found.'.format(self.queue_name)
