
from rcon import Console
from rcon.async_support import Console as AsyncConsole
import time
from datetime import datetime
import shutil
import os
from subprocess import check_output
import psutil

config={
    "ip":"192.168.1.236",
    "port":25575,
    "password":"<password>",
    "timeout_duration":5
}

# Backup every X Minutes
BACKUP_FREQUENCY=60
PLAYER_MAP={}

def sendCommand(command):
    print(f"sendCommand: {command}")
    time.sleep(5)
    try:
        con = Console(
            host=config["ip"],
            password=config["password"],
            port=config["port"],
            timeout=config["timeout_duration"]
        )
        res = con.command(command)
        con.close()
    except:
        print("RCON Connection Error!")
        return None
    return res

def newPlayerMap(data):
    NEW_PLAYER_MAP={}
    for row in data.split("\n"):
        if "name" in row and "playeruid" in row and "steamid" in row:
            continue
        split_data = row.split(",")
        if len(split_data) != 3:
            continue
        name, playeruid, steamid = split_data
        count = 1
        if steamid in PLAYER_MAP:
            count = PLAYER_MAP[steamid][1] + 1
        NEW_PLAYER_MAP[steamid]=[name,count]
    return NEW_PLAYER_MAP
    
def compareMaps(new_map):
    connected = []
    disconnected = []
    
    for key in PLAYER_MAP:
        if key not in new_map:
            disconnected.append(PLAYER_MAP[key][0])
            print(f"Disconnected: {key}, {PLAYER_MAP[key]}")
        elif PLAYER_MAP[key][1] == 2:
            connected.append(PLAYER_MAP[key][0])
            print(f"Connected: {key}, {PLAYER_MAP[key][0]}")
        
    return connected, disconnected
    
def broadcastPlayers(connected, disconnected):
    while len(connected) > 0:
        p_join = connected.pop(0)
        p_join = p_join.replace(" ","_")
        retries = 10
        while retries > 0:
            res = sendCommand(f"Broadcast Online:{p_join}")
            if res != None: break
            retries -= 1
    
    while len(disconnected) > 0:
        p_leave = disconnected.pop(0)
        p_leave = p_leave.replace(" ","_")
        retries = 10
        while retries > 0:
            res = sendCommand(f"Broadcast Offline:{p_leave}")
            if res != None: break
            retries -= 1

def TrackPlayers(init=False):
	res = None
	retries = 10
	while retries > 0:
		res = sendCommand("ShowPlayers")
		if res != None: break
		retries -= 1
	if res == None: return
	new_map = newPlayerMap(res)
	connected, disconnected = compareMaps(new_map)
	PLAYER_MAP = new_map
	if len(connected) > 0 and init:
		init = False
	else:
		broadcastPlayers(connected, disconnected)
	return init
		
def SaveGame():
	res = None
	retries = 10
	while retries > 0:
		res = sendCommand("Save")
		if res != None: break
		retries -= 1
	return res
	
# Restart at 5AM every day.
# Announce shutdown every minute (9 -> 1)
def Shutdown(start_time, counter):
	if counter > 0:
		cur_time = int(time.time())
		time_left = cur_time - start_time
		if time_left < (counter * 60):
			minutes = time_left // 60
			seconds = time_left % 60
			message = f"Restarting in {minutes:02d}:{seconds:02d}"
			message = message.replace(" ", "_")
			res = None
			retries = 10
			while retries > 0:
				res = sendCommand(f"Broadcast {message}")
				if res != None: break
				retries -= 1
		counter -= 1
	else:
		now = datetime.now()
		if now.hour == 5 and now.minute < 5:
			# initiate shutdown sequence
			message = "Restarting in 10 minutes."
			message = message.replace(" ", "_")
			res = None
			retries = 10
			while retries > 0:
				res = sendCommand(f"Shutdown 600 {message}")
				if res != None: break
				retries -= 1
			start_time = int(time.time())	
			counter = 9
	return start_time, counter

def Backup(last_backup_time):
	cur_dir = os.getcwd()
	
	try:
		cur_time = int(time.time())
		time_since_last_backup = cur_time - last_backup_time
		if time_since_last_backup > (BACKUP_FREQUENCY * 60):
			now = datetime.now()
			pretty_time = now.strftime("%Y%m%d_%H%M%S")
			# C:\steamcmd\steamapps\common\PalServer\Pal\Saved
			target_dir = os.path.join("C:\\", "steamcmd", "steamapps", "common", "PalServer", "Pal")
			os.chdir(target_dir)
			dir_name = os.path.join(target_dir, "Saved")
			shutil.make_archive(f"backup{pretty_time}.zip", 'zip', dir_name)
			last_backup_time = int(time.time())
			message = "Backup Complete!"
			message = message.replace(" ", "_")
			res = None
			retries = 10
			while retries > 0:
				res = sendCommand(f"Broadcast {message}")
				if res != None: break
				retries -= 1
	except:
		print("ERROR: Backup")
		
	os.chdir(cur_dir)
	return last_backup_time
	
def CheckForUpdates(start_time, counter):
	cur_dir = os.getcwd()
	
	try:
		target_dir = os.path.join("C:\\", "steamcmd")
		os.chdir(target_dir)
		command = "steamcmd.exe +login anonymous +app_update 2394010 +quit"
		output = check_output(command, shell=True)
		
		if "already up to date" not in output.decode():
			message = "Steam Update Available..."
			message = message.replace(" ", "_")
			res = None
			retries = 10
			while retries > 0:
				res = sendCommand(f"Broadcast {message}")
				if res != None: break
				retries -= 1
			# initiate shutdown sequence
			message = "Restarting in 10 minutes."
			message = message.replace(" ", "_")
			res = None
			retries = 10
			while retries > 0:
				res = sendCommand(f"Shutdown 600 {message}")
				if res != None: break
				retries -= 1
			start_time = int(time.time())	
			counter = 9
	except:
		print("ERROR: CheckForUpdates")
	
	os.chdir(cur_dir)
	return start_time, counter

def CheckServerRunning():
	cur_dir = os.getcwd()
	
	try:
		process_list = [p.name() for p in psutil.process_iter()]
		count = 0
		for p in process_list:
			if "PalServer" in p:
				count += 1
		if count == 0:
			# start it up!
			target_dir = os.path.join("C:\\", "steamcmd")
			os.chdir(target_dir)
			command = "launch_palserver.bat"
			output = check_output(command, shell=True)
	except:
		print("ERROR: CheckServerRunning")
		
	os.chdir(cur_dir)

def execute():
	init=True
	start_time = 0
	counter = 0
	last_backup_time = int(time.time())
	while True:
		#1. Track Players
		init = TrackPlayers(init)
		
		#2. Daily Restart
		start_time, counter = Shutdown(start_time, counter)
		
		#3. Check for updates, initiate shutdown
		start_time, counter = CheckForUpdates(start_time, counter)
		
		#4. Hourly Backups
		last_backup_time = Backup(last_backup_time)
		
		#5. Start server if not running.
		CheckServerRunning()
			
if __name__ == '__main__':
	execute()


