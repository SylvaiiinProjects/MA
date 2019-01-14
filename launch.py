

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
    farmware = MyFarmware(FARMWARE_NAME) # create the object farmware
    farmware.run() # call the method run() of the module object "farmware"
    
if __name__ == "__main__":
    main() # Launch the function main()
