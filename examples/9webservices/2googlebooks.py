# Google books api, which is mostly free
# more info:
# https://developers.google.com/books/docs/overview
# https://developers.google.com/books/docs/v1/using
# Google API console:
# console.cloud.google.com
# note: you have to get your own google books api key to use this example.
# (actually it works for a bit with a bad key...)

import json
import time
from urllib.request import urlopen

# index counts the last index recieved 
index = 0
# the base url
baseurl = 'https://www.googleapis.com/books/v1/volumes?maxResults=40&langRestrict=en&orderBy=relevance&projection=full&q='
# start index is added to deal with moving forward in the results
# this is your api key to id yourself to google - don't use mine please
apikey = '&key:AIzaSyDkssR71hwu9Nvd-216J_7YqJZxIdlQWow'
# query string
query = "Brett%20Stalbaum"

# the value of totalItems changes, so using an 'infinite' loop
# and just quit when we get a result with zero items

while True:    
    startIndex = '&startIndex=' + str(index) # how many items into the results
    url = baseurl + query + startIndex + apikey
    print(url)
    response = urlopen(url)
    contents = response.read()
    text = contents.decode('utf8')
    data = json.loads(text)
    #print(text) # full results for debug
    current_items = 0
    if 'items' in data: # if there are no items, see previous line, 0 items
        current_items = len(data['items'])
    if current_items == 0: # we are done, no more items to parse
        break
    print('api claims ', data['totalItems'], \
        ' total items current count is ', index)
    print('with ', len(data['items']), ' items in this json')
    for book in data['items']:
        # volumeInfo->title and and id seem to be attached to every book
        # but not every book has volumeInfo->subtitle, so we check for it first 
        subtitle = '' # set to empty string
        if 'subtitle' in book['volumeInfo']:
            subtitle = book['volumeInfo']['subtitle'] 
        index += 1 # keep track of the index so we can start the next url
        print("result " + str(index), book['volumeInfo']['title'], \
            subtitle, book['id'])
