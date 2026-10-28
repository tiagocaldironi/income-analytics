"""Process-wide offline guard, inherited by Python subprocesses in CI only."""

import os

if os.environ.get("INCOME_CI_OFFLINE") == "1":
    import socket
    import threading

    _internal = threading.local()
    _socketpair = socket.socketpair

    def _pair(*args, **kwargs):
        # Windows/asyncio may implement its internal wake-up pipe with TCP.
        _internal.socketpair = True
        try:
            return _socketpair(*args, **kwargs)
        finally:
            _internal.socketpair = False

    socket.socketpair = _pair
    _connect = socket.socket.connect
    _connect_ex = socket.socket.connect_ex

    def _blocked_connect(self, address):
        if getattr(_internal, "socketpair", False):
            return _connect(self, address)
        raise RuntimeError("CI_OFFLINE_NETWORK_BLOCKED")

    def _blocked_connect_ex(self, address):
        if getattr(_internal, "socketpair", False):
            return _connect_ex(self, address)
        raise RuntimeError("CI_OFFLINE_NETWORK_BLOCKED")

    socket.socket.connect = _blocked_connect
    socket.socket.connect_ex = _blocked_connect_ex
    _getaddrinfo = socket.getaddrinfo

    def _blocked_dns(host, *args, **kwargs):
        if getattr(_internal, "socketpair", False):
            return _getaddrinfo(host, *args, **kwargs)
        raise RuntimeError("CI_OFFLINE_NETWORK_BLOCKED")

    socket.getaddrinfo = _blocked_dns

    def _blocked_datagram(*args, **kwargs):
        raise RuntimeError("CI_OFFLINE_NETWORK_BLOCKED")

    socket.socket.sendto = _blocked_datagram
