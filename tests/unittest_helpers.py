'''
    unittest helper functions, base TestCase class, mocks that are
    used everywhere, etc.

'''

import sys
import os
import unittest
import html5lib
from peewee import SqliteDatabase, Model
from flask import json

sys.path.append(os.path.dirname(__file__) + '/..')

import streetsign_server
import streetsign_server.models as models

# pylint: disable=too-many-public-methods, too-many-arguments

class WrongHTTPCode(AssertionError):
    ''' validate() got the wrong HTTP status code! '''
    def __init__(self, url, should_be, actually_was):
        super(WrongHTTPCode, self).__init__(
            'For Url {0}: Expected HTTP Code: {1}, actually got: {2}'
            .format(url, should_be, actually_was))

class MockBcrypt(object):
    ''' Mock BCrypt out.  It's very slow.  Which is actually good... '''

    @staticmethod
    def hashpw(password, salt):
        return password

    @staticmethod
    def checkpw(password, hashed):
        return password == hashed

    @staticmethod
    def gensalt():
        return b''

class StreetSignTestCase(unittest.TestCase):
    ''' Base Class, initialises and tears down a streetsign_server context. '''

    def setUp(self):
        ''' initialise temporary new database. '''

        self.ctx = streetsign_server.app.test_request_context

       # streetsign_server.app.config['MODE'] = 'testing'
        models.bcrypt = MockBcrypt()
        streetsign_server.app.config['DATABASE_FILE'] = ':memory:'

        streetsign_server.app.config['TESTING'] = True

        models.DB = SqliteDatabase(None)
        models.DB.init(streetsign_server.app.config['DATABASE_FILE'])

        model_list = []

        for modelname in models.__all__:
            model = getattr(models, modelname)
            try:
                if issubclass(model, Model):
                    model.bind(models.DB)
                    model_list.append(model)
            except TypeError:
                pass

        models.DB.create_tables(model_list)

        self.client = streetsign_server.app.test_client()

    def tearDown(self):
        ''' delete temporary database '''

        models.DB.close()

    def validate(self, url, lang='html', code=200, req='GET', data=None, **kwargs):
        ''' test that a URL is actually HTML5 compliant '''

        if not data:
            data = {}

        if req == 'GET':
            request = self.client.get(url, **kwargs)
        elif req == 'POST':
            request = self.client.post(url, data=data, **kwargs)

        if lang == 'html':
            parser = html5lib.HTMLParser(strict=False)
            parser.parse(request.data)

            real_errors = []
            for err in parser.errors:
                errcode = err[1] if len(err) > 1 else None
                errdata = err[2] if len(err) > 2 else None
                if (isinstance(errdata, dict)
                        and errdata.get('name') == 'template'):
                    continue
                real_errors.append(err)

            if real_errors:
                err = real_errors[0]
                body = request.data.decode('utf-8', errors='replace')
                lineno = err[0][0] - 1

                print('HTML Parse Error, %s, %s:' % err[0])
                print('----------------:', err[1] if len(err) > 1 else None)
                print('----------------:', err[2] if len(err) > 2 else None)

                print('\n    '.join(body.split('\n')[lineno-3: lineno]))
                print('-->', body.split('\n')[lineno])
                print('\n    ' + ('\n    '.join(
                    body.split('\n')[lineno+1: lineno+3])))

                raise AssertionError(
                    'HTML parse error at line %s: %s' % (err[0], err[1]))

        elif lang == 'json':
            json.loads(request.data)


        if code != request.status_code:
            print(request.data)
            raise WrongHTTPCode(url, code, request.status_code)

    def login(self, username, password):
        return self.client.post('/login',
                                data=dict(username=username,
                                          password=password),
                                follow_redirects=True)

    def logout(self):
        return self.client.post('/logout', follow_redirects=True)
