# -*- coding: utf-8 -*-
# utils.py - Functions used in the blog app.

import re
import hashlib

from bottle import request
from json import dumps as json_dumps
from datetime import datetime, timedelta
from google.appengine.api import memcache

from models import *

# SIGNUP VALIDATION BEGIN

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")


def valid_username(username):
    return username and USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")


def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE = re.compile(r'^[\S]+@[\S]+\.[\S]+$')


def valid_email(email):
    return not email or EMAIL_RE.match(email)

# SIGNUP VALIDATION END

# Functions for dealing with memcache, users, passwords and its hashes

def set_age(key, val):
    now = datetime.utcnow()
    memcache.set(key, (val, now))


def get_age(key):
    r = memcache.get(key)
    if r:
        val, time_saved = r
        age = (datetime.utcnow() - time_saved).total_seconds()

    else:
        val, age = None, 0

    return val, age


def get_posts(set_cache=False):
    memcache_key = 'BLOG'
    posts, age = get_age(memcache_key)

    if set_cache or not posts:
        q = Posts.all().order('-created').run(limit=10)
        posts = list(q)
        set_age(memcache_key, posts)

    return posts, age


def age_msg(age):
    s = 'Queried %s seconds ago'
    age = int(age)

    if age == 1:
        s = s.replace('seconds', 'second')
    return s % age


def flush_cache():
    memcache.flush_all()


def user_register(**reg_data):
    username = reg_data.pop('username')
    pw_hash = hashlib.sha512((reg_data.pop('password'))).hexdigest()

    if "email" in reg_data:
        email = reg_data.pop('email')

    else:
        email = None

    user = Users.gql("WHERE username = :1", username).get()

    if not user and email:
        user = Users(username=username, pw_hash=pw_hash, email=email)
        key = user.put()
        return key

    elif not user and not email:
        user = Users(username=username, pw_hash=pw_hash)
        key = user.put()
        return key


def set_session(username):
    session = request.environ.get('beaker.session')
    session['username'] = username


def get_session():
    session = request.environ.get('beaker.session')
    logged = 'username' in session

    if logged:
        return session['username']


def render_json(post, permalink=False):
    """ var post: list(dbModel.run()) or db.get() object
    """
    dic = dict()
    if permalink:
        dic['subject'] = post.subject
        dic['content'] = post.content
        dic['created'] = post.created.strftime('%d/%m/%Y %H:%M')
        dic['last_modified'] = post.last_modified.strftime('%d/%m/%Y %H:%M')
        return dic

    else:
        res = list()
        for row in post:
            dic['subject'] = row.subject
            dic['content'] = row.content
            dic['created'] = row.created.strftime('%d/%m/%Y %H:%M')
            dic['last_modified'] = row.last_modified.strftime('%d/%m/%Y %H:%M')
            res.append(dic)
            dic = dict() #cleans dict. If not, the res.append(dic) appends the first result many times; don't know why
        return json_dumps(res)
