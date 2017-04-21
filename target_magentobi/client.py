import os
import logging
import requests
import json
from target_magentobi.buffer import Buffer

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE_BYTES = 4194304
DEFAULT_BATCH_DELAY_MILLIS = 60000
DEFAULT_MAGENTOBI_URL = 'https://connect.rjmetrics.com/v2/'

class Client(object):

    _buffer = Buffer()

    def __init__(self,
                 client_id,
                 api_key,
                 table_name=None,
                 callback_function=None,
                 magentobi_url=DEFAULT_MAGENTOBI_URL,
                 batch_size_bytes=DEFAULT_BATCH_SIZE_BYTES,
                 batch_delay_millis=DEFAULT_BATCH_DELAY_MILLIS):

        assert isinstance(client_id, int), 'client_id is not an integer: {}'.format(client_id)  # nopep8

        self.client_id = client_id
        self.api_key = api_key
        self.table_name = table_name
        self.magentobi_url = magentobi_url
        self.batch_size_bytes = batch_size_bytes
        self.batch_delay_millis = batch_delay_millis
        self.callback_function = callback_function

    def push(self, magentobi_record, table_name, callback_arg=None):
        buffer_item = {}
        buffer_item["record"] = magentobi_record
        buffer_item["client_id"] = self.client_id
        buffer_item["table_name"] = table_name

        self._buffer.put(buffer_item, callback_arg)            

        batch = self._buffer.take(
            self.batch_size_bytes, self.batch_delay_millis)
        if batch is not None:
            self._send_batch(batch)

    def _magentobi_request(self, client_id, records, table_name):
        url = self.magentobi_url + "client/" + str(client_id) + "/table/" + str(table_name) + "/data?apikey=" + str(self.api_key)
        headers = {'Content-Type': 'application/json'}
        return requests.post(url, headers=headers, data=records)

    def _send_batch(self, batch):
        logger.debug("Sending batch of %s entries", len(batch))

        records = {}
        for entry in batch:
            client_id = entry.value["client_id"] #never changes
            table_name = entry.value["table_name"]
            if table_name not in records:
                records[table_name] = []
            records[table_name].append(entry.value["record"])
        for table_name, data in records.items():
            data = json.dumps(data) #up to this point, data is a list/dict, stringify for request
            response = self._magentobi_request(client_id, data, table_name)
            if response.status_code < 300:
                if self.callback_function is not None:
                    self.callback_function([x.callback_arg for x in batch])
            else:
                raise RuntimeError("Error sending data to the Magento BI API. {0.status_code} - {0.content}"  # nopep8
                                   .format(response))

    def flush(self):
        while True:
            batch = self._buffer.take(0, 0)
            if batch is None:
                return

            self._send_batch(batch)

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.flush()
