# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4
# spamc - Python spamassassin spamc client library
# Copyright (C) 2015  Andrew Colin Kissa <andrew@topdog.za.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
spamc: Python spamassassin spamc client library

Copyright 2015, Andrew Colin Kissa
Licensed under AGPLv3+
"""
from __future__ import print_function

import os
import socket
import sys

if sys.version_info < (3, 0):
    from email.parser import FeedParser
    from SocketServer import StreamRequestHandler, ThreadingTCPServer, \
        ThreadingUnixStreamServer
    from cStringIO import StringIO
else:
    from email.parser import BytesFeedParser as FeedParser
    from socketserver import StreamRequestHandler, ThreadingTCPServer, \
        ThreadingUnixStreamServer
    from io import BytesIO as StringIO

from email.message import Message

ThreadingTCPServer.allow_reuse_address = True

REPORT_TMPL = b"""Spam detection software, running on the system "localhost",
has identified this incoming email as possible spam.  The original
message has been attached to this so you can view it or label
similar future email.  If you have any questions, see
the administrator of that system for details.

Content preview:  This is the GTUBE, the Generic Test for Unsolicited Bulk
Email
   If your spam filter supports it, the GTUBE provides a test by which you can
   verify that the filter is installed correctly and is detecting incoming
   spam.
   You can send yourself a test mail containing the following string of
   characters (in upper case and with no white spaces and line breaks): [...]

Content analysis details:   (15.0 points, 5.0 required)

 pts rule name              description
---- ---------------------- --------------------------------------------------
-2.00 BAYES_00                  Bayes spam probability is 0 to 1%
 0.79 RDNS_NONE                  Delivered by a host with no rDNS
 0.50 KAM_LAZY_DOMAIN_SECURITY   Sender doesn't have anti-forgery methods
