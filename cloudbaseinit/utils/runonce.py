# Copyright 2026 Cloudbase Solutions Srl
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

from cloudbaseinit import conf as cloudbaseinit_conf
from cloudbaseinit.plugins import factory as plugins_factory


CONF = cloudbaseinit_conf.CONF

RUN_ONCE_SECTION = "RunOnce"
SAVED_SMBIOS_UUID_KEY = "SmbiosUuid"
SAVED_METADATA_INSTANCE_ID_KEY = "MetadataInstanceId"


def normalize_plugin_path(class_path):
    return plugins_factory.OLD_PLUGINS.get(class_path, class_path)


def get_plugin_class_path(plugin):
    return normalize_plugin_path("%s.%s" % (plugin.__class__.__module__,
                                           plugin.__class__.__name__))


def get_run_once_plugins():
    return {normalize_plugin_path(class_path)
            for class_path in CONF.run_only_once_for}
