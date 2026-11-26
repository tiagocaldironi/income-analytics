"""Uvicorn entry point with a per-port, same-session graceful shutdown event."""

from __future__ import annotations

import argparse
import ctypes
import os
import sys
import threading
from pathlib import Path

import uvicorn

EVENT_MODIFY_STATE = 0x0002
SYNCHRONIZE = 0x00100000
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 258


def event_name(port: int) -> str:
    if not 1 <= port <= 65535:
        raise ValueError("INVALID_SERVER_PORT")
    return rf"Local\IncomeAnalytics-Uvicorn-{port}"


def request_shutdown(port: int) -> bool:
    """Signal only this user's per-port server; never terminate its process."""
    if os.name != "nt":
        raise RuntimeError("WINDOWS_SHUTDOWN_EVENT_REQUIRED")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenEventW.argtypes = [ctypes.c_uint, ctypes.c_bool, ctypes.c_wchar_p]
    kernel.OpenEventW.restype = ctypes.c_void_p
    kernel.SetEvent.argtypes = [ctypes.c_void_p]
    kernel.SetEvent.restype = ctypes.c_bool
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenEventW(EVENT_MODIFY_STATE | SYNCHRONIZE, False, event_name(port))
    if not handle:
        error = ctypes.get_last_error()
        if error == 2:
            return False
        raise OSError(error, "OpenEventW failed")
    try:
        if not kernel.SetEvent(handle):
            raise OSError(ctypes.get_last_error(), "SetEvent failed")
        return True
    finally:
        kernel.CloseHandle(handle)


class ShutdownEvent:
    def __init__(self, port: int):
        if os.name != "nt":
            raise RuntimeError("WINDOWS_SHUTDOWN_EVENT_REQUIRED")
        self.name = event_name(port)
        self.handle = None

    def open(self):
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateEventW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_bool,
                                        ctypes.c_wchar_p]
        kernel.CreateEventW.restype = ctypes.c_void_p
        self.handle = kernel.CreateEventW(None, False, False, self.name)
        if not self.handle:
            raise OSError(ctypes.get_last_error(), "CreateEventW failed")
        return kernel

    def watch(self, server: uvicorn.Server):
        kernel = self.open()
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        kernel.WaitForSingleObject.restype = ctypes.c_uint
        while True:
            result = kernel.WaitForSingleObject(self.handle, 250)
            if result == WAIT_OBJECT_0:
                server.should_exit = True
                return
            if result != WAIT_TIMEOUT:
                raise OSError(ctypes.get_last_error(), "WaitForSingleObject failed")

    def close(self):
        if self.handle:
            ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(self.handle)
            self.handle = None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("application")
    parser.add_argument("--app-dir", default=".")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--proxy-headers", action="store_true")
    parser.add_argument("--forwarded-allow-ips", default="127.0.0.1")
    parser.add_argument("--log-config")
    args = parser.parse_args()
    if args.host != "127.0.0.1":
        raise ValueError("LOCALHOST_BIND_REQUIRED")
    app_dir = Path(args.app_dir).resolve()
    sys.path.insert(0, str(app_dir))
    config = uvicorn.Config(
        args.application, host=args.host, port=args.port,
        proxy_headers=args.proxy_headers, forwarded_allow_ips=args.forwarded_allow_ips,
        log_config=args.log_config,
    )
    server = uvicorn.Server(config)
    shutdown = ShutdownEvent(args.port)
    watcher = threading.Thread(target=shutdown.watch, args=(server,), daemon=True,
                               name="income-analytics-shutdown-watch")
    watcher.start()
    try:
        server.run()
    finally:
        server.should_exit = True
        watcher.join(timeout=2)
        shutdown.close()
        try:
            from income_analytics.infrastructure.database import engine
            engine.dispose()
        except ImportError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
