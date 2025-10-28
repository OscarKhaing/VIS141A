#!/usr/bin/python3

import sqlite3

connection = sqlite3.connect('mydatabase.db')
cursor = connection.cursor()
cursor.execute('INSERT INTO places VALUES("a place", 32.555555, -116.888888)')
cursor.execute('INSERT INTO places VALUES("another place", 32.444444, -116.222222)')
connection.commit() # this actually causes the rows to be added to mydatabase.db
cursor.close()
connection.close()

