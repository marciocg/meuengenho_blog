# -*- coding: utf-8 -*- 
import re, hashlib, logging
from json import dumps as json_dumps
from bottle import app, run, get, post, view, template, request, redirect, static_file, response, request, hook
from google.appengine.ext import db
from google.appengine.api import memcache

from beaker.middleware import SessionMiddleware
from datetime import datetime, timedelta

### Datastore 'Posts' and 'Users' BEGIN

class Posts(db.Model):
    subject = db.StringProperty(required = True)
    content = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    last_modified = db.DateTimeProperty(auto_now = True)


class Users(db.Model):
    username = db.StringProperty(required = True)
    pw_hash = db.StringProperty(required = True)
    email = db.EmailProperty(required = False)

### Datastore 'Posts' and 'Users' END

### SIGNUP VALIDATION BEGIN
USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return not email or EMAIL_RE.match(email)
### SIGNUP VALIDATION END

## Session options
session_opts = {
    'session.auto': True,
    'session.key': 'user_id',
    'sessiom.type': 'cookie',
    'session.cookie_expires': False,
    'session.path': '/'
}


### Functions for dealing with memcache, users, passwords and its hashes

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
    q = list(Posts.all().order('-created').fetch(limit=10))
    memcache_key = 'BLOG'
    posts, age = get_age(memcache_key)
    logging.error('posts e age antes do if %s - %s)' % (posts, age))
    if set_cache or not posts:
        logging.error('entrou no if %s', q)
        logging.error('setcache %s', set_cache)
        logging.error('posts %s', set_cache)
        posts = list(q)
        set_age(memcache_key, posts)     

    return posts, age
    

def age_msg(age):
#    s = 'compilado há %s segundos atrás'
    s = 'Queried %s seconds ago'
    age = int(age)

#    if age < 2:
    if age == 1:
#        s = s.replace('segundos', 'segundo')
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
        user = Users(username = username, pw_hash = pw_hash, email = email)
        key = user.put()
        return key
        
    elif not user and not email:        
        user = Users(username = username, pw_hash = pw_hash)
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


def render_json(dbModel, permalink=False):
    dic = dict()
    if permalink:
        dic['subject'] = dbModel.subject
        dic['content'] = dbModel.content
        dic['created'] = dbModel.created.strftime('%d/%m/%Y %H:%M')
        dic['last_modified'] = dbModel.last_modified.strftime('%d/%m/%Y %H:%M')
        return dic
        
    else:
        res = list()
        for row in dbModel.run():
            dic['subject'] = row.subject
            dic['content'] = row.content
            dic['created'] = row.created.strftime('%d/%m/%Y %H:%M')
            dic['last_modified'] = row.last_modified.strftime('%d/%m/%Y %H:%M')
            res.append(dic)
        return json_dumps(res)

    
### END FUNCTIONS    
@get('/welcome')
@get('unit3/welcome')    
def welcome():
    u = get_session()
    
    if u:
        return 'Welcome, %s', u


@get('/login')
@view('login-form.html')
def login():
    u = get_session()
    
    if not u:
        return dict()
        
    else:
        return redirect('/blog')    


@post('/login')
def login_valid():
    username = request.forms.get('username')
    password = str(request.forms.get('password'))        
    pw_hash = hashlib.sha512((password)).hexdigest()
    login = Users.gql("WHERE username = :1 AND pw_hash = :2", username, pw_hash).get()
    if login:
        set_session(username)
        return redirect('/')
             
    else:
        params = dict(error = "login failed!")
        return template('login-form.html', **params) 

 
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
def signup_post():
    have_error = False
    username = request.forms.get('username')
    password = request.forms.get('password')
    verify = request.forms.get('verify')
    email = request.forms.get('email')

    params = dict(username = username,
                      email = email)

    if not valid_username(username):
        params['error_username'] = "That's not a valid username."
        have_error = True

    if not valid_password(password):
        params['error_password'] = "That wasn't a valid password."
        have_error = True

    elif password != verify:
        params['error_verify'] = "Your passwords didn't match."
        have_error = True

    if not valid_email(email):
        params['error_email'] = "That's not a valid email."
        have_error = True

    if have_error:
        return template('signup-form.html', **params)

    else:
        reg_data = dict(username = username, password = password, email = email)
        logging.error("reg_data values %s ", reg_data)        
        key = user_register(**reg_data)
        
        if key:
            set_session(username)
            return redirect('/')

        else:
            logging.error("key falhou!")    
            params['error_username'] = "User registration failed."            
            return template('signup-form.html', **params)
            

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
        p = Posts(subject = subject, content = content)
        key = p.put()
        if key:
            flush_cache()
            return redirect('/blog/posts/%s' % key)

        else:
            error = "Google error."
            return dict(error=error)
               
    else:
        error = "Subject and content are required."
        return dict(error = error)


@get('/blog/posts/<key>')
@get('/blog/posts/<key>.<json>')
@get('/blog/posts/<key>/.<json>')
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
            return template('permalink.html', post=post, age=age_msg(age))
            
        else:
            return template('permalink.html', post = post, user = u, age=age_msg(age))

    else:
        return redirect('/blog')


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


#app = app()
app = SessionMiddleware(app(), session_opts)
run(server='gae', debug=True)
