# -*- coding: utf-8 -*-
# main.py - app with bottle.py framework


import hashlib

from bottle import app, run, get, post, view, template, request, redirect, static_file, response
from google.appengine.ext import db
from beaker.middleware import SessionMiddleware

from models import *
from utils import *


@get('/login')
@view('login-form.html')
def login():
    u = get_session()

    if not u:
        return dict()

    else:
        return redirect('/blog')


@post('/login')
@view('login-form.html')
def login_valid():
    username = request.forms.get('username')
    password = str(request.forms.get('password'))
    pw_hash = hashlib.sha512((password)).hexdigest()
    login = Users.gql("WHERE username = :1 AND pw_hash = :2", username, pw_hash).get()

    if login:
        set_session(username)
        return redirect('/')

    else:
        viewdata = dict(error="Login failed!")
        return viewdata


@get('/logout')
def logout_get():
    session = request.environ.get('beaker.session')
    logged = 'username' in session

    if logged:
        session.delete()

    return redirect('/')


@get('/signup')
@view('signup-form.html')
def signup_get():
    return dict()


@post('/signup')
@view('signup-form.html')
def signup_post():
    have_error = False
    username = request.forms.get('username')
    password = request.forms.get('password')
    verify = request.forms.get('verify')
    email = request.forms.get('email')

    viewdata = dict(username=username,
                  email=email)

    if not valid_username(username):
        viewdata['error_username'] = "That's not a valid username."
        have_error = True

    if not valid_password(password):
        viewdata['error_password'] = "That wasn't a valid password."
        have_error = True

    elif password != verify:
        viewdata['error_verify'] = "Your passwords didn't match."
        have_error = True

    if not valid_email(email):
        viewdata['error_email'] = "That's not a valid email."
        have_error = True

    if have_error:
        return viewdata

    else:
        reg_data = dict(
            username=username,
            password=password,
            email=email)
        key = user_register(**reg_data)

        if key:
            set_session(username)
            return redirect('/')

        else:
            viewdata['error_username'] = "User registration failed."
            return viewdata


@get('/')
@get('/blog')
@get('/blog/')
@view('posts.html')
def blog():
    u = get_session()

    if not u:
        u = "Guest"

    posts, age = get_posts()
    return dict(rows=posts, user=u, age=age_msg(age))


@get('.json')
@get('/.json')
@get('/blog.json')
@get('/blog/.json')
def blog_json():
    resul = posts()
    response.content_type = "application/json; charset=UTF-8"
    return render_json(resul)


@get('/newpost')
@get('/newpost/')
@get('/blog/newpost')
@get('/blog/newpost/')
@view('newpost.html')
def newpost_form():
    u = get_session()

    if not u:
        error = 'You should login first!'
        return template('login-form.html', error=error)

    return dict()


@post('/blog/newpost')
@view('newpost.html')
def newpost_add():
    subject = unicode(request.forms.get('subject'), 'UTF-8')
    content = unicode(request.forms.get('content'), 'UTF-8')

    if subject and content:
        p = Posts(subject=subject, content=content)
        key = p.put()
        if key:
            flush_cache()
            return redirect('/blog/posts/%s' % key)

        else:
            error = "Google Datastore error."
            return dict(error=error)

    else:
        error = "Subject and content are required."
        return dict(error=error)


@get('/blog/posts/<key>')
@get('/blog/posts/<key>.<json>')
@get('/blog/posts/<key>/.<json>')
@view('permalink.html')
def permalink(key, json=None):
    u = get_session()
    memcache_post_key = 'POST_' + key

    post, age = get_age(memcache_post_key)
    if not post:
        post = db.get(key)
        set_age(memcache_post_key, post)
        age = 0

    if post and json:
        response.content_type = "application/json; charset=UTF-8"
        return render_json(post, permalink=True)

    elif post:
        if not u:
            return dict(post=post, age=age_msg(age))

        else:
            return dict(post=post, user=u, age=age_msg(age))

    else:
        return redirect('/')


@get('/flush')
def flush():
    flush_cache()
    return redirect('/')


@get('/favicon.ico')
def favico():
    return static_file('/static/favicon.ico', root='.')


@get('/main.css')
def css():
    return static_file('/static/main.css', root='.')


# Session options - beaker
session_opts = {
    'session.auto': True,
    'session.key': 'user_id',
    'sessiom.type': 'cookie',
    'session.cookie_expires': False,
    'session.path': '/'
}

app = SessionMiddleware(app(), session_opts)
run(server='gae')
