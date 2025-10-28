#!/usr/bin/python3

# delightfully, this is called slurping
file_handle = open("poem.txt", "r")
poem = file_handle.read()
file_handle.close()
print(poem)

# read line by line
file_handle = open("poem.txt", "r")
line = file_handle.readline()
print(line)
print("we just printed the first line.")
# file handles are iterable
for line in file_handle:
	print(line) 
file_handle.close()
print("we have printed the rest of the lines")

file_handle = open("poem.txt", "r")
poem = file_handle.readlines()
file_handle.close()
print(poem)

