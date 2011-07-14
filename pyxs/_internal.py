# -*- coding: utf-8 -*-
"""
    pyxs._internal
    ~~~~~~~~~~~~~~

    A place for secret stuff, not available in the public API.

    :copyright: (c) 2011 by Selectel, see AUTHORS for more details.
"""

from __future__ import unicode_literals

__all__ = ["Event", "Op", "Packet"]

import re
import struct
from collections import namedtuple

from .exceptions import InvalidOperation, InvalidPayload


#: Operations supported by XenStore.
Operations = Op = namedtuple("Operations", [
    "DEBUG",
    "DIRECTORY",
    "READ",
    "GET_PERMS",
    "WATCH",
    "UNWATCH",
    "TRANSACTION_START",
    "TRANSACTION_END",
    "INTRODUCE",
    "RELEASE",
    "GET_DOMAIN_PATH",
    "WRITE",
    "MKDIR",
    "RM",
    "SET_PERMS",
    "WATCH_EVENT",
    "ERROR",
    "IS_DOMAIN_INTRODUCED",
    "RESUME",
    "SET_TARGET",
    "RESTRICT"
])(*(range(20) + [128]))


Event = namedtuple("Event", "path token")


class Packet(namedtuple("_Packet", "op rq_id tx_id size payload")):
    """A single message to or from XenStore.

    :param int op: an item from :data:`Op`, representing
                   operation, performed by this packet.
    :param bytes payload: packet payload, should be a valid ASCII-string
                          with characters between ``[0x20;0x7f]``.
    :param int rq_id: request id -- hopefuly a **unique** identifier
                      for this packet, XenStore simply echoes this value
                      back in reponse.
    :param int tx_id: transaction id, defaults to ``0`` -- which means
                      no transaction is running.
    """
    #: ``xsd_sockmsg`` struct see ``xen/include/public/io/xs_wire.h``
    #: for details.
    _struct = struct.Struct(b"IIII")

    def __new__(cls, op, payload, rq_id=None, tx_id=None):
        if isinstance(payload, unicode):
            payload = payload.encode("utf-8")

        # Checking restrictions:
        # a) payload is limited to 4096 bytes.
        if len(payload) > 4096:
            raise InvalidPayload(payload)
        # b) operation requested is present in ``xsd_sockmsg_type``.
        if op not in Op:
            raise InvalidOperation(op)

        return super(Packet, cls).__new__(cls,
            op, rq_id or 0, tx_id or 0 , len(payload), payload)

    def __str__(self):
        # Note the ``[:-1]`` slice -- the actual payload is excluded.
        return self._struct.pack(*self[:-1]) + self.payload

    def __nonzero__(self):
        return not re.match(r"^E[A-Z]+\x00$", self.payload)

    @classmethod
    def from_string(cls, s):
        """Creates a :class:`Packet` from a given string.

        .. note:: The caller is responsible for handling any possible
                  exceptions.
        """
        if isinstance(s, unicode):
            s = s.encode("utf-8")

        (op,
         rq_id, tx_id,
         size) = map(int, cls._struct.unpack(s[:cls._struct.size]))
        return cls(op, s[-size:], rq_id, tx_id)

    @classmethod
    def from_file(cls, f):
        """Creates a :class:`Packet` from a give file-like object.

        .. note:: The caller is responsible for handling any possible
                  exceptions.
        """
        (op,
         rq_id, tx_id,
         size) = map(int, cls._struct.unpack(f.read(cls._struct.size)))
        return cls(op, f.read(size), rq_id, tx_id)
