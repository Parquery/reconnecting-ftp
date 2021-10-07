#!/usr/bin/env python3
"""
Classes helping inputries to download from FTP servers.
"""

import ftplib
import socket
from typing import Optional, Callable, TypeVar, Union, List, Iterable, Tuple, Dict, Any  # pylint: disable=unused-import


class Access:
    """
    Represents access information to the FTP server.
    """

    def __init__(self):
        self.hostname = ''
        self.port = 0
        self.user = ''
        self.password = ''


T = TypeVar('T')


def mlst(connection: ftplib.FTP, filename: str, facts: Optional[List[str]] = None):
    """
    Executes mlst command on the server.

    :param connection: to the server
    :param filename: filename
    :param facts: see ftplib.mlsd doc
    :return:
    """
    # pylint: disable=too-many-locals
    fact_lst = [] if facts is None else facts

    if fact_lst:
        connection.sendcmd("OPTS MLST " + ";".join(fact_lst) + ";")

    resp = connection.sendcmd("MLST {}".format(filename))
    lines = resp.split('\n')

    if len(lines) <= 1:
        raise ftplib.Error("Unexpected number of lines in an MLST response: {!r}".format(resp))

    line = lines[1].lstrip(' ')

    line_parts = line.split(' ')
    if len(line_parts) != 2:
        raise ftplib.Error("Unexpected partition of MLST fact line by space: {!r}".format(resp))

    facts_found, pth = line_parts
    facts_found = facts_found.rstrip(';')

    parts = facts_found.split(';')
    entry = {}
    for part in parts:
        fact_parts = part.split('=')
        if len(fact_parts) != 2:
            raise ftplib.Error("Unexpected partition of MLST fact line by equal sign: {!r}".format(resp))

        key, value = fact_parts
        entry[key.lower()] = value

    return pth, entry


