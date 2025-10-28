from mpi4py import MPI

comm = MPI.COMM_WORLD
rank = comm.rank

if rank == 0:
    data = {'a':1,'b':2,'c':3}
else:
    data = None

print('before bcast rank', rank, data)
data = comm.bcast(data, root=0)
print ('after bcast rank', rank, data)

