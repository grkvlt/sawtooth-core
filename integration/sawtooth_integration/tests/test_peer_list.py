# Copyright 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------

import json
import time
import shlex
import logging
import unittest
import subprocess


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


EXPECTED = {
    0: {1},
    1: {0, 2, 3},
    2: {1, 4},
    3: {1, 4},
    4: {2, 3},
}


class TestPeerList(unittest.TestCase):
    def test_peer_list(self):
        '''Five validators are started, peered as described in EXPECTED (see
        the test's associated yaml file for details). First `sawtooth
        peer list` is run against each of them and the output is
        verified, then `sawnet peers list` is run against the whole
        network and the output is verified.

        '''

        # It would be preferable to use, as is normally done in
        # integration tests, `integration_tools.wait_for_rest_apis`
        # instead of a sleep. However, `wait_for_rest_apis` relies on
        # a call to `/blocks`, so if a validator doesn't have any
        # blocks, it won't respond even if it is ready. As of 12/7/17,
        # a network with no additional transactions won't properly
        # pass around the genesis block, so nodes not peering with the
        # genesis node won't have any blocks.
        time.sleep(10)

        # test `sawtooth peer list`
        for node_number, peer_numbers in EXPECTED.items():
            actual_peers = _get_peers(node_number)

            expected_peers = {
                _make_tcp_address(peer_number)
                for peer_number in peer_numbers
            }

            LOGGER.debug(
                'Actual: %s -- Expected: %s',
                actual_peers,
                expected_peers)

            self.assertEqual(
                actual_peers,
                expected_peers)

        # test `sawnet peers list`
        expected_network = {
            _make_http_address(node_number): [
                _make_tcp_address(peer_number)
                for peer_number in peers
            ]
            for node_number, peers in EXPECTED.items()
        }

        http_addresses = ','.join([
            _make_http_address(node_number)
            for node_number in EXPECTED
        ])

        # make sure pretty-print option works
        subprocess.run(shlex.split(
            'sawnet peers list {} --pretty'.format(http_addresses)))

        sawnet_peers_output = json.loads(
            _run_peer_command(
                'sawnet peers list {}'.format(http_addresses)
            )
        )

        self.assertEqual(
            sawnet_peers_output,
            expected_network)

        # run `sawnet peers graph`, but don't verify output
        subprocess.run(shlex.split(
            'sawnet peers graph {}'.format(http_addresses)))


def _get_peers(node_number, fmt='json'):
    cmd_output = _run_peer_command(
        'sawtooth peer list --url {} --format {}'.format(
            _make_http_address(node_number),
            fmt))

    LOGGER.debug('peer list output: %s', cmd_output)

    if fmt == 'json':
        parsed = json.loads(cmd_output)

    elif fmt == 'csv':
        parsed = cmd_output.split(',')

    return set(parsed)


def _run_peer_command(command):
    return subprocess.check_output(
        shlex.split(command)
    ).decode().strip().replace("'", '"')


def _make_http_address(node_number):
    return 'http://rest-api-{}:8008'.format(node_number)


def _make_tcp_address(node_number):
    return 'tcp://validator-{}:8800'.format(node_number)