"""

def parse_headers(fp, MessageClass):
    parser = FeedParser(_factory=MessageClass)
    while True:
        line = fp.readline()
        if line == b'\r\n' or line == b'\n' or line == b'':
            headers = parser.close()
            return headers
        else:
            parser.feed(line)

class TestSpamdHandler(StreamRequestHandler):
    """
    A spamd mockup

    Implements the spamd protocol: http://svn.apache.org/repos/asf/spamassassin/trunk/spamd/PROTOCOL
    and returns valid dummy responses
    """

    MessageClass = Message
    default_request_version = "SPAMD/1.0"
    allow_tell = True

    def do_PING(self):
        """Emulate PING"""
        self.wfile.write(b"SPAMD/1.5 0 PONG\r\n")

    def do_TELL(self):
        """Emulate TELL"""
        if self.allow_tell:
            self.wfile.write(b"SPAMD/1.5 0 EX_OK\r\n")
            didset = self.headers.get('Set')
            if didset:
                self.wfile.write(b"DidSet: True\r\n")
            didremove = self.headers.get('Remove')
            if didremove:
                self.wfile.write(b"DidRemove: True\r\n")
        else:
            self.wfile.write(b"SPAMD/1.0 69 Service Unavailable: TELL commands are not enabled, set the --allow-tell switch.\r\n")
        self.wfile.write(b"\r\n\r\n")
        self.close_connection = 1

    def do_HEADERS(self):
        """Emulate HEADERS"""
        content_length = int(self.headers.get('Content-length', 0))
        body = self.rfile.read(content_length)
        # Remove trailing \r\n\r\n
        parts, = body.rsplit(b'\r\n\r\n', 1)
        _headers = parse_headers(StringIO(parts), self.MessageClass)
        if hasattr(_headers, 'as_bytes'):
            response = _headers.as_bytes()
        else:
            response = _headers.as_string()
        print('response', repr(response))

        self.wfile.write(b"SPAMD/1.5 0 EX_OK\r\n")
        self.wfile.write(b"Spam: True ; 15 / 5\r\n")
        if self.request_version >= (1, 3):
            self.wfile.write(b"Content-length: %d\r\n" % len(response))
        self.wfile.write(b"\r\n")
        self.wfile.write(response)
        self.close_connection = 1

    def do_PROCESS(self):
        """Emulate PROCESS"""
        content_length = int(self.headers.get('Content-length', 0))
        body = self.rfile.read(content_length)
        self.wfile.write(b"SPAMD/1.5 0 EX_OK\r\n")
        self.wfile.write(b"Spam: True ; 15 / 5\r\n")
        if self.request_version >= (1, 3):
            self.wfile.write(
                b"Content-length: %d\r\n" % content_length)
        self.wfile.write(b"\r\n\r\n")
        self.wfile.write(body)
        self.close_connection = 1

    def do_REPORT_IFSPAM(self):
        """Emulate REPORT_IFSPAM"""
        self.do_REPORT()

    def do_REPORT(self):
        """Emulate REPORT"""
        self.wfile.write(b"SPAMD/1.5 0 EX_OK\r\n")
        self.wfile.write(b"Spam: True ; 15 / 5\r\n")
        if self.request_version >= (1, 3):
            self.wfile.write(
                b"Content-length: %d\r\n" % len(REPORT_TMPL))
        self.wfile.write(b"\r\n\r\n")
        self.wfile.write(REPORT_TMPL)
        self.close_connection = 1

    def do_SYMBOLS(self):
        """Emulate SYMBOLS"""
        rules = b"BAYES_00,RDNS_NONE,KAM_LAZY_DOMAIN_SECURITY"
        self.wfile.write(b"SPAMD/1.5 0 EX_OK\r\n")
        self.wfile.write(b"Spam: True ; 15 / 5\r\n")
        if self.request_version >= (1, 3):
            self.wfile.write(b"Content-length: %d\r\n" % len(rules))
        self.wfile.write(b"\r\n\r\n")
        self.wfile.write(rules)
        if self.request_version < (1, 3):
            self.wfile.write(b"\r\n")
        self.close_connection = 1

    def do_CHECK(self):
        """Emulate CHECK"""
        self.wfile.write(b"SPAMD/1.5 0 EX_OK\r\n")
        self.wfile.write(b"Spam: True ; 15 / 5\r\n")
        self.wfile.write(b"\r\n\r\n")
        self.close_connection = 1

    def send_error(self, msg):
        """Send Error response"""
        self.wfile.write(b"SPAMD/1.0 EX_PROTOCOL Bad header line: %s\r\n" % msg)

    def parse_request(self):
        """Parse the request"""
        self.command = None
        self.request_version = version = self.default_request_version
        self.close_connection = 1
        requestline = self.raw_requestline
        requestline = requestline.rstrip(b'\r\n')
        self.requestline = requestline
        words = requestline.split()

        if len(words) == 2:
            command, version = words
            if version[:6] != b'SPAMC/':
                self.send_error(b"Bad request version (%r)" % version)
                return False
            try:
                base_version_number = version.split(b'/', 1)[1]
                version_number = base_version_number.split(b".")
                if len(version_number) != 2:
                    raise ValueError

                version_number = int(version_number[0]), int(version_number[1])
            except (ValueError, IndexError):
                self.send_error(b"Bad request version (%r)" % version)
                return False
            if version_number >= (1, 6):
                self.send_error(
                    b"Invalid HTTP Version (%s)" % base_version_number)
                return False
        elif not words:
            return False
        else:
            self.send_error(b"Bad request syntax (%r)" % requestline)
            return False
        self.command, self.request_version = command, version_number
        # Read headers
        self.headers = parse_headers(self.rfile, self.MessageClass)
        return True

    def handle_one_request(self):
        """Handle a request"""
        try:
            self.raw_requestline = self.rfile.readline(65537)
            print('requestline', repr(self.raw_requestline))
            if len(self.raw_requestline) > 65536:
                self.requestline = ''
                self.request_version = ''
                self.command = ''
                self.send_error(b"Invalid request")
                return

            if not self.raw_requestline:
                self.close_connection = 1
                return

            if not self.parse_request():
                return

            mname = 'do_' + self.command.decode()
            if not hasattr(self, mname):
                self.send_error(b"Unsupported method (%r)" % self.command)
                return

            method = getattr(self, mname)
            method()
            self.wfile.flush()
        except socket.timeout:
            self.close_connection = 1
            return

    def handle(self):
        """Main handler"""
        self.close_connection = 1

        self.handle_one_request()
        while not self.close_connection:
            self.handle_one_request()

class TestNoLearningSpamdHandler(TestSpamdHandler):
    allow_tell = False

def return_tcp(port=10000, allow_tell=True):
    """Return a tcp SPAMD server"""
    address = ('127.0.0.1', port)
    if allow_tell:
        server = ThreadingTCPServer(address, TestSpamdHandler)
    else:
        server = ThreadingTCPServer(address, TestNoLearningSpamdHandler)

    return server


def return_unix(sock='spamd.sock'):
    """Return a unix SPAMD server"""
    if os.path.exists(sock):
        os.remove(sock)
    server = ThreadingUnixStreamServer(sock, TestSpamdHandler)
    return server


def start_tcp():
    """Start a tcp SPAMD server"""
    server = return_tcp()
    server.serve_forever()


def start_unix():
    """Start a unix SPAMD server"""
    server = return_unix()
    server.serve_forever()


if __name__ == '__main__':
    start_unix()
