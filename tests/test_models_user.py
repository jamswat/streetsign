'''
    Tests for the User (and Group) peewee ORM models
'''

import sys
import os

sys.path.append(os.path.dirname(__file__) + '/..')

from streetsign_server.models import Feed, User, Group

from unittest_helpers import StreetSignTestCase

#pylint: disable=missing-docstring, invalid-name, too-many-public-methods

class TestUserModel(StreetSignTestCase):

    ''' test the by_id helper function '''

    def test_users_none(self):
        self.assertEqual(User.select().count(), 0)


class TestUserModel_writable_feeds(StreetSignTestCase):

    def test_user_with_no_perms(self):
        u = User(passwordhash='123')
        f = Feed()

        u.save()
        f.save()

        self.assertEqual(u.writeable_feeds(), [])

    def test_user_with_one_feed(self):
        u = User(passwordhash='123')
        f = Feed()

        u.save()
        f.save()

        f.grant('Write', user=u)

        self.assertEqual(u.writeable_feeds(), [f])

    def test_user_with_one_feed_via_group(self):
        u = User(passwordhash='123')
        g = Group(name='group_with_a_name')
        f = Feed()

        u.save()
        f.save()
        g.save()

        g.set_users([u.id])

        f.grant('Write', group=g)

        self.assertEqual(u.writeable_feeds(), [f])

    def test_admin_sees_all_writeable_feeds(self):
        admin = User(passwordhash='123', is_admin=True)
        f = Feed()

        admin.save()
        f.save()

        self.assertEqual(admin.writeable_feeds(), [f])


class TestUserModel_publishable_feeds(StreetSignTestCase):

    def test_user_with_no_perms(self):
        u = User(passwordhash='123')
        f = Feed()

        u.save()
        f.save()

        self.assertEqual(u.publishable_feeds(), [])

    def test_user_with_one_feed(self):
        u = User(passwordhash='123')
        f = Feed()

        u.save()
        f.save()

        f.grant('Publish', user=u)

        self.assertEqual(u.publishable_feeds(), [f])

    def test_user_with_one_feed_via_group(self):
        u = User(passwordhash='123')
        g = Group(name='group_with_a_name')
        f = Feed()

        u.save()
        f.save()
        g.save()

        g.set_users([u.id])

        f.grant('Publish', group=g)

        self.assertEqual(u.publishable_feeds(), [f])

    def test_write_does_not_grant_publish(self):
        u = User(passwordhash='123')
        f = Feed()

        u.save()
        f.save()

        f.grant('Write', user=u)

        self.assertEqual(u.publishable_feeds(), [])

    def test_admin_sees_all_publishable_feeds(self):
        admin = User(passwordhash='123', is_admin=True)
        f = Feed()

        admin.save()
        f.save()

        self.assertEqual(admin.publishable_feeds(), [f])


class TestUserModel_groups(StreetSignTestCase):

    def test_user_with_no_groups(self):
        u = User(passwordhash='123')
        u.save()
        self.assertEqual(u.groups(), [])

    def test_user_with_one_group(self):
        u = User(passwordhash='123')
        g = Group(name='testgroup')

        u.save()
        g.save()
        g.set_users([u.id])

        self.assertEqual(u.groups(), [g])

    def test_user_with_multiple_groups(self):
        u = User(passwordhash='123')
        g1 = Group(name='testgroup1')
        g2 = Group(name='testgroup2')

        u.save()
        g1.save()
        g2.save()
        g1.set_users([u.id])
        g2.set_users([u.id])

        self.assertEqual(len(u.groups()), 2)
        self.assertIn(g1, u.groups())
        self.assertIn(g2, u.groups())


class TestUserModel_set_groups(StreetSignTestCase):

    def test_set_groups_adds_groups(self):
        u = User(passwordhash='123')
        g1 = Group(name='testgroup1')
        g2 = Group(name='testgroup2')

        u.save()
        g1.save()
        g2.save()

        self.assertEqual(u.groups(), [])

        result, groups = u.set_groups([g1.id, g2.id])
        self.assertTrue(result)
        self.assertEqual(len(groups), 2)

        self.assertEqual(len(u.groups()), 2)

    def test_set_groups_replaces_old_groups(self):
        u = User(passwordhash='123')
        g1 = Group(name='testgroup1')
        g2 = Group(name='testgroup2')

        u.save()
        g1.save()
        g2.save()

        g1.set_users([u.id])
        self.assertEqual(len(u.groups()), 1)

        u.set_groups([g2.id])
        self.assertEqual(len(u.groups()), 1)
        self.assertEqual(u.groups(), [g2])

    def test_set_groups_clears_all(self):
        u = User(passwordhash='123')
        g = Group(name='testgroup')

        u.save()
        g.save()
        g.set_users([u.id])
        self.assertEqual(len(u.groups()), 1)

        u.set_groups([])
        self.assertEqual(u.groups(), [])

    def test_set_groups_invalid_id(self):
        u = User(passwordhash='123')
        u.save()

        result, msg = u.set_groups([9999])
        self.assertFalse(result)
        self.assertIn('Invalid', msg)


class TestUserModel_passwords(StreetSignTestCase):

    def test_set_and_confirm_password(self):
        u = User(passwordhash='123')
        u.save()
        u.set_password('testpassword')

        self.assertTrue(u.confirm_password('testpassword'))
        self.assertFalse(u.confirm_password('wrongpassword'))

    def test_password_hash_is_not_plaintext(self):
        u = User(passwordhash='123')
        u.save()
        u.set_password('testpassword')

        self.assertNotEqual(u.passwordhash, 'testpassword')
