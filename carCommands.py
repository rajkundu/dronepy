from enum import Enum

class carCommands(Enum):
    STARTSTOP = "remote_start"
    LOCK = "arm"
    UNLOCK = "disarm"

def carCommandToText(carCommand):
    if(carCommand == carCommands.STARTSTOP):
        return "Start/Stop"
    elif(carCommand == carCommands.LOCK):
        return "Lock"
    elif(carCommand == carCommands.UNLOCK):
        return "Unlock"
    else:
        print("\033[91mERROR CONVERTING ACTION TO TEXT\033[00m")
        exit()
