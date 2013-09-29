meuengenho_blog
===============

Blog app implementation for udacity_cs253 classes, but using [bottle.py](bottlepy.org).

The app was made to run in Google AppEngine, with Google Datastore as database.


### Known issues:

- there's a /flush route to clean memcache. Sometimes when the code is changed, gae returns HTTP 500 because of memcache, don't know why.
 Cleaning/flushing memcache solves the problem.


## TODO:

- BETTER DESIGN/LAYOUT;
- Include link to json api in template files;
- Include user auth with facebook/google+.
