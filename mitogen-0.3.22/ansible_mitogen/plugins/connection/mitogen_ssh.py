# Copyright 2019, David Wilson
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import os.path
import sys

from ansible.plugins.connection.ssh import (
    DOCUMENTATION as _ansible_ssh_DOCUMENTATION,
)

DOCUMENTATION = """
    name: mitogen_ssh
    author: David Wilson <dw@botanicus.net>
    short_description: Connect over SSH via Mitogen
    description:
        - This connects using an OpenSSH client controlled by the Mitogen for
          Ansible extension. It accepts every option the vanilla ssh plugin
          accepts.
    options:
""" + _ansible_ssh_DOCUMENTATION.partition('options:\n')[2]

try:
    import ansible_mitogen
except ImportError:
    base_dir = os.path.dirname(__file__)
    sys.path.insert(0, os.path.abspath(os.path.join(base_dir, '../../..')))
    del base_dir

import ansible_mitogen.connection
import ansible_mitogen.loaders


class Connection(ansible_mitogen.connection.Connection):
    transport = 'ssh'
    (vanilla_class, load_context) = ansible_mitogen.loaders.connection_loader__get_with_context(
        'ssh',
        class_only=True,
    )

    @staticmethod
    def _create_control_path(*args, **kwargs):
        """Forward _create_control_path() to the implementation in ssh.py."""
        # https://github.com/dw/mitogen/issues/342
        return Connection.vanilla_class._create_control_path(*args, **kwargs)
