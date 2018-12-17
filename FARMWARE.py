import time, os
import pickle
import requests
import sys
import xml.etree.ElementTree
from farmware_tools import log
from farmware_tools import send_celery_script as send
import CeleryPy as cp



##List of functions and classes for ease of use
"""
SECONDARY FUNCTION CLASSES:
PlantType(name, lightNeeded, growthTimeS, growthTimeP, growthTimeF)
Plant(kind, pot)
Pot(region, posx, posy, posz)
Region(ident, gs, position)
Structure()
___________________________________________________________________
parameter lists of Structure:
plantTypeList = plant type repository for accessing data for growth needs
waterList = [time]                --> when to water which pot
repotList = dict[time] = [Plant]  --> when to repot a certain plant
plantList = current plants
potList = a list of pots. This is useful for watering.
regionList = a list of the regions... for specific tasks
___________________________________________________________________
methods of Structure:
currDate()
currTime()
uWaterList(step) --> step = interval between water checks
uRepotList()
checkDead()
initFarmLayout()
initPlantTypes()
sendMail(kind) --> kind defines which message to send
"""

##CLASSES
class PlantType():
    def __init__(self, name, lightNeeded, growthTimeS, growthTimeP, growthTimeF):
        """
        name : string
        lightNeeded : int (lumen)
        waterNeeded : int (ml/day)
        growthTimeS : int (days)
        growthTimeP : int (days)
        growthTimeF : int (days)
        """
        self.name = name
        self.lightNeeded = lightNeeded
        self.growthTime0 = growthTimeS
        self.growthTime1 = growthTimeP
        self.growthTime2 = growthTimeF
        
class Plant():
    growthStage = 0
    daysInStage = 0
    plantId = 0
    def __init__(self, kind, pot):
        """
        kind : PlantType
        pot : Pot
        """
        self.kind = kind
        self.pot = pot
        self.id = str(Plant.plantId)
        Plant.plantId += 1
    
class Pot():
    """
    plant : Plant
    full : boolean (presence of peat)
    """
    plant = None 
    full = False
    def __init__(self, ident, region, posx, posy, posz):
        """
        region : Region
        posx : Int
        poxy : Int
        ident : String
        """
        self.region = region
        self.ident = ident
        self.point = cp.add_point(posx, posy, posz, 1)
    

class Region():
    def __init__(self, ident, gs, position):
        """
        gs : int
        position : ((<x1>,<y1>),(<x2>,<y2>))
        ident : string
        """
        self.growthStage = gs
        self.position = position
        self.ident = ident


