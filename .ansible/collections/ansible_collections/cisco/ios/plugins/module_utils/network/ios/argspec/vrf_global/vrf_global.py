# -*- coding: utf-8 -*-
# Copyright 2024 Red Hat
# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

#############################################
#                WARNING                    #
#############################################
#
# This file is auto generated by the
# ansible.content_builder.
#
# Manually editing this file is not advised.
#
# To update the argspec make the desired changes
# in the documentation in the module file and re-run
# ansible.content_builder commenting out
# the path to external 'docstring' in build.yaml.
#
##############################################

"""
The arg spec for the ios_vrf_global module
"""


class Vrf_globalArgs(object):  # pylint: disable=R0903
    """The arg spec for the ios_vrf_global module"""

    argument_spec = {
        "config": {
            "type": "dict",
            "options": {
                "vrfs": {
                    "type": "list",
                    "elements": "dict",
                    "options": {
                        "name": {"type": "str", "required": True},
                        "description": {"type": "str"},
                        "ipv4": {
                            "type": "dict",
                            "options": {
                                "multicast": {
                                    "type": "dict",
                                    "options": {"multitopology": {"type": "bool"}},
                                },
                            },
                        },
                        "ipv6": {
                            "type": "dict",
                            "options": {
                                "multicast": {
                                    "type": "dict",
                                    "options": {"multitopology": {"type": "bool"}},
                                },
                            },
                        },
                        "rd": {"type": "str"},
                        "route_target": {
                            "type": "dict",
                            "options": {
                                "export": {"type": "str"},
                                "import_config": {"type": "str"},
                                "both": {"type": "str"},
                            },
                        },
                        "vnet": {
                            "type": "dict",
                            "options": {"tag": {"type": "int"}},
                        },
                        "vpn": {
                            "type": "dict",
                            "options": {"id": {"type": "str"}},
                        },
                    },
                },
            },
        },
        "running_config": {"type": "str"},
        "state": {
            "choices": [
                "parsed",
                "gathered",
                "deleted",
                "merged",
                "replaced",
                "rendered",
                "overridden",
                "purged",
            ],
            "default": "merged",
            "type": "str",
        },
    }  # pylint: disable=C0301
