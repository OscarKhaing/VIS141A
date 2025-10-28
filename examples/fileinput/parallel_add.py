#!/usr/bin/env python
#  scatter_sum_using_Scatter.py
#  Run e.g.:
#     mpirun -n 4 python addparallel.py

from mpi4py import MPI
import numpy as np
import time

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# rank 0 (the head node, primary node, root) holds the initial data 
# have rank 0 load the data from the file into a numpy array
if rank == 0:
    # numpy can read comma separated text
    nums = np.genfromtxt('textfile.txt', delimiter=',')
    # the file we are reading has some \n chars in it, this comprehension
    # (~ is not) removes all non number from nums
    nums = nums[~np.isnan(nums)] 
    print("nums as read", nums)
    arraysize = nums.size
    print("nums size: ", nums.size)
    print("nums modulus size: ", nums.size % size)
    nums = nums.astype(np.ubyte) # input is all 0 to 255 so...
    print("nums converted to bytes: ", nums)
    #print("nums sum in rank 0: ", nums.sum())
else:
    original = None

# we want to measure the speed
if rank == 0:
   before = int(time.time()*1000)

# Again in rank 0` 
# Scatter is dividing up the numpy array among the nodes
# so we need to divide it into arrry / size blocks
if rank == 0:
    total_len   = nums.size
    blocksize   = (total_len + size - 1) // size          # ceil division
    padded_len  = blocksize * size
    # Pad with zeros (value 0 does not affect the sum)
    padded = np.zeros(padded_len, dtype=np.ubyte)
    padded[:total_len] = nums 
else:
    padded = None
    blocksize = None

# Broadcast blocksize so all ranks know how big each chunk is
blocksize = comm.bcast(blocksize, root=0)

# Allocate a buffer for the local chunk and Scatter
recvbuf = np.empty(blocksize, dtype=np.ubyte)

# Scatter – all ranks receive `blocksize` elements
# The datatype that matches np.ubyte is MPI.UNSIGNED_CHAR, why? 
# the data set I am using is all 0-255! Saves memory. But
# your data types may differ!
comm.Scatter(padded, recvbuf, root=0)
print(recvbuf)

# Local sum is placed back into a unsigned 32 bit int as, obvs, larger than 255 
local_sum = np.sum(recvbuf, dtype=np.uint32)

# Gather all partial sums to the root
if rank == 0:
    all_sums = np.empty(size, dtype=np.uint32) # remember that size is the number of nodes...
else:
    all_sums = None

comm.Gather(local_sum, all_sums, root=0)

# Final result on root
if rank == 0:
    total = np.sum(all_sums)
    print("time in milis: ",  int(time.time()*1000) - before)
    print("textfile data (unpadded):", sum)
    print("Padded data sent to Scatter:", padded)
    print("Local sums:", all_sums)
    print("Final sum:", total)

