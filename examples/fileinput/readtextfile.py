#!/usr/bin/python3

# read line by line and add all of the numbers
file_handle = open("textfile.txt", "r")
total = 0

# iterate over the lines
for line in file_handle:
    # read into a list 
    nums = line.split(',')
    # if you were to print now, you would see why we need to remove newlines
    del nums[-1] # removes the last item in a list, this time "\n"
    nums = list(map(int, nums))
    total += sum(nums) 
file_handle.close()

print(total)


