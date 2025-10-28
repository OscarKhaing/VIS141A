# same code as googlebooks.py but writes to a file, so that queries could
# saved and used locally instead of calling the api multiple times.

import json
import time
import traceback
from urllib.request import urlopen

# index counts the last index recieved 
index = 0
# the base url
baseurl = 'https://www.googleapis.com/books/v1/volumes?maxResults=40&langRestrict=en&orderBy=relevance&projection=full&q='
# start index is added to deal with moving forward in the results
# this is your api key to id yourself to google - don't use mine please
apikey = '&key:AIzaSyDkssR71hwu9Nvd-216J_7YqJZxIdlQWow'
# query string
query = "Calzona,%20California"
# we are going to count on a exception to determine when we are done

# a little function to help us write data
def append_data(file, *params):
        f = open(file, "a")
        f.write('^'.join(params))
        f.write('\n')
        f.close()

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
        description = '' # same as subtitle, need to check for it 
        if 'description' in book['volumeInfo']:
            description = book['volumeInfo']['description']
        index += 1 # keep track of the index so we can start the next url
        append_data("fileout.txt", \
                        book['id'], \
                        book['volumeInfo']['title'], \
                        subtitle, \
                        description)
