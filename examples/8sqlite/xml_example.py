#!/usr/bin/python3

import xml.dom.minidom

gpx = ""

#slurp, automatic close of fin
with open("izo.gpx", "rt") as fin:
	gpx = fin.read()

print(gpx)

# this gets the dom object, representing the entire document
dom = xml.dom.minidom.parseString(gpx)
# getElementsByTagName() lets us get a NodeList of all the elements with that name
nodes = dom.getElementsByTagName('wpt')
for node in nodes:
	name = node.getElementsByTagName("name")[0] # how many names are there?
	print(name.firstChild.data + ", " + node.getAttribute('lat') + ", " + node.getAttribute('lon'))
