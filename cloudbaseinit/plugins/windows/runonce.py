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

from oslo_log import log as oslo_logging

from cloudbaseinit import conf as cloudbaseinit_conf
from cloudbaseinit.osutils import factory as osutils_factory
from cloudbaseinit.plugins.common import base
from cloudbaseinit.utils import runonce as runonce_utils


CONF = cloudbaseinit_conf.CONF
LOG = oslo_logging.getLogger(__name__)


class RunOncePlugin(base.BasePlugin):
    execution_stage = base.PLUGIN_STAGE_PRE_METADATA_DISCOVERY

    @staticmethod
    def _normalize_value(value):
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    def _reset_run_once_plugins(self, osutils):
        run_once_plugins = sorted(runonce_utils.get_run_once_plugins())
        for class_path in run_once_plugins:
            osutils.set_config_value(class_path, 0,
                                     runonce_utils.RUN_ONCE_SECTION)
        if run_once_plugins:
            LOG.info("Reset run-once plugin state for: %s",
                     ", ".join(run_once_plugins))

    def _log_smbios_changes(self, saved_uuid, current_uuid, current_serial):
        if saved_uuid:
            if current_uuid.casefold() != saved_uuid.casefold():
                LOG.info("SMBIOS UUID changed. Previous=%s Current=%s",
                         saved_uuid, current_uuid)
            else:
                LOG.debug("SMBIOS UUID unchanged: %s", current_uuid)
        else:
            LOG.debug("No saved SMBIOS UUID found. Treating current SMBIOS "
                      "UUID as the first observed value: %s", current_uuid)

        if current_serial:
            LOG.debug("Current SMBIOS serial: %s", current_serial)
        else:
            LOG.debug("SMBIOS serial not available")

    def execute(self, service, shared_data):
        osutils = osutils_factory.get_os_utils()
        current_uuid, current_serial = osutils.get_smbios_uuid_serial()
        current_uuid = self._normalize_value(current_uuid)
        current_serial = self._normalize_value(current_serial)
        reset_serial = self._normalize_value(CONF.run_once_reset_serial)
        run_once_plugins = sorted(runonce_utils.get_run_once_plugins())

        if not current_uuid:
            LOG.debug("SMBIOS UUID not available, skipping run-once reset "
                      "checks")
            return base.PLUGIN_EXECUTION_DONE, False

        saved_uuid = self._normalize_value(osutils.get_config_value(
            runonce_utils.SAVED_SMBIOS_UUID_KEY, runonce_utils.RUN_ONCE_SECTION
        ))

        LOG.debug("Run-once reset context: saved SMBIOS UUID=%s, current "
                  "SMBIOS UUID=%s, current SMBIOS serial=%s, configured "
                  "reset serial=%s",
                  saved_uuid, current_uuid, current_serial, reset_serial)
        LOG.debug("Configured run-once plugins: %s",
                  ", ".join(run_once_plugins) if run_once_plugins else
                  "<none>")
        self._log_smbios_changes(saved_uuid, current_uuid, current_serial)

        if saved_uuid and current_uuid.casefold() != saved_uuid.casefold():
            if (reset_serial and current_serial and
                    current_serial.casefold() == reset_serial.casefold()):
                LOG.info("SMBIOS UUID changed and reset serial matched. "
                         "Resetting configured run-once plugins")
                self._reset_run_once_plugins(osutils)
                if run_once_plugins:
                    LOG.info("The following run-once plugins are now "
                             "eligible to rerun: %s",
                             ", ".join(run_once_plugins))
            else:
                LOG.info("SMBIOS UUID changed but reset serial did not "
                         "match. Preserving run-once plugin state")
        elif saved_uuid:
            LOG.debug("SMBIOS clone identity unchanged. Preserving run-once "
                      "plugin state")

        if saved_uuid != current_uuid:
            osutils.set_config_value(runonce_utils.SAVED_SMBIOS_UUID_KEY,
                                     current_uuid,
                                     runonce_utils.RUN_ONCE_SECTION)
            LOG.debug("Stored SMBIOS UUID for future clone detection: %s",
                      current_uuid)

        return base.PLUGIN_EXECUTION_DONE, False

    def get_os_requirements(self):
        return 'win32', (5, 2)