class Client:
    """
    Reconnects to the FTP server if the connection has been closed. The current working directory is cached
    in between the sessions. When you re-connect, it changes first to the last available CWD.
    """

    # pylint: disable=too-many-public-methods
    def __init__(self,
                 hostname: str,
                 port: int,
                 user: str,
                 password: str,
                 max_reconnects: int = 10,
                 timeout: int = 10,
                 FTP=ftplib.FTP,
                 encoding: str = 'utf-8') -> None:
        # pylint: disable=too-many-arguments
        self.access = Access()
        self.access.hostname = hostname
        self.access.port = port
        self.access.user = user
        self.access.password = password

        self.connection = None  # type: Optional[ftplib.FTP]
        self.last_pwd = None  # type: Optional[str]
        self.encoding = encoding
        self.max_reconnects = max_reconnects
        self.timeout = timeout

        self.FTP = FTP  # pylint: disable=invalid-name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self) -> None:
        """ Connects to the server if not already connected. """
        if self.connection is not None and self.connection.file is None:
            self.connection.close()
            self.connection = None

        if self.connection is None:
            conn_refused = None  # type: Optional[ConnectionRefusedError]
            try:
                self.connection = self.FTP(timeout=self.timeout, encoding=self.encoding)
                self.connection.connect(host=self.access.hostname, port=self.access.port)
                self.connection.login(user=self.access.user, passwd=self.access.password)
            except ConnectionRefusedError as err:
                conn_refused = err

            if conn_refused:
                raise ConnectionRefusedError("Failed to connect to {}:{}: {}".format(
                    self.access.hostname, self.access.port, conn_refused))

            if self.last_pwd is not None:
                self.connection.cwd(self.last_pwd)

    def close(self) -> None:
        """ Closes the connection. """
        if self.connection is not None:
            self.connection.close()

    def __wrap_reconnect(self, method: Callable[[ftplib.FTP], T]) -> T:
        """
        Dispatches the method to the connection and reconnects if needed.

        :param method: to be dispatched
        :return: response from the method
        """
        last_err = None  # type: Optional[Exception]

        for _ in range(0, self.max_reconnects):
            try:
                if self.connection is None:
                    self.connect()

                assert self.connection is not None, "Expected connect() to either raise or create a connection"
                return method(self.connection)

            except (ConnectionRefusedError, socket.timeout, socket.gaierror, socket.herror, ftplib.error_temp,
                    EOFError) as err:
                self.connection.close()
                self.connection = None
                last_err = err

        assert last_err is not None, 'Expected either an error or a previous return'
        raise ftplib.error_temp(
            "Failed to execute a command on {}:{} after {} reconnect(s), the last error was: {}".format(
                self.access.hostname, self.access.port, self.max_reconnects, last_err))

    def reconnecting(self, method: Callable[[ftplib.FTP], T]) -> T:
        """
        Dispatches the method to the connection, reconnects if needed and observes the last working directory.

        :param method: to be dispatched
        :return: response from the method
        """
        resp = self.__wrap_reconnect(method=method)
        self.last_pwd = self.pwd()
        return resp

    def abort(self):
        """ See ftplib documentation """
        return self.reconnecting(method=lambda conn: conn.abort())

    def sendcmd(self, cmd):
        """ See ftplib documentation """
        return self.reconnecting(method=lambda conn: conn.sendcmd(cmd))

    def voidcmd(self, cmd):
        """ See ftplib documentation """
        return self.reconnecting(method=lambda conn: conn.voidcmd(cmd))

    def sendport(self, host, port):
        """ See ftplib documentation """
        return self.reconnecting(method=lambda conn: conn.sendport(host, port))

    def sendeprt(self, host, port):
        """ See ftplib documentation """
        return self.reconnecting(method=lambda conn: conn.sendeprt(host, port))

    def makeport(self):
        """ See ftplib documentation """
        return self.reconnecting(method=lambda conn: conn.makeport())

    def makepasv(self):
        """ See ftplib documentation """
        return self.reconnecting(method=lambda conn: conn.makepasv())

    def ntransfercmd(self, cmd, rest=None):
        """ See ftplib documentation """
        return self.reconnecting(method=lambda conn: conn.ntransfercmd(cmd, rest))

    def transfercmd(self, cmd, rest=None):
        """ See ftplib documentation """
        return self.reconnecting(method=lambda conn: conn.transfercmd(cmd, rest))

    def retrbinary(self, cmd, callback, blocksize=8192, rest=None):
        """ See ftplib documentation """
        return self.reconnecting(method=lambda conn: conn.retrbinary(cmd, callback, blocksize, rest))

    def retrlines(self, cmd, callback=None):
        """ See ftplib documentation """
        return self.reconnecting(method=lambda conn: conn.retrlines(cmd, callback))

    def storbinary(self, cmd, fp, blocksize=8192, callback=None, rest=None):
        """ See ftplib documentation """
        # pylint: disable=invalid-name, too-many-arguments
        return self.reconnecting(method=lambda conn: conn.storbinary(cmd, fp, blocksize, callback, rest))

    def storlines(self, cmd, fp, callback=None):
        """ See ftplib documentation """
        # pylint: disable=invalid-name
        return self.reconnecting(method=lambda conn: conn.storlines(cmd, fp, callback))

    def acct(self, password):
        """ See ftplib documentation """
        return self.reconnecting(method=lambda conn: conn.acct(password))

    def nlst(self, *args):
        """ See ftplib documentation """
        return self.reconnecting(method=lambda conn: conn.nlst(*args))

    def dir(self, *args):
        """ See ftplib documentation """
        return self.reconnecting(method=lambda conn: conn.dir(*args))

    def mlsd(self, path="", facts=None) -> List[Tuple[str, Dict[str, Any]]]:
        """
        See ftplib documentation.

        Unlike ftplib.FTP.mlsd, converts the generator to a list.
        This is necessary in order to give you atomicity (the connection succeeded and you can iterate over the list
        or the connection failed).

        Mind that you need to have enough memory to hold all the directory entries.
        """
        facts_lst = [] if facts is None else facts
        return self.reconnecting(method=lambda conn: list(conn.mlsd(path, facts_lst)))

    def rename(self, fromname, toname):
        """ See ftplib documentation """
        return self.reconnecting(method=lambda conn: conn.rename(fromname, toname))

    def delete(self, filename):
        """ See ftplib documentation """
        return self.reconnecting(method=lambda conn: conn.delete(filename))

    def cwd(self, dirname):
        """ See ftplib documentation """
        return self.reconnecting(method=lambda conn: conn.cwd(dirname))

    def size(self, filename):
        """ See ftplib documentation """
        return self.reconnecting(method=lambda conn: conn.size(filename))

    def mkd(self, dirname):
        """ See ftplib documentation """
        return self.reconnecting(method=lambda conn: conn.mkd(dirname))

    def rmd(self, dirname):
        """ See ftplib documentation """
        return self.reconnecting(method=lambda conn: conn.rmd(dirname))

    def pwd(self):
        """ See ftplib documentation """
        self.last_pwd = self.__wrap_reconnect(method=lambda conn: conn.pwd())
        return self.last_pwd

    def quit(self):
        """ See ftplib documentation """
        resp = self.reconnecting(method=lambda conn: conn.quit())
        self.connection = None
        return resp

    def mlst(self, filename: str, facts: Optional[List[str]] = None):
        """ Executes the mlst command """
        return self.reconnecting(method=lambda conn: mlst(connection=conn, filename=filename, facts=facts))
