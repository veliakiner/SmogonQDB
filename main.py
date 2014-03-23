import os
import webapp2
import jinja2
from google.appengine.ext import db
from datetime import datetime
import time
import re
import sys
from time import sleep
import qdb_cache
from date_convert import date_convert
import cgi
from google.appengine.api import memcache

def escape_html(s):
    return cgi.escape(s,quote =True)

template_dir = os.path.join(os.path.dirname(__file__),'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),autoescape = True)

quotes_per_page=20
salt="KqGV3nlE2lkdQEWqo3em"
pwhash='058310394b0190924a6786ed6532419c4df82d666814fc5b1ad57b77239e3962'
#data classes
class DBQuote(db.Model):
    quote=db.TextProperty(required = True) #quote content, needs to be text as string's character limit is too low
    submitter_id=db.StringProperty(required = True) #name of submitter
    quote_id=db.IntegerProperty(required = True) #id starting from 1
    score=db.IntegerProperty(required = True,default=0)
    TimeSubmitted=db.DateTimeProperty() #all following attributes to be required once database is cleared; only not so to prevent error of existing data being entered before addition of these attributes
    Time=db.StringProperty()
    submitter_ip=db.StringProperty()
    Flagged=db.BooleanProperty(default=False)
    imgurl=db.StringProperty()

class Visitor(db.Model):
    ip=db.StringProperty(required = True) #consists of an IP address concatenated with the quote id
    Banned=db.BooleanProperty(required = True) #used to prevent banned users from voting, not implemented yet
    last_voted=db.FloatProperty(required = True) #a number in seconds to allow quick calculation of time since last vote, should really be calculated form a date

class ID_list(db.Model):
    IDs=db.ListProperty(int)

#handlers
class Handler(webapp2.RequestHandler):
    def write(self,*a, **kw): #write and render are simply easier to type out than what they replace
        self.response.out.write(*a,**kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

#handlers
class Submit(Handler):
    def get(self):
        self.render('submit.html')

    def post(self):
        content = self.request.get('quote')
        submitter=self.request.get('submitter_id')
        imgurl=self.request.get('imgurl')
        ip=str(self.request.remote_addr) #convenient variable type for database
        if imgurl and not re.match(r'http://.*(\.jpg|\.png|\.gif|\.bmp|\.tif)',imgurl): #ensures image URL is valid and of an image
            self.render('submit.html',error="Invalid image url.",submitter_id=submitter,imgurl=imgurl)
        elif content:
            if not submitter:
                submitter='Anonymous'
            quote_number=qdb_cache.highest_quote_ID() #highest current quote number
            if quote_number==0: #empty, initialize empty id list
                id_list=ID_list(IDs=[1]) #can't have an empty list because db query will return none instead of empty list
                id_list.put() #stick in database
                sleep(0.1)#to give db time to store the list
            quote_id=quote_number+1 #get quote id for this quote that's being submitted
            id_list_obj=qdb_cache.return_ID_list() #get current id list
            time=datetime.now()
            #TimeSubmitted is in DateTime type, Time is a string ready to be displayed in HTML
            #create quote object
            quote=DBQuote(quote=content,submitter_id=submitter,quote_id=quote_id,TimeSubmitted=time,Time=date_convert(time),submitter_ip=ip,imgurl=imgurl)
            qdb_cache.update_quote(quote_id,quote)
            if quote_id!=1: #1 already in the id list since there had to be at least one number in there upon init.
                qdb_cache.update_ID_list(quote_id,id_list_obj)
            sleep(0.1) #required because the homepage gets loaded before the database is updated, just looks a bit messy to refresh page 
            self.redirect('/')
        else:
            self.render('submit.html',error="Content required.",submitter_id=submitter,imgurl=imgurl)

class MainPage(Handler): #home page displaying most recent quotes
    def get(self):
        quote_ids=qdb_cache.return_ID_list()
        if quote_ids is None:#database is empty
            quotes=[]
        else:
            quote_ids=quote_ids.IDs #get quote IDs
            quote_ids.sort()
            quote_ids.reverse() #most recent first
            #quotes_per_page=20 #set at start of file
            quote_list=quote_ids[:quotes_per_page] #gets latest quotes, or all if quotes per page>total
            quotes=[qdb_cache.return_quote(id) for id in quote_list]
        self.render('mainpage.html',quotes=quotes)

class Permalink(Handler): #link to individual quote
    def get(self,i_d):
        if re.match(r'[0-9]*',i_d): #make sure it's only a number just in case a non-integer id does slip into the database
            #query=db.GqlQuery("SELECT * FROM DBQuote WHERE quote_id=:x",x=int(i_d)).get() #without memcached
            query=qdb_cache.return_quote(i_d)
        else:
            query=None
        if query: #makes sure only the specified quote is displayed, if any
            self.render("singlequote.html",DBQuote=query)
        else:
            self.redirect('/error')
    
def not_spammer(ip): #Currently makes sure that a quote is not voted on by the same IP address more than once every hourlimit hours
    hourlimit=24
    secondlimit=hourlimit*3600
    query=qdb_cache.return_ip(ip) #cache this shit otherwise you have to hit the db each time to check if the user can vote
    if not query or (time.time()-query.last_voted)>secondlimit:
        return True
    return False
    
class Vote(Handler): #allows up- and downvoting
    def get(self,u_or_d,i_d): #u_or_d decides whether the vote is up or down
        if re.match(r'[0-9]*',i_d): #make sure it's only a number just in case a non-integer id does slip into the database
            ip = '"'+str(self.request.remote_addr)+':'+str(i_d)+'"' #unique ID for quote ID/IP address combination
            query=qdb_cache.return_quote(i_d)
        if not_spammer(ip):
            delta={'u':1,'d':-1}
            query.score+=delta[u_or_d] #upvotes for u, downvotes for d
            qdb_cache.update_quote(i_d,query) #update cache and db
            visitor=Visitor(ip=str(ip),last_voted=time.time(),Banned=False) #updates visitor with the new last voted time
            qdb_cache.update_ip(ip,visitor) #update db and cache with new visitor instance
            self.write('Your vote was recorded. <a href=\'/\'>Return to the main page.</a>')
        else:
            self.write('You\'re doing that too much. Try again in 24 hours.')

class Top(Handler): #displays top-voted links
    def get(self):
        quotes=db.GqlQuery("SELECT * FROM DBQuote ORDER BY score DESC")
        self.render('top.html',quotes=quotes)

class Flag(Handler): #allows quotes to be flagged for moderation
    def get(self,i_d):
        if re.match(r'[1-9][0-9]*',i_d): #make sure i_d is a number; this code is repeated elsewhere so there's probably a better way of doing it
            query=qdb_cache.return_quote(i_d)
        else:
            query=None
        if not query:
            self.write(query)
            return
            self.redirect('/error')
        else:
            if query.Flagged==False:
                query.Flagged=True #mark quote as flagged
                qdb_cache.update_quote(i_d,query) #update quote with flagged status
                self.write('Quote flagged for moderation. <a href=\'/\'>Return to the main page.</a>') #placeholder message until page is written
            else:
                self.write('Quote already flagged. Someone else doesn\'t like it either!')

class Unflag(Handler): #removes flag
    def get(self,i_d):
        if re.match(r'[1-9][0-9]*',i_d): #make sure i_d is a number; this code is repeated elsewhere so there's probably a better way of doing it
            query=qdb_cache.return_quote(i_d)
        else:
            query=None
        if not query:
            self.write(query)
            return
            self.redirect('/error')
        else:
            if query.Flagged==True:
                query.Flagged=False #mark quote as flagged
                qdb_cache.update_quote(i_d,query) #update quote with flagged status
                self.write('Quote flag removed. <a href=\'/\'>Return to the main page.</a>') #placeholder message until page is written
            else:
                self.write('Quote flag already removed. <a href=\'/\'>Return to the main page.</a>')
        
class Delete(Handler): #deletes quote
    def get(self,i_d):
        if re.match(r'[1-9][0-9]*',i_d): #make sure i_d is a number; this code is repeated elsewhere so there's probably a better way of doing it
            qdb_cache.remove_quote(i_d)
            self.write('Quote removed from database. <a href=\'/\'>Return to the main page.</a>')

class Error(Handler): #default error page
    def get(self):
        self.write('Whoops! You\'ve entered an invalid url. Return to the <a href="/">main page</a>.') #placeholder message until error page is written

from random_list import random_list

class Random(Handler): #page with random quotes #WITH CACHE
    def get(self):
        #quotes_per_page=20 #set at start of file
        quote_id_list=qdb_cache.return_ID_list().IDs # list of quote ids
        rand_id_list=random_list(quote_id_list,quotes_per_page)#gives a list up to quotes_per_page long of quote_id_list numbers selected at random
        random_quotes=[qdb_cache.return_quote(quote_id) for quote_id in rand_id_list] #list of random quotes
        self.render('page.html',quotes=random_quotes,param='Random')

class Test(Handler): #miscellaneous handler to test various things
    def get(self):
        g=ID_list(IDs=[1,2,3])
        g.put()
        self.write(g.IDs)

import hashlib
def make_pw_hash(pw,salt):
    if not pw:
        pw=''
    h=hashlib.sha256(pw+salt).hexdigest()
    return h

class Admin(Handler): #currently only displays flagged quotes, to implement: approval or rejection of flagged quotes
    def get(self):
        pw=self.request.cookies.get('password')
        if pwhash==make_pw_hash(pw,salt):   
            flagged=db.GqlQuery("SELECT * FROM DBQuote WHERE Flagged=True")
            self.render('admin.html',quotes=flagged)
        else:
            self.render("login.html")
            #self.write("Something went wrong. <a href='\'>Return to the main page.</a>")
    def post(self):
        pw=self.request.get('password')
        self.response.headers.add_header('Set-Cookie', 'password=%s; Path=/' % str(pw))
        if pwhash==make_pw_hash(pw,salt):
            self.redirect('/admin')
        else:
            self.render('login.html',error='Invalid password.')

class Page(Handler): #takes a list of quotes and returns a certain number of them. For example: for 20 quotes per page and a list ordered by rating, page 1 would have the top 20, page 2 the next 20, and so on
    def get(self,page_number,order):
        self.write(order)
        quotes_per_page=3
        page_number=int(page_number[5:])
        start=1+(page_number-1)*quotes_per_page
        end=start+quotes_per_page-1
        if qdb_cache.highest_quote_ID>start:
            self.redirect('/error')
        else:
            quotes=db.GqlQuery("SELECT * FROM DBQuote WHERE quote_id >= :x AND quote_id <= :y",x=start,y=end)
            self.render('top.html',quotes=quotes)
        
        #self.render('page.html')
        
app = webapp2.WSGIApplication([
    ('/',MainPage),
    ('/submit/?', Submit),
    ('/([1-9]+[0-9]*)/?',Permalink), #link to individual quote
    ('/([ud])/([1-9]+[0-9]*)/?',Vote), #link to vote on individual quote
    ('/(page_[1-9]+[0-9]*)([a-zA-Z0-9]*)/?',Page),
    ('/top/?',Top),
    ('/flag/([1-9]+[0-9]*)/?',Flag), #link to flag individual quote for moderation
    ('/unflag/([1-9]+[0-9]*)/?',Unflag),
    ('/delete/([1-9]+[0-9]*)/?',Delete),
    ('/random/?',Random), #link to page with 10 random quotes
    ('/admin/?',Admin),
    ('/error/?',Error),
    ('/test/?',Test),
    ('/.*',Error) #Anything else that isn't specified above will automatically go to the error page THIS MUST BE AT THE END
], debug=True)
