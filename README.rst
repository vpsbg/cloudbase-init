Portable Multi-Cloud Initialization Service
===========================================

* Author:         Cloudbase Solutions Srl
* Contact:        info@cloudbasesolutions.com
* Home page:      http://www.cloudbase.it/cloud-init-windows/

* Documentation:  http://cloudbase-init.readthedocs.org/en/latest/
* Source:         https://github.com/openstack/cloudbase-init
* License:        Apache 2.0


Fork Notice
-----------

This repository is a downstream fork of the upstream Cloudbase-Init project:

https://github.com/cloudbase/cloudbase-init

We maintain this fork in order to support our Windows VM provisioning workflow
and to publish the exact code that is deployed on customer systems for
transparency and reviewability.

The goal is to keep the fork as close as possible to upstream while carrying a
small set of targeted changes required by our environment.

Active patch branch::

    proxmox-provisioning-1.1.8 for Cloudbase-Init 1.1.8

This branch carries the downstream patch set used for Windows VM provisioning
with Proxmox Cloud-Init metadata:

* support multiple IPv4 and IPv6 addresses per adapter from Cloud-Init network
  metadata;
* parse Debian ``network-interfaces`` content into the newer network details
  model when native v2 network metadata is not present;
* configure multiple static addresses per Windows network adapter;
* add run-once plugin state with SMBIOS UUID tracking and serial-gated reset
  support for cloned VMs;
* allow selected plugins to run once per machine, independently of metadata
  instance id changes;
* run volume extension before metadata discovery.

For the original project documentation and general Cloudbase-Init usage, please
refer to the upstream repository.


Downloads
---------

Stable
~~~~~~

* (64bit) https://www.cloudbase.it/downloads/CloudbaseInitSetup_Stable_x64.msi
* (32bit) https://www.cloudbase.it/downloads/CloudbaseInitSetup_Stable_x86.msi

Beta
~~~~

* (64bit) https://www.cloudbase.it/downloads/CloudbaseInitSetup_x64.msi
* (32bit) https://www.cloudbase.it/downloads/CloudbaseInitSetup_x86.msi


Got a question?
---------------

Visit http://ask.cloudbase.it/questions/
