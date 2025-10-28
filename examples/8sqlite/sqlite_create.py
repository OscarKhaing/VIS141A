#!/usr/bin/python3

import sqlite3

connection = sqlite3.connect('mydatabase.db')
cursor = connection.cursor()
cursor.execute('CREATE TABLE places (name VARCHAR(20) PRIMARY Key, \
	lat FLOAT, \
	lon FLOAT)')
cursor.close()
connection.close()

