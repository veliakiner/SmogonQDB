from google.appengine.api import memcache
from google.appengine.ext import db

#cache the following:
#individual quotes
#pages ?

def return_quote(quote_id): #returns an individual quote from cache, or updates it
    quote_id=str(quote_id)
    key="quote_"+quote_id
    quote=memcache.get(key)
    if quote is None:
        quote=db.GqlQuery("SELECT * FROM DBQuote WHERE quote_id=:x",x=int(quote_id)).get()
        memcache.set(key,quote) # add to/update cache
    return quote

def update_quote(quote_id,quote): #updates database and cache at the same time with quote object
    quote_id=str(quote_id)
    key="quote_"+quote_id
    quote.put()
    memcache.set(key,quote)
    return

def remove_quote(quote_id):
    #remove quote id from db
    key="ID_list"
    result=db.GqlQuery("SELECT * FROM ID_list").get() #id list
    if len(result.IDs)==1:
        result.delete() #don't leave an empty id_list, that will bork shit up
    else:
        result.IDs.remove(int(quote_id))
        result.put()
    #remove quote from db
    quote_id=str(quote_id)
    quote=db.GqlQuery("SELECT * FROM DBQuote WHERE quote_id=:x",x=int(quote_id)).get()
    quote.delete() #remove quote
    #flush the cache after this operation, would be better if instance was removed from cache but w/evs
    memcache.flush_all()
    return

def return_ip(ip): #returns unique ID which is a combination of IP address and link id
    key=ip
    query=memcache.get(key)
    if query is None:
        query=db.GqlQuery("SELECT * FROM Visitor where ip=:ip",ip=ip).get()
        memcache.set(key,query)
    return query

def update_ip(ip,visitor): #updates the unique ID with updated visitor object, which contains the last visit time
    key=ip
    visitor.put()
    memcache.set(key,visitor)
    return

def return_ID_list(): #returns an object with list with quote IDs
    key="ID_list"
    result=memcache.get("ID_list") #result is object containing the list of quote IDs
    if result is None: #not in cache, go to database
        result=db.GqlQuery("SELECT * FROM ID_list").get()
        memcache.set(key,result)
    return result

def update_ID_list(quote_id,id_list_obj): #id_list_obj is object containing id list
    #needs object else it puts a new instance of the ID list instead of editing the existing one
    key="ID_list"
    id_list_obj.IDs.append(quote_id) #update with quote id
    id_list_obj.put() #update db
    memcache.set(key,id_list_obj) #update cache

def highest_quote_ID(): #get the highest number
    ID_list_object=return_ID_list() #get object containing the list of IDs
    if ID_list_object is None: #db was empty, so no IDs yet
        return 0
    return max(ID_list_object.IDs)
