#!/usr/bin/env python3

import argparse
import logging
import logging.config
import os
import copy
import io
import sys
import time
import json
import threading
import http.client
import urllib
import pkg_resources

from datetime import datetime
from dateutil import tz

from strict_rfc3339 import rfc3339_to_timestamp

from jsonschema import Draft4Validator, validators, FormatChecker
from target_magentobi.client import Client
import singer

logger = singer.get_logger()


def write_last_state(states):
    logger.info('Persisted batch of {} records to Magento BI'.format(len(states)))
    last_state = None
    for state in reversed(states):
        if state is not None:
            last_state = state
            break
    if last_state:
        line = json.dumps(state)
        logger.debug('Emitting state {}'.format(line))
        sys.stdout.write("{}\n".format(line))
        sys.stdout.flush()


class DryRunClient(object):
    """A client that doesn't actually persist to the Gate.

    Useful for testing.
    """

    def __init__(self, buffer_size=100):
        self.pending_callback_args = []
        self.buffer_size = buffer_size


    def flush(self):
        logger.info("---- DRY RUN: NOTHING IS BEING PERSISTED TO MAGENTO BI ----")
        write_last_state(self.pending_callback_args)
        self.pending_callback_args = []

    def push(self, magentobi_record, table_name, callback_arg=None):
        self.pending_callback_args.append(callback_arg)

        if len(self.pending_callback_args) % self.buffer_size == 0:
            self.flush()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.flush()


def persist_lines(magentobiclient, lines):
    state = None
    schemas = {}
    key_properties = {}
    for line in lines:

        message = singer.parse_message(line)

        if isinstance(message, singer.RecordMessage):
            magentobi_record = message.record
            magentobi_record["keys"] = key_properties[message.stream]
            table_name = message.stream
            magentobiclient.push(magentobi_record, table_name, state)
            state = None

        elif isinstance(message, singer.StateMessage):
            state = message.value

        elif isinstance(message, singer.SchemaMessage):
            schemas[message.stream] = message.schema
            key_properties[message.stream] = message.key_properties

        else:
            raise Exception("Unrecognized message {} parsed from line {}".format(message, line))

    return state


def magentobi_client(args):
    """Returns an instance of MagentoBIClient or DryRunClient"""
    if args.dry_run:
        return DryRunClient()
    else:
        with open(args.config) as input:
            config = json.load(input)

        if not config.get('disable_collection', False):
            logger.info('Sending version information to stitchdata.com. ' +
                        'To disable sending anonymous usage data, set ' +
                        'the config parameter "disable_collection" to true')
            threading.Thread(target=collect).start()

        missing_fields = []

        if 'client_id' in config:
            client_id = config['client_id']
        else:
            missing_fields.append('client_id')

        if 'api_key' in config:
            api_key = config['api_key']
        else:
            missing_fields.append('api_key')

        if missing_fields:
            raise Exception('Configuration is missing required fields: {}'
                            .format(missing_fields))

        return Client(client_id, api_key, callback_function=write_last_state)

        
def collect():
    try:
        version = pkg_resources.get_distribution('target-magentobi').version
        conn = http.client.HTTPSConnection('collector.stitchdata.com', timeout=10)
        conn.connect()
        params = {
            'e': 'se',
            'aid': 'singer',
            'se_ca': 'target-magentobi',
            'se_ac': 'open',
            'se_la': version,
        }
        conn.request('GET', '/i?' + urllib.parse.urlencode(params))
        response = conn.getresponse()
        conn.close()
    except:
        logger.debug('Collection request failed')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help='Config file')
    parser.add_argument('-n', '--dry-run', help='Dry run - Do not push data to Magento BI', action='store_true')
    args = parser.parse_args()

    if not args.dry_run and args.config is None:
        parser.error("config file required if not in dry run mode")

    input = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    with magentobi_client(args) as client:
        state = persist_lines(client, input)
    write_last_state([state])
    logger.info("Exiting normally")


if __name__ == '__main__':
    main()
