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

import collections
import re

from oslo_log import log as oslo_logging

from cloudbaseinit.models import network as network_model
from cloudbaseinit.utils import network


LOG = oslo_logging.getLogger(__name__)

NAME = "name"
MAC = "mac"
ADDRESS = "address"
ADDRESS6 = "address6"
NETMASK = "netmask"
NETMASK6 = "netmask6"
BROADCAST = "broadcast"
GATEWAY = "gateway"
GATEWAY6 = "gateway6"
DNSNS = "dnsnameservers"
DEFAULT_GATEWAY_CIDR_IPV4 = u"0.0.0.0/0"
DEFAULT_GATEWAY_CIDR_IPV6 = u"::/0"
# Fields of interest by regexps.
FIELDS = {
    NAME: re.compile(r"iface\s+(?P<{}>\S+)"
                     r"\s+inet6?\s+static".format(NAME)),
    MAC: re.compile(r"hwaddress\s+ether\s+"
                    r"(?P<{}>\S+)".format(MAC)),
    ADDRESS: re.compile(r"address\s+"
                        r"(?P<{}>\S+)".format(ADDRESS)),
    ADDRESS6: re.compile(r"post-up ip -6 addr add (?P<{}>[^/]+)/"
                         r"(\d+) dev".format(ADDRESS6)),
    NETMASK: re.compile(r"netmask\s+"
                        r"(?P<{}>\S+)".format(NETMASK)),
    NETMASK6: re.compile(r"post-up ip -6 addr add ([^/]+)/"
                         r"(?P<{}>\d+) dev".format(NETMASK6)),
    BROADCAST: re.compile(r"broadcast\s+"
                          r"(?P<{}>\S+)".format(BROADCAST)),
    GATEWAY: re.compile(r"gateway\s+"
                        r"(?P<{}>\S+)".format(GATEWAY)),
    GATEWAY6: re.compile(r"post-up ip -6 route add default via "
                         r"(?P<{}>.+) dev".format(GATEWAY6)),
    DNSNS: re.compile(r"dns-nameservers\s+(?P<{}>.+)".format(DNSNS))
}
IFACE_TEMPLATE = dict.fromkeys(FIELDS.keys())
# Map IPv6 availability by value index under `NetworkDetails`.
V6_PROXY = {
    ADDRESS: ADDRESS6,
    NETMASK: NETMASK6,
    GATEWAY: GATEWAY6,
    NAME: NAME,
    MAC: MAC,
}
DETAIL_PREPROCESS = {
    MAC: lambda value: value.upper(),
    DNSNS: lambda value: value.strip().split()
}


def _get_iface_blocks(data):
    """"Yield interface blocks as pairs of v4 and v6 halves."""
    iface_blocks = collections.OrderedDict()
    crt_lines = None
    for line in data.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("iface "):
            parts = line.split()
            if len(parts) >= 4 and parts[2] in ("inet", "inet6"):
                iface_name = parts[1]
                lines, lines6 = iface_blocks.setdefault(
                    iface_name, ([], []))
                crt_lines = lines6 if parts[2] == "inet6" else lines
            else:
                crt_lines = None
        if crt_lines is not None:
            crt_lines.append(line)
    for lines, lines6 in iface_blocks.values():
        if lines or lines6:
            yield lines, lines6


def _get_iface_stanzas(data):
    iface_stanzas = collections.OrderedDict()
    crt_stanza = None
    for line in data.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("iface "):
            parts = line.split()
            if len(parts) >= 4 and parts[2] in ("inet", "inet6"):
                iface_name = parts[1]
                crt_stanza = {
                    "family": parts[2],
                    "method": parts[3],
                    "lines": [line],
                }
                iface_stanzas.setdefault(iface_name, []).append(crt_stanza)
            else:
                crt_stanza = None
        elif crt_stanza is not None:
            crt_stanza["lines"].append(line)
    return iface_stanzas


def _get_field(line):
    for field, regex in FIELDS.items():
        match = regex.match(line)
        if match:
            yield field, match.group(field)


def _add_nic(iface, nics):
    if not iface or iface == IFACE_TEMPLATE:
        return    # no information gathered
    LOG.debug("Found new interface: %s", iface)
    # Each missing detail is marked as None.
    nic = network_model.NetworkDetails(**iface)
    nics.append(nic)


def parse(data):
    """Parse the received content and obtain network details."""
    if not data or not isinstance(data, str):
        LOG.error("Invalid Debian config to parse:\n%s", data)
        return

    LOG.info("Parsing Debian config...\n%s", data)
    nics = []    # list of NetworkDetails objects
    for lines_pair in _get_iface_blocks(data):
        iface = IFACE_TEMPLATE.copy()
        for lines, use_proxy in zip(lines_pair, (False, True)):
            for line in lines:
                for field, value in _get_field(line):
                    if use_proxy:
                        field = V6_PROXY.get(field)
                        if not field:
                            continue
                    func = DETAIL_PREPROCESS.get(field, lambda value: value)
                    iface[field] = func(value) if value != "None" else None
        _add_nic(iface, nics)

    return nics


def _parse_stanza_fields(stanza):
    iface = IFACE_TEMPLATE.copy()
    use_proxy = stanza["family"] == "inet6"
    for line in stanza["lines"]:
        for field, value in _get_field(line):
            if use_proxy:
                field = V6_PROXY.get(field, field)
            func = DETAIL_PREPROCESS.get(field, lambda value: value)
            iface[field] = func(value) if value != "None" else None
    return iface


def _get_default_gateway_cidr(address):
    if ":" in address:
        return DEFAULT_GATEWAY_CIDR_IPV6
    return DEFAULT_GATEWAY_CIDR_IPV4


def _get_stanza_network(stanza):
    if stanza["method"] != "static":
        return

    iface = _parse_stanza_fields(stanza)
    if stanza["family"] == "inet6":
        address = iface[ADDRESS6]
        netmask = iface[NETMASK6]
        gateway = iface[GATEWAY6]
    else:
        address = iface[ADDRESS]
        netmask = iface[NETMASK]
        gateway = iface[GATEWAY]

    if not address or not netmask:
        return

    routes = []
    if gateway:
        routes.append(network_model.Route(
            network_cidr=_get_default_gateway_cidr(address),
            gateway=gateway))

    return network_model.Network(
        link=iface[NAME],
        address_cidr=network.ip_netmask_to_cidr(address, netmask),
        dns_nameservers=iface[DNSNS],
        routes=routes)


def parse_v2(data):
    """Parse Debian network interfaces content as NetworkDetailsV2."""
    if not data or not isinstance(data, str):
        LOG.error("Invalid Debian config to parse:\n%s", data)
        return

    LOG.info("Parsing Debian config...\n%s", data)
    links = []
    networks = []
    services = []
    iface_stanzas = _get_iface_stanzas(data)
    for iface_name, stanzas in iface_stanzas.items():
        iface_networks = []
        for stanza in stanzas:
            net = _get_stanza_network(stanza)
            if net:
                iface_networks.append(net)
        if not iface_networks:
            continue

        mac_address = None
        for stanza in stanzas:
            fields = _parse_stanza_fields(stanza)
            if fields[MAC]:
                mac_address = fields[MAC]
                break

        links.append(network_model.Link(
            id=iface_name,
            name=iface_name,
            type=network_model.LINK_TYPE_PHYSICAL,
            enabled=None,
            mac_address=mac_address,
            mtu=None,
            bond=None,
            vlan_link=None,
            vlan_id=None))
        networks += iface_networks

    if not links and not networks:
        return

    return network_model.NetworkDetailsV2(
        links=links, networks=networks, services=services)
