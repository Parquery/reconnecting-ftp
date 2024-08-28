#!/usr/bin/env python3
"""
Tests the reconning FTP.
"""

import contextlib
import ftplib
import logging
import pathlib
import shutil
import socket
import tempfile
import threading
import time
import unittest
from typing import Optional, List, Dict, Any  # pylint: disable=unused-import

import datetime
import pyftpdlib.authorizers
import pyftpdlib.handlers
import pyftpdlib.servers

import reconnecting_ftp


def find_free_port() -> int:
    """
    :return: a free port; mind that this is not multi-process safe and can lead to race conditions.
    """
    skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with contextlib.closing(skt):
        skt.bind(('', 0))
        _, port = skt.getsockname()
        return int(port)


class ThreadedFTPServer:
    """
    Creates a dummy FTP server which serves in a loop running in a separate thread.
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self, hostname: str, port: int, timeout: int, homedir: pathlib.Path, user: str, password: str) -> None:
        # pylint: disable=too-many-arguments
        self.port = port
        self.hostname = hostname
        self.timeout = timeout
        self.user = user
        self.password = password

        self.thread = None  # type: Optional[threading.Thread]
        self.lock = threading.Lock()

        authorizer = pyftpdlib.authorizers.DummyAuthorizer()
        authorizer.add_user(self.user, self.password, homedir=homedir.as_posix(), perm='elradfmwMT')

        handler = pyftpdlib.handlers.FTPHandler
        handler.authorizer = authorizer
        handler.timeout = self.timeout

        self.ftpd = pyftpdlib.servers.FTPServer((self.hostname, self.port), handler)

    def __enter__(self) -> None:
        self.thread = threading.Thread(target=self.ftpd.serve_forever)
        self.thread.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        with self.lock:
            self.ftpd.close_all()

        self.thread.join()


class TestContext:
    """
    A standard context of a test case. Starts a FTP server in a parallel thread.
    """

    def __init__(self, port: int, timeout: int, hostname: str = '127.0.0.1') -> None:
        self.port = port
        self.hostname = hostname
        self.timeout = timeout  # in seconds; max time between two FTP commands

        self.homedir = pathlib.Path()
        self.exit_stack = contextlib.ExitStack()
        self.user = 'some-user'
        self.password = 'some-password'

    def __enter__(self):
        self.homedir = pathlib.Path(tempfile.mkdtemp())
        self.exit_stack.callback(lambda: shutil.rmtree(self.homedir.as_posix()))

        ftpd = ThreadedFTPServer(hostname=self.hostname,
                                 port=self.port,
                                 timeout=self.timeout,
                                 homedir=self.homedir,
                                 user=self.user,
                                 password=self.password)

        ftpd.__enter__()
        self.exit_stack.push(ftpd)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit_stack.close()


class TestReconnectingFTP(unittest.TestCase):
    # pylint: disable=missing-docstring
    def test_connect(self):
        with TestContext(port=find_free_port(), timeout=1) as ctx:
            ftp = reconnecting_ftp.Client(hostname=ctx.hostname, port=ctx.port, user=ctx.user, password=ctx.password)

            with ftp:
                ftp.connect()

    def test_timeout(self):
        with TestContext(port=find_free_port(), timeout=1) as ctx:
            ftp = reconnecting_ftp.Client(hostname=ctx.hostname, port=ctx.port, user=ctx.user, password=ctx.password)

            with ftp:
                ftp.connect()
                (ctx.homedir / 'some-dir/some-subdir').mkdir(parents=True)
                ftp.cwd(dirname='/some-dir/some-subdir')

                time.sleep(ctx.timeout + 1)  # ensure we timed out and we can still reconnect

                pth = ftp.pwd()
                self.assertEqual(pth, '/some-dir/some-subdir')

    def test_mlst(self):
        with TestContext(port=find_free_port(), timeout=1) as ctx:
            ftp = reconnecting_ftp.Client(hostname=ctx.hostname, port=ctx.port, user=ctx.user, password=ctx.password)

            with ftp:
                pth = ctx.homedir / 'some-dir/some-file.txt'
                pth.parent.mkdir(parents=True)
                pth.write_text('tested', encoding='utf-8')

                ftp.cwd(dirname='/some-dir')

                srv_pth, entry = ftp.mlst(filename='some-file.txt')
                self.assertEqual(srv_pth, '/some-dir/some-file.txt')

                modify = datetime.datetime.strptime(entry['modify'], '%Y%m%d%H%M%S')

                expected_modify = datetime.datetime.utcfromtimestamp(
                    pathlib.Path(pth).stat().st_mtime).replace(microsecond=0)

                self.assertEqual(modify, expected_modify)
                self.assertEqual(entry['type'], 'file')

                with self.assertRaises(ftplib.error_perm):
                    _, _ = ftp.mlst(filename='/non-existing/some-file.txt')

                ftp.cwd(dirname='/')
                srv_pth, entry = ftp.mlst(filename='some-dir')
                self.assertEqual(srv_pth, '/some-dir')

                modify = datetime.datetime.strptime(entry['modify'], '%Y%m%d%H%M%S')

                expected_modify = datetime.datetime.utcfromtimestamp(
                    pathlib.Path(pth).stat().st_mtime).replace(microsecond=0)

                self.assertEqual(modify, expected_modify)
                self.assertEqual(entry['type'], 'dir')

    def test_mlsd(self):
        with TestContext(port=find_free_port(), timeout=1) as ctx:
            ftp = reconnecting_ftp.Client(hostname=ctx.hostname, port=ctx.port, user=ctx.user, password=ctx.password)

            with ftp:
                pth = ctx.homedir / 'some-dir/some-file.txt'
                pth.parent.mkdir(parents=True)
                pth.write_text('tested', encoding='utf-8')

                ftp.cwd(dirname='/some-dir')

                names = []  # type: List[str]
                entry_dicts = []  # type: List[Dict[str, Any]]

                for name, entry_dict in ftp.mlsd(facts=['size']):
                    names.append(name)
                    entry_dicts.append(entry_dict)

                self.assertListEqual(names, ['some-file.txt'])

                self.assertEqual(len(entry_dicts), 1)
                self.assertDictEqual(entry_dicts[0], {'size': '6'})


if __name__ == '__main__':
    logger = logging.getLogger('pyftpdlib')  # pylint: disable=invalid-name
    logger.setLevel(logging.WARNING)
    unittest.main()
