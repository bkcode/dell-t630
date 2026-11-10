#!/usr/bin/env python3
"""Probe an MCP stdio command without recording credentials or design contents."""
import json
import queue
import subprocess
import threading
import time


class Probe:
    def __init__(self, command):
        self.child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True, bufsize=1)
        self.messages = queue.Queue()
        self.next_id = 0
        self.stdout_is_JSON_only = True
        self.stderr_bytes = 0
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    def _read_stdout(self):
        for line in self.child.stdout:
            try:
                self.messages.put(json.loads(line))
            except ValueError:
                self.stdout_is_JSON_only = False
        self.messages.put(None)

    def _read_stderr(self):
        for line in self.child.stderr:
            self.stderr_bytes += len(line.encode())

    def request(self, method, params=None, timeout=40):
        self.next_id += 1
        identity = self.next_id
        self.child.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': identity, 'method': method,
                                          **({'params': params} if params is not None else {})}) + '\n')
        self.child.stdin.flush()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = self.messages.get(timeout=max(0.01, deadline - time.monotonic()))
            if value is None:
                raise RuntimeError('MCP-process-closed')
            if value.get('id') == identity:
                if 'error' in value:
                    raise RuntimeError('MCP-request-rejected')
                return value.get('result')
        raise RuntimeError('MCP-response-timeout')

    def initialize(self):
        result = self.request('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {},
                              'clientInfo': {'name': 'dell-MCP-client-readonly-check', 'version': '1'}})
        self.child.stdin.write(json.dumps({'jsonrpc': '2.0', 'method': 'notifications/initialized'}) + '\n')
        self.child.stdin.flush()
        return result

    def close(self):
        if self.child.stdin and not self.child.stdin.closed:
            self.child.stdin.close()
        try:
            return self.child.wait(timeout=12)
        except subprocess.TimeoutExpired:
            self.child.terminate()
            return self.child.wait(timeout=8)
