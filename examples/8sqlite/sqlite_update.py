#!/usr/bin/python3

import sqlite3

connection = sqlite3.connect('mydatabase.db')
cursor = connection.cursor()
cursor.execute('UPDATE places SET name="a new name" WHERE name LIKE "%another%"')
connection.commit() # this actually causes the rows to be added to mydatabase.db
cursor.close()
connection.close()

