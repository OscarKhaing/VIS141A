#!/usr/bin/python3

import sqlite3

connection = sqlite3.connect('mydatabase.db')
cursor = connection.cursor()
cursor.execute('DELETE FROM places WHERE name like "S2%"')
connection.commit() # this actually causes the changes to be saved
cursor.close()
connection.close()

