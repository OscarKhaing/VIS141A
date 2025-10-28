from mpi4py import MPI
import numpy as np

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

if rank == 0:
    # Create a matrix to scatter
    m = np.array(range(size * size), dtype=float).reshape((size, size))
    print("Root process has matrix:\n", m)
else:
    m = None

# Scatter rows of the matrix to each process
local_row = np.empty(size, dtype=float)
comm.Scatter(m, local_row, root=0)

print(f"Process {rank} received: {local_row}")

# Perform computation (e.g., square each element)
local_row = local_row ** 2

# Gather results back to root
recvbuf = None
if rank == 0:
    recvbuf = np.empty((size, size), dtype=float)
comm.Gather(local_row, recvbuf, root=0)

if rank == 0:
    print("Gathered results:\n", recvbuf)