class Structure():
 
    ##LIST AND VARIABLE INITIALIZATIONS
    plantTypeList = []              #plant type repository for accessing data for growth needs
    waterList = []                  #[time]                --> when to water
    waterAccessList = []             #[[Int,Int,Int]]       --> water access point coords
    repotList = {}                  #dict[time] = [Plant]  --> when to repot a certain plant
    plantList = []                  #current plants
    potList = []                    #a list of pots. This is useful for watering.
    regionList = {}                 #a list of the regions... for specific tasks
    toolList = {"water":[0,0,0], "seeder":[0,0,0], "holer":[0,0,0], "waterSensor":[0,0,0]}

    def __init__(self):
        log("Init - 0 --> structure", message_type='info')
        log("Yes I can!", message_type='info')
        self.initPlantTypes()
        log("Init - 1 --> structure", message_type='info')
        self.initFarmLayout()
        log("Init - 2 --> structure", message_type='info')
        self.uWaterList(2)
        log("Init - 3 --> structure", message_type='info')
        self.loadPlants()
        log("Init - 4 --> structure", message_type='info')
        self.uRepotList()
        log("Init - 5 --> structure", message_type='info')
        
    ##TIME AND DATE FUNCTIONS
    def currDate(self):
        """
        return current date as string in dd/mm/yyyy format
        """
        return str(time.localtime(time.time())[2]) + "/" + str(time.localtime(time.time())[1]) + "/" + str(time.localtime(time.time())[0])
        
    def currTime(self):
        """
        return current time as string in hh:mm format
        """
        return str(time.localtime(time.time())[3]) + ":" + str(time.localtime(time.time())[4]) 
        
    ##UPDATE FUNCTIONS
    def uWaterList(self, step):
        """
        Divide up the day, to water at regular intervals (step).
        """
        for i in range(0, 24):
            if i % step == 0:
                self.waterList.append(i)
        return
        
        
    def uRepotList(self):
        """
        empty old repotList and check each plant for the remaining days, before repot.
        """
        self.repotList == {}
        for plant in self.plantList:
            if plant.growthStage == 0:
                remTime = plant.kind.growthTime0 - plant.daysInStage
            elif plant.growthStage == 1:
                remTime = plant.kind.growthTime1 - plant.daysInStage
            elif plant.growthStage == 2:
                remTime = plant.kind.growthTime2 - plant.daysInStage
                
            if remTime in self.repotList:
                self.repotList[remTime].append(plant)
        return
        
    ##INITIALIZATION FUNCTIONS
    def initFarmLayout(self):
        e = xml.etree.ElementTree.parse('./potLayout.xml').getroot()
        log("Accessed potLayout.xml", message_type='struct')
        for region in e:
            #init regions
            x1 = int(region.attrib["x1"])
            x2 = int(region.attrib["x2"])
            y1 = int(region.attrib["y1"])
            y2 = int(region.attrib["y2"])
            gs = int(region.attrib["gs"])
            ident = int(region.attrib["id"])
            
            self.regionList[region.attrib["id"]] = Region(ident, gs, ((x1, y1), (x2, y2)))
            
            if region.attrib["gs"] == "0":
                #init bacs in region 0
                for bac in region:
                    x1 = int(bac.attrib["x1"])
                    x2 = int(bac.attrib["x2"])
                    y1 = int(bac.attrib["y1"])
                    y2 = int(bac.attrib["y2"])
                    z = int(bac.attrib["z"])
                    border = int(bac.attrib["border"])
                    dist = int(bac.attrib["dist"])
                    
                    for i in range(x1 + border, x2 - border + 1, dist):
                        for j in range(y1 + border, y2 - border + 1, dist):
                            pot = Pot(self.regionList[region.attrib["id"]], i, j, z)
                            self.potList.append(pot)
                            
            else:
                #init pots in other regions
                for pot in region:
                    pot = Pot(pot.attrib["id"], self.regionList[region.attrib["id"]], int(pot.attrib["x"]), int(pot.attrib["y"]), int(pot.attrib["z"]))
                    self.potList.append(pot)
        log("Loaded pot layout.", message_type='info')

    def initPlantTypes(self):
        log("Present o)", message_type='info')
        e = xml.etree.ElementTree.parse('./plantTypes.xml').getroot()
        log("Accessed plantTypes.xml", message_type='info')
        for plantType in e:
            name = plantType.attrib["name"]
            lightNeeded = int(plantType.attrib["lightNeeded"])
            gt0 = int(plantType.attrib["gt0"])
            gt1 = int(plantType.attrib["gt1"])        
            gt2 = int(plantType.attrib["gt2"])     
               
            self.plantTypeList.append(PlantType(name, lightNeeded, gt0, gt1, gt2))
        log("Loaded plant types.", message_type='info')
           
    def savePlants(self):
        log("Saving plant objects.", message_type='info')
        for plant in self.plantList:
            f = open("./plants/" + plant.id + ".txt" , "wb")
            pickle.dump(plant, f)
            f.close()
        log("Saved plant objects.", message_type='info')
            
    def loadPlants(self):
        log("Loading plant objects.", message_type='info')
        for file in os.listdir("./plants"):
            if file != "save.txt":
                if file.endswith(".txt"):
                    f = open("./plants/" + file, "rb")
                    plant = pickle.Unpickler(f).load()
                    self.plantList.append(plant)
                    f.close()
        log("Loaded plant objects.", message_type='info')
        
    ##SEND MAIL FUNCTION(S)
    def sendMail(self, kind):
        """
        Send a mail to the agriculturist, informing hime of 
            0 : Plants that are ready to be moved
            1 : Empty pot spots
            2 : ...
            
            else : an error
        """
        me = "email"
        you = "me"
        if kind == 0:
            textfile = "./plantsDonemsg.txt"
            subject = "There are plants done."
        elif kind == 1:
            textfile = "./needPeatmsg.txt"
            subject = "Some pots need new peat."
        else:
            textfile = "./errormsg.txt"
            subject = "An error occurred."
            
class Sequence:
    def __init__(self, name='New Sequence', color='gray'):
        self.sequence = {
            'name': name,
            'color': color,
            'body': []
            }
        self.add = self.sequence['body'].append

    
##=================================================================##
##===                MAIN PART OF THE PROGRAM                   ===##
##=================================================================##

    """ Define the origin is the most important """

