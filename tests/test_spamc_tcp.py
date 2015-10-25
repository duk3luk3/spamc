import os
import unittest2
import threading

from mimetools import Message

from spamc import SpamC
from spamc.exceptions import SpamCError

from _s import return_tcp


class TestSpamCTCP(unittest2.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.using_sa = True
        if os.environ.get('SPAMD_HOST', None) is None:
            cls.tcp_server = return_tcp()
            t1 = threading.Thread(target=cls.tcp_server.serve_forever)
            t1.setDaemon(True)
            t1.start()
            cls.using_sa = False
        cls.spamc_tcp = SpamC(
            host=os.environ.get('SPAMD_HOST', '127.0.0.1'),
            port=int(os.environ.get('SPAMD_PORT', 10000)),
            gzip=os.environ.get('SPAMD_COMPRESS', None),
            compress_level=int(os.environ.get('SPAMD_COMPRESS_LEVEL', 6)))
        path = os.path.dirname(os.path.dirname(__file__))
        cls.filename = os.path.join(path, 'examples', 'sample-spam.txt')

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'tcp_server'):
            cls.tcp_server.shutdown()

    def test_spamc_tcp_no_conn(self):
        spamc_tcp = SpamC(host='127.0.0.1', port=10001)
        self.assertRaises(SpamCError, spamc_tcp.ping)

    def test_spamc_tcp_ping(self):
        result = self.spamc_tcp.ping()
        self.assertIn('message', result)
        self.assertEqual('PONG', result['message'])

    def test_spamc_tcp_check(self):
        with open(self.filename) as handle:
            result = self.spamc_tcp.check(handle)
        self.assertIn('message', result)
        self.assertEqual('EX_OK', result['message'])
        if not self.using_sa:
            self.assertEqual(15.0, result['score'])

    def test_spamc_tcp_symbols(self):
        with open(self.filename) as handle:
            result = self.spamc_tcp.symbols(handle)
        self.assertIn('message', result)
        self.assertEqual('EX_OK', result['message'])
        if not self.using_sa:
            self.assertIn('BAYES_00', result['symbols'])

    def test_spamc_tcp_report(self):
        with open(self.filename) as handle:
            result = self.spamc_tcp.report(handle)
        self.assertIn('message', result)
        self.assertEqual('EX_OK', result['message'])
        if not self.using_sa:
            self.assertIn('BAYES_00', result['report'][0]['name'])

    def test_spamc_tcp_report_ifspam(self):
        with open(self.filename) as handle:
            result = self.spamc_tcp.report_ifspam(handle)
        self.assertIn('message', result)
        self.assertEqual('EX_OK', result['message'])
        if not self.using_sa:
            self.assertIn('BAYES_00', result['report'][0]['name'])

    def test_spamc_tcp_process(self):
        with open(self.filename) as handle:
            result = self.spamc_tcp.process(handle)
        self.assertIn('message', result)
        # self.assertEqual(
        #     open(self.filename).read() + '\r\n',
        #     result['message'])

    def test_spamc_tcp_headers(self):
        with open(self.filename) as handle:
            result = self.spamc_tcp.headers(handle)
        self.assertIn('message', result)
        headers = Message(open(self.filename))
        org_subject = "Subject: %s" % headers.get('Subject')
        new_subject = "Subject: %s" % result['headers'].get('Subject')
        self.assertEqual(org_subject, new_subject)

    def test_spamc_tcp_learn(self):
        with open(self.filename) as handle:
            result = self.spamc_tcp.learn(handle, 'spam')
        self.assertIn('message', result)
        self.assertEqual('EX_OK', result['message'])
        if not self.using_sa:
            self.assertEqual(True, result['didset'])
            self.assertEqual(False, result['didremove'])

    def test_spamc_tcp_tell(self):
        with open(self.filename) as handle:
            result = self.spamc_tcp.tell(handle, 'forget')
        self.assertIn('message', result)
        self.assertEqual('EX_OK', result['message'])
        if not self.using_sa:
            self.assertEqual(False, result['didset'])
            self.assertEqual(True, result['didremove'])

    def test_spamc_tcp_revoke(self):
        with open(self.filename) as handle:
            result = self.spamc_tcp.revoke(handle)
        self.assertIn('message', result)
        self.assertEqual('EX_OK', result['message'])
        if not self.using_sa:
            self.assertEqual(True, result['didset'])
            self.assertEqual(True, result['didremove'])

if __name__ == '__main__':
    unittest2.main()
