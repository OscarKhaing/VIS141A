#!/usr/bin/python3

f = open("fileout.txt", "r")
for line in f:
    values = line.split('^')
    if (values[2].lower().find('ghost') != -1):
        print(values[1] + ", " + values[2])
