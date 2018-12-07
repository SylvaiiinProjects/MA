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
        send_celery_script(cp.wait(milliseconds=10000))
        self.move(250,200,50,80)
