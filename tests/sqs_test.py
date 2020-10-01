# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import pytest
import simplejson
from mock import MagicMock
from mock import patch

from amira.sqs import SqsHandler


TEST_DATA_DIR_PATH = 'tests/data'


@pytest.fixture
def sqs_handler():
    with patch('amira.sqs.boto3') as mock_boto3:
        handler = SqsHandler('us-west-1', 'godzilla')
        mock_boto3.resource.assert_called_once_with('sqs', region_name='us-west-1')
        mock_boto3.resource.return_value.get_queue_by_name.assert_called_once_with(
            QueueName='godzilla',
        )
        yield handler


def read_s3_event_notifications_file(s3_event_notifications_file_path):
    with open(s3_event_notifications_file_path) as fp:
        s3_event_notifications = simplejson.load(fp)
        json_s3_event_notifications = [
            simplejson.dumps(s3_event_notification)
            for s3_event_notification in s3_event_notifications
        ]
    return json_s3_event_notifications


def create_s3_event_notification_message_mocks(s3_event_notifications_file_name):
    """Creates SQS queue message mocks that will return the JSON content of
    `s3_event_notifications_file_path` JSON file as the body of the message.
    """
    s3_event_notifications_file_path = '{0}/{1}'.format(
        TEST_DATA_DIR_PATH, s3_event_notifications_file_name,
    )
    json_s3_event_notifications = read_s3_event_notifications_file(
        s3_event_notifications_file_path,
    )
    return [
        MagicMock(body=json_s3_event_notification)
        for json_s3_event_notification in json_s3_event_notifications
    ]


def mock_s3_event_notifications(
        mock_sqs_queue, s3_event_notifications_file_name,
):
    """`SqsHandler.get_created_objects()` is a generator, so we need to
    mock multiple values returned by `get_messages()` method.
    In this case only one as the test cases do not operate on more than
    one message.
    """
    s3_event_notification_message_mocks = create_s3_event_notification_message_mocks(
        s3_event_notifications_file_name,
    )
    mock_sqs_queue.receive_messages.side_effect = [s3_event_notification_message_mocks]
    return s3_event_notification_message_mocks


class TestSqsHandler(object):

    def test_get_created_objects(self, sqs_handler):
        s3_event_notification_message_mocks = mock_s3_event_notifications(
            sqs_handler.sqs_queue, 's3_event_notifications.json',
        )
        created_objects = sqs_handler.get_created_objects()
        actual_key_names = [
            created_object.key_name
            for created_object in created_objects
        ]
        assert actual_key_names == [
            'AMIRA-1561-2016_01_11-10_54_07.tar.gz',
            'AMIRA-1562-2016_01_11-10_54_47.tar.gz',
            'AMIRA-1563-2016_01_11-10_54_58.tar.gz',
            'AMIRA-1564-2016_01_11-10_55_12.tar.gz',
            'AMIRA-1565-2016_01_11-10_55_32.tar.gz',
            'AMIRA-1566-2016_01_11-10_55_49.tar.gz',
            'AMIRA-1567-2016_01_11-10_56_09.tar.gz',
        ]
        for message_mock in s3_event_notification_message_mocks:
            message_mock.delete.assert_called_once_with()

    def test_get_created_objects_no_created_objects(self, sqs_handler):
        sqs_handler.sqs_queue.receive_messages.side_effect = [[]]
        created_objects = sqs_handler.get_created_objects()
        assert not list(created_objects)

    def test_get_created_objects_no_records(self, sqs_handler):
        """Tests the behavior of `get_created_objects()` method in case
        the message received from SQS does not contain the "Records"
        field in the message body.
        """
        mock_s3_event_notifications(
            sqs_handler.sqs_queue, 's3_test_event_notification.json',
        )
        assert not list(sqs_handler.get_created_objects())
