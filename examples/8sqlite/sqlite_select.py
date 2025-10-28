#!/usr/bin/python3

import sqlite3

connection = sqlite3.connect('mydatabase.db')
cursor = connection.cursor()
cursor.execute('SELECT name, lon, lat FROM places')
var = cursor.fetchall()
print(var) 
cursor.close()
connection.close()

