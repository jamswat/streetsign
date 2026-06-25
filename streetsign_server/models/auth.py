# -*- coding: utf-8 -*-
#  StreetSign Digital Signage Project
#     (C) Copyright 2013-2015 Daniel Fairhead
#
#    StreetSign is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    StreetSign is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with StreetSign.  If not, see <http://www.gnu.org/licenses/>.
#
#    -------------------------------
'''
===============================================
streetsign_server.models.auth
===============================================

Session tracking and authentication functions.

'''

from uuid import uuid4
from peewee import * # pylint: disable=wildcard-import,unused-wildcard-import

import bcrypt

from .base import DBModel, now, SECRET_KEY, InvalidPassword
from .users import User


class UserSession(DBModel):
    ''' Track user logged in sessions in the database. '''

    id = CharField(primary_key=True) #: unique id
    username = CharField() #: which username?

    user = ForeignKeyField(User, backref='sessions') #: the user
    login_time = DateTimeField(default=now) #: when did they log in?

def user_login(name, password):
    ''' preferred way to get a user object, which checks the password,
        and either returns a User object, or raises an exception '''

    user = User.select().where(User.loginname == name).get()
    # on error, raises: User.DoesNotExist

    if bcrypt.checkpw(
            (password + SECRET_KEY).encode('utf-8'),
            user.passwordhash.encode('utf-8'),
    ):
        session = UserSession(id=str(uuid4()), username=user.loginname,
                                               user=user)
        session.save(force_insert=True)

        return user, session.id
    raise InvalidPassword('Invalid Password!')

def get_logged_in_user(name, session_uuid):
    ''' either returns a logged in user, or raises an error '''
    session = UserSession.get(id=session_uuid, username=name)
    return session.user

def user_logout(name, session_uuid):
    ''' removes a session '''
    UserSession.get(id=session_uuid, username=name).delete_instance()
    return True
