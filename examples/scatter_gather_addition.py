#!/usr/bin/env python
#  scatter_sum_using_Scatter.py
#  Run e.g.:
#     mpirun -n 4 python addparallel.py

from mpi4py import MPI
import numpy as np

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# rank 0 (the head node, primary node, root) holds the initial data 
if rank == 0:
    original = np.arange(1, 16, dtype=np.ubyte)   # 1 .. 15
else:
    original = None

# Again in rank 0` 
# Scatter is dividing up the numpy array among the nodes
# so we need to divide it into arrry / size blocks
if rank == 0:
    total_len   = original.size
    blocksize   = (total_len + size - 1) // size          # ceil division
    padded_len  = blocksize * size
    # Pad with zeros (value 0 does not affect the sum)
    padded = np.zeros(padded_len, dtype=np.ubyte)
    padded[:total_len] = original
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

# Local sum is placed back into a unsigned 32 bit int as, obvs, larger than 255 
local_sum = np.sum(recvbuf, dtype=np.uint32)

# 5) Gather all partial sums to the root
if rank == 0:
    all_sums = np.empty(size, dtype=np.uint32) # remember that size is the number of nodes...
else:
    all_sums = None

comm.Gather(local_sum, all_sums, root=0)

# ------------------------------------------------------------------
# 6) Final result on root
# ------------------------------------------------------------------
if rank == 0:
    total = np.sum(all_sums)
    print("Original data (unpadded):", original)
    print("Padded data sent to Scatter:", padded)
    print("Local sums:", all_sums)
    print("Final sum of 1..15:", total)

