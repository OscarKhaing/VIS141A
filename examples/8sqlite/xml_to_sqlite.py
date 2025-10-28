#!/usr/bin/python3

import xml.dom.minidom
import sqlite3

gpx = None 

#slurp, close fin handle
with open("izo.gpx", "r") as fin:
    gpx = fin.read()
    fin.close()

# this gets the dom object, representing the entire document
dom = xml.dom.minidom.parseString(gpx)
# open the sqlite database
connection = sqlite3.connect('mydatabase.db')
cursor = connection.cursor()

nodes = dom.getElementsByTagName('wpt')

# insert the gpx data into the database
for node in nodes:
    name = node.getElementsByTagName("name")[0] # how many names are there?
    inserter = "INSERT INTO places (name, lat, lon) VALUES (?,?,?)" 
    cursor.execute(inserter, (name.firstChild.data,  node.getAttribute('lat'),  node.getAttribute('lon')))
connection.commit()
cursor.close()
connection.close()

