meuengenho_blog
===============

Blog app implementation for udacity_cs253 classes, but using [bottle.py](bottlepy.org).

The app was made to run in Google AppEngine, with Google Datastore as database.


### Know issues:


- there's a /flush route to clean memcache. Sometimes when the code is changed, gae returns HTTP 500 because of memcache, don't know why.
 cleaning/flushing memcache solves the problem, just point your browser direct to yourapp.appspot.com/flush.

- JSON API: /<key><.json> not working, don't know why. Use <key>/.json to get the post in json format. /.json and just .json works to get all posts, but with different order in results.

## TODO:

- BETTER DESIGN/LAYOUT;
- Include link to json api in template files.
