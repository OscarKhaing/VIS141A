#!/usr/bin/python3

import sqlite3

connection = sqlite3.connect('mydatabase.db')
cursor = connection.cursor()
cursor.execute('SELECT * FROM places WHERE name like "%another%"')
var = cursor.fetchall()
print(var) 
connection.close()

