import vlc
import time
import os
from mpi4py import MPI

# run with:
# $ mpiexec -n 4 -pernode -machinefile mpi_exec python3 vlc-mpi.py

comm = MPI.COMM_WORLD
rank = comm.Get_rank()

os.environ['DISPLAY'] = ':0.0'
os.system('caffeinate sleep 1')


if comm.rank == 0:
    player = vlc.MediaPlayer("train.mp4")
elif comm.rank == 1:
    player = vlc.MediaPlayer("yeti.mp4")
elif comm.rank == 2:
    player = vlc.MediaPlayer("monkey.mp4")
else: # then it must be 3
    player = vlc.MediaPlayer("cowkiller.mp4")

player.set_fullscreen(True)
comm.Barrier() # this tells all mpi jobs to "wait here" until all are 
               # caught up
player.play()
time.sleep(10)
player.pause()
player.set_fullscreen(False)
player.stop()