class MyFarmware():  
    
    TOKEN = ''
    
    """
	[x,y,z,iid]	
	1 : planter  / 2 : seeder
    """
    list_tool=[[2676,871,-370,1], [2670,1075,-371,2]]
	
    #coords bac semis for planter tool
    coords_bac=[2000,1000,-410]

    #coords bac semis for seeder tool (offset of tool)
    c=[1980,1000,-360]

    # coords pots
    coords1=[50,80,-30]
    coords2=[-50,-400,-30]

    # coords tools
    planter=[2676,871,-370]
    seeder=[2670,1075,-371]
    seeds=[2650, 770,-320]
  

    def input_env(self):
	self.input_username = os.environ.get("jhempbot"+"_username", "nobodyyy")

    def __init__(self,farmwarename):
        self.farmwarename = farmwarename
	self.input_env()
	
    
    ##FUNCTION CONTROL
    def waterSensor(self):
        water = False
        water = True    #<-- change to check soil sensor...
        return water
        
    def waterFall(self, mm): #<-- implement
        return 
    
    def waiting(self,time):
	log("Waiting {} ms".format(time), message_type='debug')
	info = send(cp.wait(milliseconds=time))
        return info

    ##MOVEMENT
    def moveRel(self, distx, disty, distz, spd):
        """
        distx:Int ,disty:Int ,distz:Int
        spd :Int
        """
        log("moving " + str(distx) + ", " + str(disty) + ", " + str(distz), message_type='debug')
        info = send(cp.move_relative(distance=(distx, disty, distz), speed=spd))
        return info
             
    def move(self, posx, posy, posz, spd):
        """
        posx:Int ,posy:Int ,posz:Int
        spd :Int
        """
        log("going to " + str(posx) + ", " + str(posy) + ", " + str(posz), message_type='debug')
        info = send(cp.move_absolute(location=[posx, posy, posz], offset=[0,0,0], speed=spd))
        return info

    def Read(self, pin, mode, label):
	""" pin : int 64 soil sensor
	    mode : 0 digital 1 analog
	    label : description str
	"""
	
	info = send(cp.read_pin(number=pin, mode=mode, label = label))
	return info

    def Write(self, pin, val, m):
	"""
	   pin : int 10 for vaccum (0 up to 69)
	   val : 1 on / 0 off
	   m   : 0 digital / 1 analog
	"""
	# or send(...)
	info = send(cp.write_pin(number=pin, value=val , mode=m))
        return info
    
    def vacuum_on(self):
	#Sequence0 vaccum on 
	on = Sequence("0", "green")
	on.add(log("Vaccum on ", message_type='info'))
	#on.add(self.waiting(5000))
	#on.add(log("waiting ok", message_type='info'))
	on.add(self.Write(10,1,0))
	send(cp.create_node(kind='execute', args=on.sequence))

    def vacuum_off(self):
	#Sequence01 vaccum off 
	off = Sequence("01", "green")
	off.add(log("Vaccum off ", message_type='info'))
	#off.add(self.waiting(5000))
	#off.add(log("waiting ok", message_type='info'))
	off.add(self.Write(10,0,0))
	send(cp.create_node(kind='execute', args=off.sequence))	

    def water_on(self):
	#Sequence01 vaccum off 
	won = Sequence("02", "green")
	won.add(log("Water on ", message_type='info'))
	#off.add(self.waiting(5000))
	#off.add(log("waiting ok", message_type='info'))
	won.add(self.Write(9,1,0))
	send(cp.create_node(kind='execute', args=won.sequence))	

    def water_off(self):
	#Sequence01 vaccum off 
	wof = Sequence("03", "green")
	wof.add(log("Water off ", message_type='info'))
	#off.add(self.waiting(5000))
	#off.add(log("waiting ok", message_type='info'))
	wof.add(self.Write(9,0,0))
	send(cp.create_node(kind='execute', args=wof.sequence))	
	

    def Reading(self, pin, signal ):
	"""
	    pin : int pin number
	    signal : 1 analog   /   0 digital
	"""

	#Sequence redaing pin value	
	ss = Sequence("40", "green")
        ss.add(log("Read pin {}.".format(pin), message_type='info'))
	ss.add(self.Read(pin, signal,'Soil'))
	ss.add(log("Data loaded.", message_type='info'))
        send(cp.create_node(kind='execute', args=ss.sequence))	

    def exec_seq(self, id):
	info = send(cp.execute_sequence(sequence_id=id))
        return info


    def gohome(self):
	s2 = Sequence("2", "green")
	s2.add(log("Go home ! ", message_type='info'))
	s2.add(self.move(0,0,0,80))
	send(cp.create_node(kind='execute', args=s2.sequence))

    def goto(self, x, y, z):
	g = Sequence("13", "green")
	g.add(self.move(x,y,z,80))
	info = send(cp.create_node(kind='execute', args=g.sequence))
	return info
        
        
    def getTool(self, iid):
	
	#Sequence take planter tool out 
        if iid == 1:
	   t = Sequence("110","green")
           t.add(log("Go get Planter !.", message_type='info'))
           t.add(self.move(self.list_Tool[0][0],self.list_Tool[0][1],0, 90))
	   t.add(self.move(self.list_Tool[0][0],self.list_Tool[0][1], list_Tool[0][2], 90))
	   t.add(self.move(self.list_Tool[0][0]-150, self.list_Tool[0][1], list_Tool[0][2], 90))
	   t.add(self.move(self.list_Tool[0][0]-150, self.list_Tool[0][1],0, 80))
	   info = send(cp.create_node(kind='execute', args=t.sequence))
	
	elif iid == 2:
		tss = Sequence("155","green")
		tss.add(log("Go get Seeder !.", message_type='info'))
        	tss.add(self.move(self.list_Tool[1][0], self.list_Tool[1][1], self.list_Tool[1][2]-150, 90))
		tss.add(self.move(self.list_Tool[1][0], self.list_Tool[1][1], self.list_Tool[1][2], 90))
		tss.add(self.move(self.list_Tool[1][0]-150, self.list_Tool[1][1],self.list_Tool[1][2] , 90))
		tss.add(self.move(self.list_Tool[0][0]-150, self.list_Tool[1][1],self.list_Tool[1][2], 80))
		info = send(cp.create_node(kind='execute', args=tss.sequence))
	return info
      

        
    def putTool(self, iid):

	#Sequence put tool back
	if idd == 1:
		b = Sequence("11", "green")
		b.add(log("Put Planter back !.", message_type='info'))
        	b.add(self.move(self.planter[0]-150, self.planter[1], self.planter[2], 80))
		b.add(self.move(self.planter[0], self.planter[1], self.planter[2]+1, 80))
		#up to 0 to leave tool
		b.add(self.move(self.planter[0], self.planter[1],-150, 80))
		send(cp.create_node(kind='execute', args=b.sequence))
        
	elif iid == 2:
		#Put seeder tool back
		ba = Sequence("11", "green")
		ba.add(log("Put seeder back !.", message_type='info'))
	        ba.add(self.move(self.c[0],self.c[1]-46,0, 80))
		ba.add(self.move(self.seeder[0]-150, self.seeder[1],0, 80))
		ba.add(self.move(self.seeder[0]-150, self.seeder[1],self.seeder[2], 80))
		ba.add(self.move(self.seeder[0], self.seeder[1],self.seeder[2], 80))
		ba.add(self.move(self.seeder[0], self.seeder[1],0, 80))
		send(cp.create_node(kind='execute', args=ba.sequence))
        



    def calibrate(self):
        try:
            i = 0
            while True and i<21:
                self.moveRel(100,0,0,50)
                i += 1
        except:
            pass
        try:
            i = 0
            while True and i<14:
                self.moveRel(0,100,0,50)
                i += 1
        except:
            pass
        try:
            i = 0
            while True and i<4:
                self.moveRel(0,0,100,50)
                i += 1
        except:
            pass 
              
    ##SEQUENCES   
    def water(self):
        whereWater = []
        l = self.s.waterAccessList
        self.getTool("waterSensor")
        for i in l:
            self.goto(i[0], i[1], i[2])
            sensor = waterSensor()
            while sensor == False:
                self.move(i[0], i[1], self.coords[2] - 20, 20)
                self.coords[2] -= 20
            whereWater.append(i[2]-self.coords[2])
        self.putTool("waterSensor")
        self.getTool("water")
        for i in range(len(l)):
            if whereWater[i] > 0:
                self.goto(l[i][0], l[i][1], l[i][2])
                self.waterFall(whereWater[i])
        self.putTool("water")
    
    def repot(self):
        return            
              
                  
    ##START POINT

    def run(self):
	log("Hello {}".format(self.input_username), message_type='info')
        log("Farmware running...", message_type='info')
       
	# implement try : except : in case of network loss
	# Test goto function
	self.goto(self.coords1[0], self.coords1[1], self.coords1[2])
	self.gohome()

	self.Reading(63,1)
	self.waiting(2000)
	self.Reading(64,1)	

	#Sequence take planter tool out 
	self.getTool(self.list_tool[0][3])	
	self.gohome()

		
	
	# Sequence1 ligne bac semis avec outil planter
        s = Sequence("1", "green")
	s.add(log("First move.", message_type='info'))
        s.add(self.move(self.coords_bac[0], self.coords_bac[1], 0, 80))
	s.add(self.moveRel(0,0,-410,100))
	s.add(self.moveRel(0,0,60,80))

	# Loop if for each rows
	for i in range(1,4):
		s.add(self.move(self.coords_bac[0], self.coords_bac[1]-i*46, -350, 80))
		s.add(self.moveRel(0,0,-60,100))
		s.add(self.moveRel(0,0,40,100))
	s.add(self.moveRel(0,0,100,100))
     	send(cp.create_node(kind='execute', args=s.sequence))
	#sys.exit(0) doesn't work

	#Put planter tool back
	self.putTool(1)

	#Sequence take seeder tool out 
	self.putTool(2)
	
	###
	#Go above seeds
	self.goto(self.seeder[0]-150, self.seeder[1],-200)
	self.goto(self.seeds[0],self.seeds[1],-200)
	self.goto(self.seeds[0],self.seeds[1],self.seeds[2])

	#Vacuum
	self.vacuum_on()
	self.goto(self.seeds[0],self.seeds[1],0)
	
	#go to bac seeder
	self.goto(self.c[0],self.c[1]-46,-200)
	self.goto(self.c[0],self.c[1],self.c[2])

	#Vacuum
	self.vacuum_off()

	#### Do loop if..
	#Go above seeds
	self.goto(self.c[0], self.c[1],0)
	self.goto(self.seeds[0],self.seeds[1],-200)
	self.goto(self.seeds[0],self.seeds[1],self.seeds[2])

	#Vacuum
	self.vacuum_on()
	self.goto(self.seeds[0],self.seeds[1],0)
	
	#go to bac seeder
	self.goto(self.c[0],self.c[1]-46,-200)
	self.goto(self.c[0],self.c[1]-46,self.c[2])

	#Vacuum
	self.vacuum_off()
	

	#Put seeder tool back
	self.putTool(2)
	

	#go to bac seeder
	self.goto(self.c[0]-30,self.c[1]-20,-200)
	self.goto(self.c[0]-30,self.c[1]-20,self.c[2])

	#Water on
	self.water_on()
	self.waiting(2000)
	self.water_off()

	#Sequence2 home
	self.gohome()
	
	
	
	#Sequence3
	#s3 = Sequence("3", "green")
	#s3.add(self.moveRel(0,0,-180,80))
	#s3.add(self.moveRel(0, 0, 180, 80))
	#send(cp.create_node(kind='execute', args=s3.sequence))

	
	#Sequence4
	#s4 = Sequence("4", "green")
	#s4.add(log("Try to move to pot 2", message_type='info'))
	#s4.add(self.move(self.coords2[0],self.coords2[1],180,80))
	#s4.add(self.moveRel(0,0,-180,80))
	#s4.add(self.moveRel(0, 0, 180, 80))
	#send(cp.create_node(kind='execute', args=s4.sequence))

	#Sequence6
	#s6 = Sequence("6", "green")
	#s6.add(self.move(-700,-600,50,80))
	#send(cp.create_node(kind='execute', args=s6.sequence))
	

	#Sequence7
	#s7 = Sequence("7", "green")
	#s7.add(log("Get a tool", message_type='info'))
	#s7.add(self.moveRel(0, 0, 130, 80))
	#s7.add(self.move(self.tool1[0],self.tool1[1],130,80))
	#s7.add(self.move(self.tool1[0],self.tool1[1],self.tool1[2],50))
	#s7.add(self.move(self.tool1[0]-150,self.tool1[1],self.tool1[2],50))
	#s7.add(self.moveRel(0, 0, 130, 80))
	#s7.add(self.move(self.coords2[0],self.coords2[1],180,80))
	#send(cp.create_node(kind='execute', args=s7.sequence))


       
        
        
        ##TESTS
        
        #self.s.sendMail(0)
        #self.s.initFarmLayout()
        #self.s.initPlantTypes()
        #print(struct.currDate())
        #print(struct.currTime())
        #print(list(pot.region.ident for pot in self.s.potList))
        #print(list(self.s.regionList[region].ident for region in self.s.regionList))
        #print(list(pt.name for pt in self.s.plantTypeList))
        #print("lol Sylvain") 
        #plant pickle test
        #self.s.plantList.append(Plant("plant1", potList[0].ident))
        #print(list(plant.id for plant in plantList))
        #savePlants()
        """
        print(struct.plantList, " <-- plantlist")
        print(struct.waterAccessList, " <-- waterAccessList")
        print(struct.plantTypeList, " <-- plantTypeList")
        print(struct.waterList, " <-- waterList")
        print(struct.repotList, " <-- repotList")
        print(struct.potList, " <-- potList")
        print(struct.regionList, " <-- regionList")
        print(struct.toolList, " <-- toolList")
        """
        #loadPlants()
        #print(list(plant.id for plant in plantList))
        
      
