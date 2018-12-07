import os
from farmware_tools import log
from farmware_tools import send_celery_script
import CeleryPy as cp

class MyFarmware():
        
    def __init__(self,farmwarename):
        self.farmwarename = farmwarename

    def move(self, posx, posy, posz, spd):
        """
        pos = [x:Int ,y:Int ,z:Int]
        spd :Int
        """
        log("going to " + str(posx) + ", " + str(posy) + ", " +     str(posz), message_type='debug')
        send_celery_script(cp.move_absolute(location=[posx, posy, posz], offset=[0,0,0], speed=spd))
    
    
    def run(self):
        log("Test two move absolute", message_type='debug')
	self.move(150,150,10,50)
        p= [[100,100,-30],[50,50,50]]
        self.move(p[0][0], p[0][1], p[0][2], 20)
        self.move(p[1][0], p[1][1], p[1][2], 50)
