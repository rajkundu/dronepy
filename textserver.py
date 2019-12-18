#!/usr/bin/python3

import os
import sys
import subprocess
import time
import keyring
import requests
import json

from flask import Flask, request, redirect
from twilio.twiml.messaging_response import MessagingResponse

from carCommands import carCommands, carCommandToText
from schedulecmd import scheduleRelative, scheduleAbsolute

def argError(s):
	print(s)
	exit()
def validateIP(s):
	ipParts = s.split(":")
	ipSubparts = ipParts[0].split(".")
	if(len(ipParts) != 2 or len(ipSubparts) != 4):
		argError("\033[91mHOST IP & LISTENING PORT SPECIFIED IMPROPERLY\033[00m - usage: \"[Host IPV4 Address]:[1 <= listeningPort <= 65535]\"")
	try:
		for partString in ipSubparts:
			part = int(partString)
			if(part < 0 or part > 255):
				raise ValueError()
		hostIP = ipParts[0]
	except ValueError:
		argError("\033[91mHOST IP SPECIFIED IMPROPERLY\033[00m - usage: \"[Host IPV4 Address]:[1 <= listeningPort <= 65535]\"")
	try:
		listeningPort = int(ipParts[1])
		if(listeningPort < 1 or listeningPort > 65535):
			raise ValueError()
	except ValueError:
		argError("\033[91mLISTENING PORT SPECIFIED IMPROPERLY\033[00m - usage: \"[Host IPV4 Address]:[1 <= listeningPort <= 65535]\"")

	return [hostIP, listeningPort]

if(len(sys.argv) < 2):
	argError("\033[91mHOST IP & LISTENING PORT SPECIFIED IMPROPERLY\033[00m - usage: \"[Host IPV4 Address]:[1 <= listeningPort <= 65535]\"")
hostIP = ""
listeningPort = -1
hostIP, listeningPort = validateIP(sys.argv[1])

# ============ READ AUTH DATA ============ #

dirname, filename = os.path.split(os.path.abspath(sys.argv[0]))
with open(os.path.join(dirname, "auth.json")) as auth_json:
	auth_data = json.load(auth_json)
	username = auth_data["username"]
	password = auth_data["password"]
	deviceID = auth_data["deviceID"]

# ============= GET API KEY ============== #

def getAPIKey():
	url = 'https://cognito-idp.us-east-1.amazonaws.com/'
	headers = {
		"Content-Type": "application/x-amz-json-1.1",
		"X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
		"X-Amz-User-Agent": "aws-amplify/0.1.x js",
		"Content-Length": "176"
	}
	body = {
		"AuthFlow": "USER_PASSWORD_AUTH",
		"ClientId": "3l3gtebtua7qft45b4splbeuiu",
		"AuthParameters": {
			"USERNAME": username,
			"PASSWORD": password
		},
		"ClientMetadata":{}
	}

	# Send request, print response
	response = requests.post(url, data=json.dumps(body), headers=headers)
	return response.json()["AuthenticationResult"]["IdToken"]

# ============= CAR CONTROL ============== #

timeInterval = -1
carAction = -1

# NOTE: carAction parameter must be member of enum carCommands
def executeCarAction(carAction):
	carActionText = carCommandToText(carAction)
	print("Selected command: " + "\033[91m" + carActionText + "\033[00m")

	url = 'https://accounts.dronemobile.com/api/iot/send-command'
	headers = {
		"x-drone-api": getAPIKey(),
		"Content-Type": "application/json;charset=utf-8",
		"Content-Length": "48",
	}
	body = {
		"deviceKey": deviceID,
		"command": carAction.value
	}

	# Send request, print response
	response = requests.post(url, data=json.dumps(body), headers=headers)
	data = response.json()
	if("detail" in data):
		data = data["detail"]
		print("\033[91mFailure\033[00m")
	else:
		data = data["parsed"]
		if(data["command_success"]):
			print("\033[92mSuccess\033[00m")
		else:
			print("\033[91mFailure\033[00m")

	print(json.dumps(data, indent=4))
	'''
	#While identifier is the same, print that application is sending request
	sys.stdout.write("\033[93mWaiting for confirmation.   ")
	print("\r\033[00m" + carActionText + " confirmation received ")
	'''

