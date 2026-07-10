''' Tests for post playlist ordering (sort_order field). '''

#pylint: disable=import-error,too-many-public-methods,too-few-public-methods,missing-docstring

import sys
import os
from datetime import timedelta
from flask import json

sys.path.append(os.path.dirname(__file__) + '/..')

import streetsign_server.models as models
from streetsign_server.models import Post

from unittest_helpers import StreetSignTestCase

USERNAME = 'testuser'
USERPASS = '12345'


class TestPlaylistOrdering(StreetSignTestCase):
    ''' Posts should be returned in sort_order by the screens_posts_from_feeds
        endpoint, not in insertion order. '''

    def setUp(self):
        super().setUp()
        self.feed = models.Feed.create(name='ordering feed')
        self.user = models.User.create(name='test user', loginname=USERNAME,
                                       emailaddress='test@example.com',
                                       passwordhash='', is_admin=True)
        self.user.set_password(USERPASS)
        self.user.save()
        self.feed.grant('Write', user=self.user)
        self.feed.grant('Publish', user=self.user)
        self.feed.save()

    def create_post(self, sort_order=0, **kwargs):
        kwargs.setdefault('title', 'test')
        kwargs.setdefault('type', 'html')
        kwargs.setdefault('content', '{"content":"text"}')
        kwargs.setdefault('author', self.user)
        kwargs.setdefault('published', True)
        p = models.Post.create(feed=self.feed, sort_order=sort_order, **kwargs)
        p.save()
        return p

    def get_posts_ids(self, feeds):
        feeds_str = ','.join([str(i) for i in feeds])
        url = '/screens/posts_from_feeds/%5B' + feeds_str + '%5D'
        return [x['id'] for x in json.loads(self.client.get(url).data)['posts']]

    def test_default_order_by_sort_order(self):
        ''' Posts returned in sort_order then id. '''
        p1 = self.create_post(sort_order=5)
        p2 = self.create_post(sort_order=1)
        p3 = self.create_post(sort_order=3)

        ids = self.get_posts_ids([self.feed.id])
        self.assertEqual(ids, [p2.id, p3.id, p1.id])

    def test_same_sort_order_falls_back_to_id(self):
        p1 = self.create_post(sort_order=0)
        p2 = self.create_post(sort_order=0)
        p3 = self.create_post(sort_order=0)

        ids = self.get_posts_ids([self.feed.id])
        self.assertEqual(ids, [p1.id, p2.id, p3.id])

    def test_reorder_endpoint(self):
        ''' POSTing a new order to /feeds/<id>/reorder updates sort_order. '''
        p1 = self.create_post(sort_order=0)
        p2 = self.create_post(sort_order=1)
        p3 = self.create_post(sort_order=2)

        self.login(USERNAME, USERPASS)

        resp = self.client.post(f'/feeds/{self.feed.id}/reorder',
                                data=json.dumps({'post_ids': [p3.id, p1.id, p2.id]}),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        ids = self.get_posts_ids([self.feed.id])
        self.assertEqual(ids, [p3.id, p1.id, p2.id])

    def test_reorder_requires_admin(self):
        ''' Non-admin users cannot reorder. '''
        p1 = self.create_post(sort_order=0)

        # Create a non-admin user with write access.
        non_admin = models.User.create(name='editor', loginname='editor',
                                       emailaddress='e@x', passwordhash='')
        non_admin.set_password('pass')
        non_admin.save()
        self.feed.grant('Write', user=non_admin)

        self.login('editor', 'pass')

        resp = self.client.post(f'/feeds/{self.feed.id}/reorder',
                                data=json.dumps({'post_ids': [p1.id]}),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 403)


if __name__ == '__main__':
    import unittest
    unittest.main()
