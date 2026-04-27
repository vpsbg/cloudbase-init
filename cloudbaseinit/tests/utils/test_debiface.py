# Copyright 2014 Cloudbase Solutions Srl
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


import unittest

from cloudbaseinit.models import network as network_model
from cloudbaseinit.tests.metadata import fake_json_response
from cloudbaseinit.tests import testutils
from cloudbaseinit.utils import debiface


class TestInterfacesParser(unittest.TestCase):

    def setUp(self):
        date = "2013-04-04"
        content = fake_json_response.get_fake_metadata_json(date)
        self.data = content["network_config"]["debian_config"]

    def _test_parse_nics(self, no_nics=False):
        with testutils.LogSnatcher('cloudbaseinit.utils.'
                                   'debiface') as snatcher:
            nics = debiface.parse(self.data)

        if no_nics:
            expected_logging = 'Invalid Debian config to parse:'
            self.assertTrue(snatcher.output[0].startswith(expected_logging))
            self.assertFalse(nics)
            return
        # check what we've got
        nic0 = network_model.NetworkDetails(
            fake_json_response.NAME0,
            fake_json_response.MAC0.upper(),
            fake_json_response.ADDRESS0,
            fake_json_response.ADDRESS60,
            fake_json_response.NETMASK0,
            fake_json_response.NETMASK60,
            fake_json_response.BROADCAST0,
            fake_json_response.GATEWAY0,
            fake_json_response.GATEWAY60,
            fake_json_response.DNSNS0.split()
        )
        nic1 = network_model.NetworkDetails(
            fake_json_response.NAME1,
            None,
            fake_json_response.ADDRESS1,
            fake_json_response.ADDRESS61,
            fake_json_response.NETMASK1,
            fake_json_response.NETMASK61,
            fake_json_response.BROADCAST1,
            fake_json_response.GATEWAY1,
            fake_json_response.GATEWAY61,
            None
        )
        nic2 = network_model.NetworkDetails(
            fake_json_response.NAME2,
            None,
            fake_json_response.ADDRESS2,
            fake_json_response.ADDRESS62,
            fake_json_response.NETMASK2,
            fake_json_response.NETMASK62,
            fake_json_response.BROADCAST2,
            fake_json_response.GATEWAY2,
            fake_json_response.GATEWAY62,
            None
        )
        self.assertEqual([nic0, nic1, nic2], nics)

    def test_nothing_to_parse(self):
        invalid = [None, "", 324242, ("dasd", "dsa")]
        for data in invalid:
            self.data = data
            self._test_parse_nics(no_nics=True)

    def test_parse(self):
        self._test_parse_nics()

    def test_parse_split_inet6_stanza(self):
        data = """
auto eth0
iface eth0 inet static
    address 192.0.2.10
    netmask 255.255.255.255
    gateway 172.16.0.1
    dns-nameservers 1.1.1.1 9.9.9.9
iface eth0 inet6 static
    address 2001:db8:589::
    netmask 64
    gateway fe80::1
    dns-nameservers 1.1.1.1 9.9.9.9
        """

        nic = network_model.NetworkDetails(
            "eth0",
            None,
            "192.0.2.10",
            "2001:db8:589::",
            "255.255.255.255",
            "64",
            None,
            "172.16.0.1",
            "fe80::1",
            ["1.1.1.1", "9.9.9.9"]
        )

        self.assertEqual([nic], debiface.parse(data))

    def test_parse_v2_multiple_addresses(self):
        data = """
auto eth0
iface eth0 inet static
    address 91.92.66.16
    netmask 255.255.255.255
    gateway 172.16.0.1
    dns-nameservers 1.1.1.1 9.9.9.9
iface eth0 inet static
    address 91.92.66.10
    netmask 255.255.255.255
    dns-nameservers 1.1.1.1 9.9.9.9
iface eth0 inet static
    address 87.120.37.168
    netmask 255.255.255.255
    dns-nameservers 1.1.1.1 9.9.9.9
iface eth0 inet6 static
    address 2a00:1728:f:0589::
    netmask 64
    gateway fe80::1
    dns-nameservers 1.1.1.1 9.9.9.9
        """
        expected_link = network_model.Link(
            id="eth0",
            name="eth0",
            type=network_model.LINK_TYPE_PHYSICAL,
            enabled=None,
            mac_address=None,
            mtu=None,
            bond=None,
            vlan_link=None,
            vlan_id=None)
        expected_networks = [
            network_model.Network(
                link="eth0",
                address_cidr="91.92.66.16/32",
                dns_nameservers=["1.1.1.1", "9.9.9.9"],
                routes=[network_model.Route(
                    network_cidr="0.0.0.0/0",
                    gateway="172.16.0.1")]),
            network_model.Network(
                link="eth0",
                address_cidr="91.92.66.10/32",
                dns_nameservers=["1.1.1.1", "9.9.9.9"],
                routes=[]),
            network_model.Network(
                link="eth0",
                address_cidr="87.120.37.168/32",
                dns_nameservers=["1.1.1.1", "9.9.9.9"],
                routes=[]),
            network_model.Network(
                link="eth0",
                address_cidr="2a00:1728:f:0589::/64",
                dns_nameservers=["1.1.1.1", "9.9.9.9"],
                routes=[network_model.Route(
                    network_cidr="::/0",
                    gateway="fe80::1")]),
        ]

        network_details = debiface.parse_v2(data)

        self.assertEqual([expected_link], network_details.links)
        self.assertEqual(expected_networks, network_details.networks)
        self.assertEqual([], network_details.services)
