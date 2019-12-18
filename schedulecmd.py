import os
import subprocess
import re

from carCommands import carCommands

def getCommandScript(carCommand):
    if(carCommand == carCommands.STARTSTOP):
        return "startstop.sh"
    elif(carCommand == carCommands.LOCK):
        return "lock.sh"
    elif(carCommand == carCommands.UNLOCK):
        return "unlock.sh"
    else:
        return ";"

def scheduleRelative(carCommand, timeRelative):
    print("Scheduling [%s] for [%s] from now" % (carCommand.value, timeRelative))
    output = subprocess.run(["at","-f", getCommandScript(carCommand), ("now + " + timeRelative)], cwd=os.path.dirname(os.path.realpath(__file__)), capture_output=True).stderr.decode("utf-8").lower()
    output = output[output.find("job "):]
    # Return "at" job ID
    print("Job ID: " + output[4:output.find(" ", 4)])
    return output[4:output.find(" ", 4)]

def scheduleAbsolute(carCommand, timeAbsolute):
    print("Scheduling [%s] at [%s]" % (carCommand.value, timeAbsolute))
    output = subprocess.run(["at","-f", getCommandScript(carCommand), timeAbsolute], cwd=os.path.dirname(os.path.realpath(__file__)), capture_output=True).stderr.decode("utf-8").lower()
    output = output[output.find("job "):]
    # Return "at" job ID
    print("Job ID: " + output[4:output.find(" ", 4)])
    return output[4:output.find(" ", 4)]

