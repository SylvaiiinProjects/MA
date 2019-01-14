import os
from FARMWARE import MyFarmware
from FARMWARE import Sequence
from farmware_tools import log
from structure import Structure
import CeleryPy as cp
from farmware_tools import send_celery_script

FARMWARE_NAME = "jhempbot"

def main():
    log("jhempbot")
    farmware = MyFarmware(FARMWARE_NAME) 
    farmware.run() 
    
if __name__ == "__main__":
    main()
