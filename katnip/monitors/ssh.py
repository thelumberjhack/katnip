# Copyright (C) 2016 Cisco Systems, Inc. and/or its affiliates. All rights reserved.
#
# This file is part of Katnip.
#
# Katnip is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Katnip is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Katnip.  If not, see <http://www.gnu.org/licenses/>.

import time

from kitty.monitors.base import BaseMonitor

import paramiko


class SSHMonitor(BaseMonitor):
    '''
    SSHMonitor monitors target ip
    and runs a command over SSH in case it is not responding.
    '''

    def __init__(self, name, username, password, hostname, port,
                 status_command, restart_command=None, logger=None):
        '''
        :param name: name of the object
        :param username: ssh login username
        :param password: ssh login password
        :param hostname: ssh server ip
        :param port: ssh server port
        :param status_command: command to make sure target is alive
        :param restart_command: command to restart the target in case it is deadore
        :param logger: logger for this object (default: None)
        '''
        super(SSHMonitor, self).__init__(name, logger)

        self._username = username
        self._password = password
        self._hostname = hostname
        self._port = port
        self._status_command = status_command
        self._restart_command = restart_command
        self._ssh = None

    def setup(self):
        super(SSHMonitor, self).setup()
        self._connect_ssh()

    def teardown(self):
        if self._ssh:
            self._ssh.close()
        self._ssh = None
        super(SSHMonitor, self).teardown()

    def _connect_ssh(self):
        if not self._ssh:
            self._ssh = paramiko.SSHClient()
            self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._ssh.connect(self._hostname, self._port, self._username, self._password)

    def _ssh_command(self, cmd):
        return_code = None
        try:
            self._connect_ssh()
            (self._stdin, self._stdout, self._stderr) = self._ssh.exec_command(cmd)
            return_code = self._stdout.channel.recv_exit_status()
            self.logger.debug("%s, %d" % (cmd, return_code))
        except KeyboardInterrupt:
            raise
        except Exception as e:
            self.logger.debug('SSHMonitor: ssh command exec error: %s' % str(e))
        return return_code

    def post_test(self):
        return_code = self._ssh_command(self._status_command)
        if return_code != 0:
            self.report.add('status_command', self._status_command)
            self.report.add('status_command return code', return_code)
            self.report.failed("got non-zero return code")
            if self._restart_command:
                self.logger.info('target not responding - restarting target !!!')
                return_code = self._ssh_command(self._restart_command)
                self.report.add('restart_command', self._restart_command)
                self.report.add('restart_command return code', return_code)
        super(SSHMonitor, self).post_test()

    def pre_test(self, test_number):
        super(SSHMonitor, self).pre_test(test_number)
        return_code = self._ssh_command(self._status_command)
        while return_code != 0:
            self.logger.debug('waiting for target to be up')
            time.sleep(1)

    def _monitor_func(self):
        '''
        Nothing is done here, so we use a sleep for now.
        '''
        time.sleep(0.1)
