# -*- coding: utf-8 -*- 
import re, hashlib, logging
from json import dumps as json_dumps
from bottle import app, run, get, post, view, template, request, redirect, static_file, response, request
from google.appengine.ext import db

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

### Functions for dealing with cookies, users, passwords and its hashes
secret = str("*(AH9ah89*AH98habab  )")
#COOKIE_DATA = dict()

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
        
    else:        
        return False        

def setcookie_secure(**cookie):
    response.set_cookie(cookie["userid"], cookie["username"], secret=cookie["secret"], path="/", domain="localhost", httponly=True)
    return True

def getcookie_secure(name="userid"):
    cookie = request.get_cookie(name, secret=secret)
    return cookie

def delcookie():
    return response.set_header('Set-Cookie', 'userid=deleted; Max-Age=0; Path=/; Domain=localhost; HttpOnly')    

def render_json(dbModel, permalink=False):
    dic = dict()
    res = list()
    if permalink:
        dic['subject'] = dbModel.subject
        dic['content'] = dbModel.content
        dic['created'] = dbModel.created.strftime('%d/%m/%Y %H:%M')
        dic['last_modified'] = dbModel.last_modified.strftime('%d/%m/%Y %H:%M')
        res.append(dic)
        
    else:
        for row in dbModel.run():
            dic['subject'] = row.subject
            dic['content'] = row.content
            dic['created'] = row.created.strftime('%d/%m/%Y %H:%M')
            dic['last_modified'] = row.last_modified.strftime('%d/%m/%Y %H:%M')
            res.append(dic)
        
    return json_dumps(res)

def posts():
    return Posts.all().order('-created')
    
### END FUNCTIONS    
    
@get('/login')
@view('login-form.html')
def login():
    u = request.get_cookie("userid", secret=secret)
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
        cookie = dict(userid="userid", username=username, secret=secret)
        setcookie_secure(**cookie)
            
    else:
        params = dict(error = "login failed!")
        return template('login-form.html', **params) 

 
@get('/logout')
def logout_get():
    delcookie()

             
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
            logging.error("key ok! str: %s", key)            
            cookie = dict(userid="userid", username=username, secret=secret)
            setcookie_secure(**cookie)
#            return redirect('/login')

        else:
            logging.error("key falhou!")    
            params['error_username'] = "User registration failed."            
            return template('signup-form.html', **params)
            

@get('/')
@get('/blog')
@get('/blog/')
@view('posts.html')
def blog():
    u = getcookie_secure()

    if not u:       
        u = "Guest"
                            
    resul = posts()
    return dict(rows = resul, user = u)


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
    return dict()


@post('/blog/newpost')
@view('newpost.html')
def newpost_add():    
    subject = request.forms.get('subject')
    content = request.forms.get('content')
    
    if subject and content:
        p = Posts(subject = subject, content = content)
        key = p.put()
        return redirect('/blog/posts/%s' % key)
        
    else:
        error = "Subject and content are required."
        return dict(error = error)


@get('/blog/posts/<key>')
@get('/blog/posts/<key>.<json>')
@get('/blog/posts/<key>/.<json>')
def permalink(key, json = None):
    u = getcookie_secure()
    post = db.get(key)

    if post and json:
        response.content_type = "application/json; charset=UTF-8"
        return render_json(post, permalink=True)
        
    elif post:
        if not u:
            return template('permalink.html', post = post)
            
        else:
            return template('permalink.html', post = post, user = u)

    else:
        return redirect('/blog')


### DIDN'T WORKED:        
#@get('/<filename>')
#def static(filename):
#    if filename is ('favicon.ico' or 'main.css'):
#        return static_file('filename', root='static')
###


@get('/favicon.ico')
def favico():
    return static_file('/static/favicon.ico', root='.')


@get('/main.css')
def css():
    return static_file('/static/main.css', root='.')


app = app()
run(server='gae', debug=True)
        
