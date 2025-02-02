# SPDX-License-Identifier: Apache-2.0
#
# Copyright (C) 2015, ARM Limited and contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os.path
import contextlib

from time import sleep

class TargetScript:
    """
    This class provides utility to create and run a script
    directly on a devlib target.

    :param target: Reference :class:`devlib.target.Target` instance. Will be
      used for some commands that must really be executed instead of accumulated.
    :type env: devlib.target.Target

    :param script_name: Name of the script that will be pushed on the target
    :type script_name: str

    :param local_dir: Local directory to use to prepare the script
    :type local_dir: str

    :meth:`execute` is made to look like Devlib's, so a Target instance can
    be swapped with an instance of this class, and the commands will be
    accumulated for later use instead of being executed straight away.
    """

    _target_attrs = ['screen_resolution', 'android_id', 'abi', 'os_version', 'model']

    def __init__(self, target, script_name='remote_script.sh', local_dir='./'):
        self.target = target

        self.script_name = script_name
        self.local_path = os.path.join(local_dir, script_name)
        self.remote_path = ""

        self.commands = []

        self._proc = None

    def execute(self, cmd):
        """
        Accumulate command for later execution.

        :param cmd: Command that would be run on the target
        :type cmd: str

        This is made to look like the devlib Target execute()
        """
        self.append(cmd)

    def append(self, cmd):
        """
        Append a command to the script.

        :param cmd: Command string to append
        :type cmd: str
        """
        self.commands.append(cmd)

    # Some commands may require some info about the real target.
    # For instance, System.{h,v}swipe needs to get the value of
    # screen_resolution to generate a swipe command at a given
    # screen coordinate percentage.
    # Thus, if such a property is called on this object,
    # it will be fetched from the 'real' target object.
    def __getattr__(self, name):
        # dunder name lookup would have succeeded by now, like __setstate__
        if not (name.startswith('__') and name.endswith('__')) \
            and name in self._target_attrs:
            return getattr(self.target, name)

        return super().__getattribute__(name)

    def push(self):
        """
        Push a script to the target

        The script is created and stored on the host, and is then sent
        to the target.
        """
        actions = ['set -e'] + self.commands + ['set +e']
        actions = ['#!{} sh'.format(self.target.busybox)] + actions
        actions = str.join('\n', actions)

        # Create script locally
        with open(self.local_path, 'w') as script:
            script.write(actions)

        # Push it on target
        self.remote_path = self.target.install(self.local_path)

    def _prerun_check(self):
        if not self.target.file_exists(self.remote_path):
            raise FileNotFoundError('Remote script was not found on target device')

    def run(self, as_root=False, timeout=None):
        """
        Run the previously pushed script

        :param as_root: Execute that script as root
        :type as_root: bool

        :param timeout: Timeout (in seconds) for the execution of the script
        :type timeout: int

        .. attention:: :meth:`push` must have been called beforehand
        """
        self._prerun_check()
        self.target.execute(self.remote_path, as_root=as_root, timeout=timeout)

    def background(self, as_root=False):
        """
        Non-blocking variant of :meth:`run`

        :param as_root: Execute that script as root
        :type as_root: bool

        :returns: the :class:`subprocess.Popen` instance for the command

        .. attention::

          You'll have to properly close the file descriptors used by
          :class:`subprocess.Popen`, for this we recommend using it as a context
          manager::

            with script.background():
                pass
        """
        self._prerun_check()
        self._proc = self.target.background(self.remote_path, as_root=as_root)

        return self._proc

    def wait(self, poll_sleep_s=1):
        """
        Wait for a script started via :meth:`background` to complete

        :param poll_sleep_s: Sleep duration between poll() calls
        :type poll_sleep_s: int

        :raises: :class:`devlib.exception.TargetNotRespondingError`
        """
        if not self._proc:
            raise RuntimeError('No background process currently executing')

        while self._proc.poll() is None:
            self.target.check_responsive(explode=True)
            sleep(poll_sleep_s)

    def kill(self, as_root=False):
        """
        Kill a script started via :meth:`background`

        :param as_root: Kill the script as root
        :type as_root: bool
        """
        if not self._proc:
            raise RuntimeError('No background process currently executing')

        cmd_pid = '$(pgrep -x {})'.format(self.script_name)
        self.target.kill(cmd_pid, as_root=as_root)
        self._proc.kill()

# vim :set tabstop=4 shiftwidth=4 textwidth=80 expandtab
