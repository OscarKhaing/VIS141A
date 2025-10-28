#! /usr/bin/env python

import pygame
import os
# from mpi4py import MPI # note, not an MPI program if commmented, still runs!

os.environ["DISPLAY"] = ":0"
pygame.display.init()
disp_info = pygame.display.Info()
width = disp_info.current_w
height = disp_info.current_h

print(str(height) + " " + str(width))
#print(MPI.Get_processor_name() + " " + str(height) + " " + str(width))



