# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import boto
import pytest
import simplejson
from mock import MagicMock

from amira.sqs import SqsHandler
from amira.sqs import SqsQueueNotFoundException


TEST_DATA_DIR_PATH = 'tests/data'


@pytest.fixture
def mock_sqs_queue():
    boto.sqs.connect_to_region = MagicMock()
    sqs_connection_mock = boto.sqs.connect_to_region.return_value
    return sqs_connection_mock.get_queue.return_value


def read_s3_event_notifications_file(s3_event_notifications_file_path):
    with open(s3_event_notifications_file_path) as fp:
        s3_event_notifications = simplejson.load(fp)
        json_s3_event_notifications = [
            simplejson.dumps(s3_event_notification)
            for s3_event_notification in s3_event_notifications
        ]
    return json_s3_event_notifications


def create_s3_event_notification_message_mocks(
        s3_event_notifications_file_name,
):
    """Creates SQS queue message mocks that will return the JSON content of
    `s3_event_notifications_file_path` JSON file as the body of the message.
    """
    s3_event_notifications_file_path = '{0}/{1}'.format(
        TEST_DATA_DIR_PATH, s3_event_notifications_file_name,
    )
    json_s3_event_notifications = read_s3_event_notifications_file(
        s3_event_notifications_file_path,
    )
    s3_event_notification_message_mocks = [
        MagicMock(**{'get_body.return_value': json_s3_event_notification})
        for json_s3_event_notification in json_s3_event_notifications
    ]
    return s3_event_notification_message_mocks


def mock_s3_event_notifications(
        mock_sqs_queue, s3_event_notifications_file_name,
):
    """`SqsHandler.get_created_objects()` is a generator, so we need to
    mock multiple values returned by `get_messages()` method.
    In this case only one as the test cases do not operate on more than
    one message.
    """
    s3_event_notification_message_mocks = \
        create_s3_event_notification_message_mocks(
            s3_event_notifications_file_name,
        )
    mock_sqs_queue.get_messages.side_effect = \
        [s3_event_notification_message_mocks]
    return s3_event_notification_message_mocks


class TestSqsHandler(object):

    def test_queue_not_found(self):
        boto.sqs.connect_to_region = MagicMock()
        sqs_connection_mock = boto.sqs.connect_to_region.return_value
        sqs_connection_mock.get_queue.return_value = None

        with pytest.raises(SqsQueueNotFoundException) as e:
            SqsHandler('us-west-1', 'godzilla')

        assert 'SQS queue godzilla not found.' == str(e.value)
        boto.sqs.connect_to_region.assert_called_once_with('us-west-1')
        sqs_connection_mock.get_queue.assert_called_once_with('godzilla')

    def test_get_created_objects(self, mock_sqs_queue):
        s3_event_notification_message_mocks = mock_s3_event_notifications(
            mock_sqs_queue, 's3_event_notifications.json',
        )
        sqs_handler = SqsHandler('us-west-1', 'godzilla')
        created_objects = sqs_handler.get_created_objects()
        actual_key_names = [
            created_object.key_name
            for created_object in created_objects
        ]

        expected_key_names = [
            'AMIRA-1561-2016_01_11-10_54_07.tar.gz',
            'AMIRA-1562-2016_01_11-10_54_47.tar.gz',
            'AMIRA-1563-2016_01_11-10_54_58.tar.gz',
            'AMIRA-1564-2016_01_11-10_55_12.tar.gz',
            'AMIRA-1565-2016_01_11-10_55_32.tar.gz',
            'AMIRA-1566-2016_01_11-10_55_49.tar.gz',
            'AMIRA-1567-2016_01_11-10_56_09.tar.gz',
        ]
        assert expected_key_names == actual_key_names

        mock_sqs_queue.delete_message_batch.assert_called_once_with(
            s3_event_notification_message_mocks,
        )

    def test_get_created_objects_no_created_objects(self, mock_sqs_queue):
        mock_sqs_queue.get_messages.side_effect = [[]]

        sqs_handler = SqsHandler('us-west-1', 'godzilla')
        created_objects = sqs_handler.get_created_objects()
        assert 0 == len(list(created_objects))

        assert mock_sqs_queue.delete_message_batch.called is False

    def test_get_created_objects_no_records(self, mock_sqs_queue):
        """Tests the behavior of `get_created_objects()` method in case
        the message received from SQS does not contain the "Records"
        field in the message body.
        """
        mock_s3_event_notifications(
            mock_sqs_queue, 's3_test_event_notification.json',
        )

        sqs_handler = SqsHandler('us-west-2', 'godzilla')
        created_objects = sqs_handler.get_created_objects()
        created_objects = list(created_objects)
        assert [] == created_objects
