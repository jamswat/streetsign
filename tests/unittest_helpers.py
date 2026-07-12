'''
    unittest helper functions, base TestCase class, mocks that are
    used everywhere, etc.

'''

import sys
import os
import unittest
import warnings
import html5lib
from peewee import SqliteDatabase, Model
from flask import json

# Peewee's _ConnectionLocal finalizer may emit a ResourceWarning during
# interpreter shutdown even though every connection was explicitly closed.
# Suppress it so the test suite runs clean under -W error.
warnings.filterwarnings('ignore',
                        message=r'.*unclosed database.*',
                        category=ResourceWarning)

sys.path.append(os.path.dirname(__file__) + '/..')

import streetsign_server
import streetsign_server.models as models

# pylint: disable=too-many-public-methods, too-many-arguments

class WrongHTTPCode(AssertionError):
    ''' validate() got the wrong HTTP status code! '''
    def __init__(self, url, should_be, actually_was):
        super().__init__(
            f'For Url {url}: Expected HTTP Code: {should_be}, actually got: {actually_was}'
        )

class MockBcrypt:
    ''' Mock BCrypt out.  It's very slow.  Which is actually good... '''

    @staticmethod
    def hashpw(password, _salt):
        """Mock bcrypt.hashpw."""
        return password

    @staticmethod
    def checkpw(password, hashed):
        """Mock bcrypt.checkpw."""
        return password == hashed

    @staticmethod
    def gensalt():
        """Mock bcrypt.gensalt."""
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

        # Close the database connection set up by models.init() at import
        # time before replacing the global DB handle with an in-memory one.
        if not models.DB.is_closed():
            models.DB.close()

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
                errdata = err[2] if len(err) > 2 else None
                if (isinstance(errdata, dict)
                        and errdata.get('name') == 'template'):
                    continue
                real_errors.append(err)

            if real_errors:
                err = real_errors[0]
                body = request.data.decode('utf-8', errors='replace')
                lineno = err[0][0] - 1

                print(f'HTML Parse Error, {err[0][0]}, {err[0][1]}:')
                print('----------------:', err[1] if len(err) > 1 else None)
                print('----------------:', err[2] if len(err) > 2 else None)

                print('\n    '.join(body.split('\n')[lineno-3: lineno]))
                print('-->', body.split('\n')[lineno])
                print('\n    ' + ('\n    '.join(
                    body.split('\n')[lineno+1: lineno+3])))

                raise AssertionError(
                    f'HTML parse error at line {err[0]}: {err[1]}')

        elif lang == 'json':
            json.loads(request.data)


        if code != request.status_code:
            print(request.data)
            raise WrongHTTPCode(url, code, request.status_code)

    def login(self, username, password):
        """Log in as the given user."""
        return self.client.post('/login',
                                data={"username": username,
                                      "password": password},
                                follow_redirects=True)

    def logout(self):
        """Log out the current user."""
        return self.client.post('/logout', follow_redirects=True)
