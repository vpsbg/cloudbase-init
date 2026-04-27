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

import unittest
import unittest.mock as mock

from cloudbaseinit.plugins.common import base
from cloudbaseinit.plugins.windows import runonce
from cloudbaseinit.tests import testutils
from cloudbaseinit.utils import runonce as runonce_utils


class RunOncePluginTests(unittest.TestCase):

    def setUp(self):
        self._plugin = runonce.RunOncePlugin()

    @mock.patch('cloudbaseinit.osutils.factory.get_os_utils')
    def test_execute_first_boot(self, mock_get_os_utils):
        mock_osutils = mock.MagicMock()
        mock_get_os_utils.return_value = mock_osutils
        mock_osutils.get_smbios_uuid_serial.return_value = ('uuid-1',
                                                            'RESETAUTH')
        mock_osutils.get_config_value.return_value = None

        response = self._plugin.execute(mock.sentinel.service,
                                        mock.sentinel.shared_data)

        mock_osutils.set_config_value.assert_called_once_with(
            runonce_utils.SAVED_SMBIOS_UUID_KEY, 'uuid-1',
            runonce_utils.RUN_ONCE_SECTION)
        self.assertEqual((base.PLUGIN_EXECUTION_DONE, False), response)

    @testutils.ConfPatcher(
        'run_only_once_for',
        ['cloudbaseinit.plugins.common.sethostname.SetHostNamePlugin',
         'cloudbaseinit.plugins.common.setuserpassword.SetUserPasswordPlugin'])
    @testutils.ConfPatcher('run_once_reset_serial', 'RESETAUTH')
    @mock.patch('cloudbaseinit.osutils.factory.get_os_utils')
    def test_execute_clone_reset(self, mock_get_os_utils):
        mock_osutils = mock.MagicMock()
        mock_get_os_utils.return_value = mock_osutils
        mock_osutils.get_smbios_uuid_serial.return_value = ('uuid-2',
                                                            'RESETAUTH')

        def _get_config_value(name, section=None):
            if (name == runonce_utils.SAVED_SMBIOS_UUID_KEY and
                    section == runonce_utils.RUN_ONCE_SECTION):
                return 'uuid-1'
            return None

        mock_osutils.get_config_value.side_effect = _get_config_value

        response = self._plugin.execute(mock.sentinel.service,
                                        mock.sentinel.shared_data)

        expected_calls = [
            mock.call('cloudbaseinit.plugins.common.sethostname.'
                      'SetHostNamePlugin', 0, runonce_utils.RUN_ONCE_SECTION),
            mock.call('cloudbaseinit.plugins.common.setuserpassword.'
                      'SetUserPasswordPlugin', 0,
                      runonce_utils.RUN_ONCE_SECTION),
            mock.call(runonce_utils.SAVED_SMBIOS_UUID_KEY, 'uuid-2',
                      runonce_utils.RUN_ONCE_SECTION),
        ]
        mock_osutils.set_config_value.assert_has_calls(expected_calls)
        self.assertEqual((base.PLUGIN_EXECUTION_DONE, False), response)

    @testutils.ConfPatcher('run_only_once_for', [
        'cloudbaseinit.plugins.common.sethostname.SetHostNamePlugin'])
    @testutils.ConfPatcher('run_once_reset_serial', 'RESETAUTH')
    @mock.patch('cloudbaseinit.osutils.factory.get_os_utils')
    def test_execute_clone_no_reset_when_serial_does_not_match(
            self, mock_get_os_utils):
        mock_osutils = mock.MagicMock()
        mock_get_os_utils.return_value = mock_osutils
        mock_osutils.get_smbios_uuid_serial.return_value = ('uuid-2',
                                                            'OTHER')

        def _get_config_value(name, section=None):
            if (name == runonce_utils.SAVED_SMBIOS_UUID_KEY and
                    section == runonce_utils.RUN_ONCE_SECTION):
                return 'uuid-1'
            return None

        mock_osutils.get_config_value.side_effect = _get_config_value

        response = self._plugin.execute(mock.sentinel.service,
                                        mock.sentinel.shared_data)

        mock_osutils.set_config_value.assert_called_once_with(
            runonce_utils.SAVED_SMBIOS_UUID_KEY, 'uuid-2',
            runonce_utils.RUN_ONCE_SECTION)
        self.assertEqual((base.PLUGIN_EXECUTION_DONE, False), response)