def parseCarAction(carCommandString):
	carCommandString = carCommandString.lower()
	if(carCommandString.find("st") > -1):
		return carCommands.STARTSTOP
	elif(carCommandString.find("un") > -1):
		return carCommands.UNLOCK
	elif(carCommandString.find("lo") > -1):
		return carCommands.LOCK
	else:
		print("\033[91mERROR SETTING ACTION\033[00m")
		exit()

def getJobList():
	output = subprocess.run(["atq"], capture_output=True).stdout.decode("utf-8")
	return (("Job Schedule:\n" + output) if output else "No jobs are currently scheduled.")

app = Flask(__name__)
@app.route("/sms", methods=['GET', 'POST'])
def incoming_sms():

	# Get the SMS message sent to the Twilio number
	commandString = request.values.get('Body', None).lower()
	commandStringTokens = commandString.split()
	carCommandString = commandStringTokens[0]

	if(carCommandString == "atrm" or carCommandString == "rm" or carCommandString == "remove"):
		jobID = commandStringTokens[1]
		if(not jobID.isdigit()):
			# Reply via text message
			smsReply = MessagingResponse()
			smsReply.message("Invalid job ID \"" + jobID + "\"")
			return str(smsReply)
		p = subprocess.run(["atrm", str(jobID)])
		if(p.returncode != 0):
			# Reply via text message
			smsReply = MessagingResponse()
			smsReply.message("Job ID " + jobID + " does not exist. " + getJobList())
			return str(smsReply)
		# Reply via text message
		replyMsg = "Job " +  jobID + " removed. " + getJobList()
		print(replyMsg)
		smsReply = MessagingResponse()
		smsReply.message(replyMsg)
		return str(smsReply)
	elif(carCommandString == "atq" or carCommandString == "ls" or carCommandString == "list"):
		jobList = getJobList()
		print(jobList)
		# Reply via text message
		smsReply = MessagingResponse()
		smsReply.message(jobList)
		return str(smsReply)

	# Parse action from text message
	carAction = parseCarAction(carCommandString)

	# Parse timing from text message
	# If message contains "in" and "in" is not the last word
	if(("in" in commandStringTokens) and (commandStringTokens.index("in") < len(commandStringTokens) - 1)):
		wordToNum = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9}
		timeRelativeTokens = commandString.split(" in ")[1].split()
		if(timeRelativeTokens[0] in wordToNum):
			timeRelativeTokens[0] = str(wordToNum[timeRelativeTokens[0]])
		# Rebuild command string
		timeRelative = timeRelativeTokens[0]
		for i in range(1, len(timeRelativeTokens)):
			timeRelative += " " + timeRelativeTokens[i]
		# Default to minutes for unspecified units
		if(len(timeRelativeTokens) == 1):
			timeRelative += " minutes"
		jobID = scheduleRelative(carAction, timeRelative)
		sendingTime = " in [" + timeRelative + "] (Job #" + jobID + ")"
	# If message contains "at" and "at" is not the last word
	elif(("at" in commandStringTokens) and (commandStringTokens.index("at") < len(commandStringTokens) - 1)):
		timeAbsoluteTokens = commandString.split(" at ")[1].split()
		# Add leading zero if necessary
		timeAbsoluteHour = timeAbsoluteTokens[0].split(":")[0]
		timeAbsoluteMinute = timeAbsoluteTokens[0].split(":")[1]
		if(len(timeAbsoluteMinute) < 2):
			timeAbsolute = "0" + timeAbsoluteHour + ":" + timeAbsoluteMinute
		else:
			timeAbsolute = timeAbsoluteHour + ":" + timeAbsoluteMinute
		# Append whatever is after the time, e.g. am/pm, today/tomorrow
		for i in range(1, len(timeAbsoluteTokens)):
			timeAbsolute += " " + timeAbsoluteTokens[i]
		jobID = scheduleAbsolute(carAction, timeAbsolute)
		sendingTime = " at [" + timeAbsolute + "] (Job #" + jobID + ")"
	# If message contains neither "in" nor "at"
	else:
		# Execute now
		executeCarAction(carAction)
		sendingTime = ""

	# Reply via text message
	smsReply = MessagingResponse()
	smsReply.message("Sending command [%s]%s" % (carCommandToText(carAction), sendingTime))
	return str(smsReply)

if __name__ == "__main__":
	app.run(host = hostIP, port = listeningPort)
