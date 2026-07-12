''' Tests for post recurrence (day-of-week scheduling). '''

#pylint: disable=import-error,too-many-public-methods,too-few-public-methods,missing-docstring

import sys
import os
import json
from datetime import timedelta

sys.path.append(os.path.dirname(__file__) + '/..')

import streetsign_server.models as models
from streetsign_server.models import Post

from unittest_helpers import StreetSignTestCase

USERNAME = 'testuser'
USERPASS = '12345'

ALL_DAYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']


class TestRecurrence(StreetSignTestCase):
    ''' Posts with recurrence enabled should only show on the selected
        days of the week. '''

    def setUp(self):
        super().setUp()
        self.feed = models.Feed.create(name='recurrence feed')
        self.user = models.User.create(displayname='test user', loginname=USERNAME,
                                       emailaddress='test@example.com',
                                       passwordhash='', is_admin=True)
        self.user.set_password(USERPASS)
        self.user.save()
        self.feed.grant('Write', user=self.user)
        self.feed.grant('Publish', user=self.user)
        self.feed.save()

    def create_post(self, recurrence=None, **kwargs):
        kwargs.setdefault('title', 'recurrence test')
        kwargs.setdefault('type', 'html')
        kwargs.setdefault('content', '{"content":"text"}')
        kwargs.setdefault('author', self.user)
        kwargs.setdefault('published', True)
        if recurrence is not None:
            kwargs['recurrence'] = json.dumps(recurrence)
        p = models.Post.create(feed=self.feed, **kwargs)
        p.save()
        return p

    def get_posts_ids(self, feeds):
        feeds_str = ','.join([str(i) for i in feeds])
        url = '/screens/posts_from_feeds/%5B' + feeds_str + '%5D'
        return [x['id'] for x in json.loads(self.client.get(url).data)['posts']]

    def today_code(self):
        return Post.WEEKDAY_CODES[models.now().weekday()]

    def test_recurrence_disabled_shows_always(self):
        ''' With recurrence disabled, the post shows. '''
        p = self.create_post()
        self.assertEqual(self.get_posts_ids([self.feed.id]), [p.id])

    def test_recurrence_enabled_today_included(self):
        ''' Recurrence enabled with today's day included — post shows. '''
        today = self.today_code()
        p = self.create_post(recurrence={
            'enabled': True, 'days': [today]})
        self.assertEqual(self.get_posts_ids([self.feed.id]), [p.id])

    def test_recurrence_enabled_today_excluded(self):
        ''' Recurrence enabled with today's day excluded — post hidden. '''
        today = self.today_code()
        other_days = [d for d in ALL_DAYS if d != today]
        p = self.create_post(recurrence={
            'enabled': True, 'days': other_days})
        self.assertEqual(self.get_posts_ids([self.feed.id]), [])

    def test_recurrence_enabled_no_days_shows(self):
        ''' Recurrence enabled but with empty days list — shows (no
            restriction actually applied). '''
        p = self.create_post(recurrence={
            'enabled': True, 'days': []})
        self.assertEqual(self.get_posts_ids([self.feed.id]), [p.id])

    def test_recurrence_all_days_shows(self):
        ''' Recurrence enabled with all days — post shows. '''
        p = self.create_post(recurrence={
            'enabled': True, 'days': ALL_DAYS})
        self.assertEqual(self.get_posts_ids([self.feed.id]), [p.id])

    def test_recurrence_in_dict_repr(self):
        ''' The dict_repr should include the recurrence field. '''
        p = self.create_post(recurrence={
            'enabled': True, 'days': ['mon', 'wed']})
        repr_data = p.dict_repr()
        self.assertIn('recurrence', repr_data)
        self.assertTrue(repr_data['recurrence']['enabled'])
        self.assertEqual(repr_data['recurrence']['days'], ['mon', 'wed'])

    def test_mixed_recurrence_posts(self):
        ''' A feed with both recurring and non-recurring posts: only the
            ones active today should show. '''
        today = self.today_code()
        other_days = [d for d in ALL_DAYS if d != today]

        p_always = self.create_post()  # no recurrence
        p_today = self.create_post(recurrence={
            'enabled': True, 'days': [today]})
        p_not_today = self.create_post(recurrence={
            'enabled': True, 'days': other_days})

        ids = self.get_posts_ids([self.feed.id])
        self.assertIn(p_always.id, ids)
        self.assertIn(p_today.id, ids)
        self.assertNotIn(p_not_today.id, ids)

    def test_rss_respects_recurrence(self):
        ''' The RSS feed should also respect recurrence rules. '''
        today = self.today_code()
        other_days = [d for d in ALL_DAYS if d != today]

        p_today = self.create_post(title='today', recurrence={
            'enabled': True, 'days': [today]})
        p_not_today = self.create_post(title='hidden', recurrence={
            'enabled': True, 'days': other_days})

        resp = self.client.get(f'/feeds/rss/{self.feed.id}')
        body = resp.data.decode()
        self.assertIn(f'<guid>{p_today.id}</guid>', body)
        self.assertNotIn(f'<guid>{p_not_today.id}</guid>', body)


if __name__ == '__main__':
    import unittest
    unittest.main()
