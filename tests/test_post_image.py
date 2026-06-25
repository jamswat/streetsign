'''
    Testing posting a new image.
'''

# pylint: disable=too-many-public-methods, missing-docstring, invalid-name

import sys
import os
import io
import shutil
import struct
import zlib
import json
from os.path import join as pathjoin, isfile

sys.path.append(os.path.dirname(__file__) + '/..')

from uuid import uuid4
from flask import url_for

import streetsign_server
from streetsign_server.models import Feed, Post

from test_views_users_and_auth import BasicUsersTestCase

USERNAME = 'test'
USERPASS = '123'

ADMINNAME = 'admin'
ADMINPASS = '42'

USER_DIR = streetsign_server.config.SITE_VARS['user_dir']

def make_minimal_png():
    def chunk(chunk_type, data):
        c = chunk_type + data
        return struct.pack('>I', len(data)) + c + \
               struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    header = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
    raw = b'\x00\xff\x00\x00'
    idat = chunk(b'IDAT', zlib.compress(raw))
    iend = chunk(b'IEND', b'')
    return io.BytesIO(header + ihdr + idat + iend)

class ImageUploadTestCase(BasicUsersTestCase):
    def setUp(self):
        super().setUp()

        self.uuid = str(uuid4())
        self.tmp_path = pathjoin('/tmp', self.uuid)
        self._old_path = streetsign_server.config.SITE_VARS['user_dir']
        streetsign_server.config.SITE_VARS['user_dir'] = self.tmp_path

        os.makedirs(self.tmp_path, exist_ok=True)

    def tearDown(self):
        streetsign_server.config.SITE_VARS['user_dir'] = self._old_path
        shutil.rmtree(self.tmp_path, ignore_errors=True)
        super().tearDown()

    def create_writable_feed(self, user, post_types='image'):
        f = Feed(name='test_feed', post_types=post_types)
        f.save()
        f.grant('Write', user=user)
        return f

class ImageUrlUpload(ImageUploadTestCase):
    ''' Uploading images '''

    def test_non_existant_feed_not_logged_in(self):
        with self.ctx():
            c = self.client.post(url_for('post_new', feed_id=0))
            self.assertEqual(c.status_code, 403)

            c = self.client.post(url_for('post_new', feed_id=0),
                                 follow_redirects=True)
            self.assertEqual(c.status_code, 403)

    def test_logged_in_without_write_permission_gets_flashed(self):
        f = Feed(name='restricted_feed')
        f.save()

        self.login(USERNAME, USERPASS)
        with self.ctx():
            c = self.client.post(url_for('post_new', feed_id=f.id),
                                 follow_redirects=True)
        self.assertIn(b"don&#39;t have permission to write", c.data)

    def test_upload_with_invalid_file_type(self):
        f = self.create_writable_feed(self.user)
        self.login(USERNAME, USERPASS)

        test_data = io.BytesIO(b'this is not an image')

        with self.ctx(), self.assertRaises(OSError):
            self.client.post(
                url_for('post_new', feed_id=f.id),
                data={
                    'post_title': 'test image post',
                    'post_type': 'image',
                    'upload': 'on',
                    'image_file': (test_data, 'test.txt'),
                },
                content_type='multipart/form-data'
            )
        self.assertEqual(Post.select().count(), 0)

    def test_upload_image_success(self):
        f = self.create_writable_feed(self.user)
        self.login(USERNAME, USERPASS)

        png_data = make_minimal_png()

        with self.ctx():
            self.client.post(
                url_for('post_new', feed_id=f.id),
                data={
                    'post_title': 'test image post',
                    'post_type': 'image',
                    'upload': 'on',
                    'image_file': (png_data, 'test.png'),
                },
                content_type='multipart/form-data',
                follow_redirects=True
            )

        self.assertEqual(Post.select().count(), 1)
        post = Post.select().first()
        self.assertEqual(post.type, 'image')
        self.assertEqual(post.title, 'test image post')

        content = json.loads(post.content)
        self.assertIn('content', content)
        self.assertIn('.png', content['content'])

    def test_create_post_with_image_type_get(self):
        f = self.create_writable_feed(self.user)
        self.login(USERNAME, USERPASS)

        with self.ctx():
            c = self.client.get(url_for('post_new', feed_id=f.id))
        self.assertEqual(c.status_code, 200)
        self.assertIn(b'Image', c.data)

    def test_post_to_feed_that_does_not_allow_images(self):
        f = self.create_writable_feed(self.user, post_types='text')
        self.login(USERNAME, USERPASS)

        with self.ctx():
            c = self.client.post(
                url_for('post_new', feed_id=f.id),
                data={
                    'post_title': 'test image post',
                    'post_type': 'image',
                    'upload': 'on',
                },
                follow_redirects=True
            )
        self.assertIn(b'post type is not allowed', c.data)

    def test_upload_corrupt_image_saved_to_disk(self):
        f = self.create_writable_feed(self.user)
        self.login(USERNAME, USERPASS)

        png_data = make_minimal_png()

        with self.ctx():
            self.client.post(
                url_for('post_new', feed_id=f.id),
                data={
                    'post_title': 'corrupt test',
                    'post_type': 'image',
                    'upload': 'on',
                    'image_file': (png_data, 'corrupt.png'),
                },
                content_type='multipart/form-data',
                follow_redirects=True
            )

        self.assertEqual(Post.select().count(), 1)
        content = json.loads(Post.select().first().content)
        full_path = pathjoin(streetsign_server.config.SITE_VARS['user_dir'],
                             'post_images', content['content'])
        self.assertTrue(isfile(full_path),
                        f'Expected file at {full_path}')

    def test_upload_no_file_creates_no_post(self):
        f = self.create_writable_feed(self.user)
        self.login(USERNAME, USERPASS)

        with self.ctx():
            self.client.post(
                url_for('post_new', feed_id=f.id),
                data={
                    'post_title': 'no file test',
                    'post_type': 'image',
                    'upload': 'on',
                },
                content_type='multipart/form-data'
            )

        self.assertEqual(Post.select().count(), 0)

    def test_upload_fake_png_succeeds_but_resize_fails(self):
        f = self.create_writable_feed(self.user)
        self.login(USERNAME, USERPASS)

        fake_png = io.BytesIO(b'\x89PNG\r\n\x1a\n' + b'garbage data')

        with self.ctx():
            self.client.post(
                url_for('post_new', feed_id=f.id),
                data={
                    'post_title': 'bad png',
                    'post_type': 'image',
                    'upload': 'on',
                    'image_file': (fake_png, 'bad.png'),
                },
                content_type='multipart/form-data',
                follow_redirects=True
            )

        self.assertEqual(Post.select().count(), 1)
        post = Post.select().first()
        content = json.loads(post.content)
        self.assertIn('.png', content['content'])
