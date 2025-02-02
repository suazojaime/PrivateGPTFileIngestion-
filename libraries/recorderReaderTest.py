#!/usr/bin/python3
# *********************************************************************************************************
#
# Copyright 2020 Caterpillar Inc.
#
# A test driver for AssignmentRecorderReader.py
#
# *********************************************************************************************************

import sys
import getopt
import json
import pprint
from datetime import datetime
from AssignmentRecorderReader import AssignmentRecorderReader
from AssignmentRecorderReader import assignmentTriggers

def testPrint(*args):
    """ Single print method to control output channel in one place """
    print(*args, file = sys.stdout)

def printAssignmentEventsByOID(recorderReader):
    """Print assignemnt events as mapped by truck OID
    Args:
      an AssignmentRecorderReader instance
    """
    assignmentEventsByOID = recorderReader.getAssignmentEventsWithForecastChecksByTruckOID()
    rcmEntitiesByOID = recorderReader.getCumulativeRCM().getEntitiesByOID()
    for oid in assignmentEventsByOID.keys():
        truckRCMEntity = rcmEntitiesByOID[oid]
        testPrint("assignment events for truck " + oid + " / " + truckRCMEntity.getName() + ":")
        for assignmentEvent in assignmentEventsByOID[oid]:
            testPrint("\ttime of forecast assignment: " + str(assignmentEvent.getTime()))
            for assignment in assignmentEvent.getAssignments():
                destinationOID = assignment["rcmDestinationQueueMachineOID"]
                destinationRCMEntity = rcmEntitiesByOID[destinationOID]
                occurred = ''
                if 'occurred' in assignment:
                    if assignment['occurred']:
                        occurred = ' occurred'
                    else:
                        occurred = " didn't occur"
                testPrint(
                    "\t\tassignment: to machine: " + destinationOID + " / " + destinationRCMEntity.getName() +
                    " leaving at: " + assignment['leavingTime'] + occurred
                )

def printRCMEntitiesByOID(rcmEntitiesByOID):
    """Print all RCM entities as mapped by entity OID
    Args:
      rcmEntitiesByOID: a map of OIDs to RCM entities
    """
    for oid in rcmEntitiesByOID:
        entity = rcmEntitiesByOID[oid]
        testPrint("RCM entity: oid: " + oid + " name: " + entity.getName())

# Global travel time records:
# format is (predicted travel time, predicted seconds, actual travel time, actual seconds, delta seconds, delta/predicted ratio):
travelTimeRecords = []

def addTravelTimeRecord(timeToArrival, assignment):
    """Add a record to the global travelTimeRecords - internal use only
    Args:
      timeToArrival: a datetime delta
      assignment: a JSON single assignment element (the first of four) from an AssignmentEvent
    """
    if (not timeToArrival):
        return
    serviceTimeDateFormat = "%Y-%m-%d %H:%M:%S.%f"
    beginServiceTime = datetime.strptime(assignment['beginServiceTime'], serviceTimeDateFormat)
    endServiceTime = datetime.strptime(assignment['endServiceTime'], serviceTimeDateFormat)
    testPrint("\t\tbegin service: " + str(beginServiceTime) + " end service: " + str(endServiceTime))
    serviceTime = endServiceTime - beginServiceTime
    travelTimeRecord = [
        serviceTime, serviceTime.total_seconds(), timeToArrival, timeToArrival.total_seconds(),
        timeToArrival.total_seconds() - serviceTime.total_seconds(), 
        (timeToArrival.total_seconds() - serviceTime.total_seconds())/serviceTime.total_seconds()
    ]
    travelTimeRecords.append(travelTimeRecord)

def printTravelTimeRecordsAsCSV():
    """Write the travel time records in travelTimeRecords to the file travelTimes.csv
    """
    originalStdout = sys.stdout
    with open('travelTimes.csv', 'w') as output:
        sys.stdout = output
        testPrint("Predicted Travel Time,Predicted Seconds,Actual Travel Time,Actual Seconds,Delta Seconds,Delta To Predicted Ratio")
        for travelTimeRecord in travelTimeRecords:
            testPrint(
                str(travelTimeRecord[0]) + ',' + str(travelTimeRecord[1]) + ',' + str(travelTimeRecord[2]) + ',' +
                str(travelTimeRecord[3]) + ',' + str(travelTimeRecord[4]) + ',' + str(travelTimeRecord[5])
            )
    sys.stdout = originalStdout

def main():
    """Test driver main

    This reads in a JSON conversion of an assignment recorder sqlite database using an instance of AssignmentRecorderReader
    and then prints out a summary of triggers and assignments for each truck (ordered by truck, then by time).  It then
    prints a list of assignment events for each truck, with the added field denoting whether a given assignment occurred.
    Note that each assignment contains a base assignment (with no occurrence flag, since it has occurred as it was given) and
    three future predicted assignments (each with a potential occurence flag, since they can be compared to subsequent base
    assignments).
    """
    verbose = 0
    outputPath = ''
    options, remainder = getopt.getopt(sys.argv[1:], 'o:e:v', ['output=', 'events=', 'verbose'])
    testPrint('OPTIONS: ', options)
    for option in options:
        if (option[0] == "--output") or (option[0] == "-o"):
            outputPath = option[1].strip()
        elif (option[0] == "--verbose") or (option[0] == "-v"):
            verbose = 1
        elif (option[0] == "--events") or (option[0] == "-e"):
            events = option[1].split(",")
    if verbose:
        testPrint("outputPath is \"" + outputPath + "\"")
        testPrint("events is  \"" + str(events) + "\"")
    if len(remainder) < 1:
        raise Error("Need a single argument - the path to the sqlite recorder database")
    recorderReader = AssignmentRecorderReader(remainder[0])
    testPrint("Event types and counts:\n")
    for eventType in recorderReader.getEventTypes():
        testPrint("\t" + eventType + ": " + str(recorderReader.getEventCountByType(eventType)) + "\n")
    rcmEntitiesByOID = recorderReader.getRCMEntitiesByOID()
    triggersAndAssignmentsByTruckOID = recorderReader.getAssignmentEventsByTruckOID()
    for oid in triggersAndAssignmentsByTruckOID:
        triggersAndAssignments = triggersAndAssignmentsByTruckOID[oid]
        print('Triggers and assignments for truck ' + rcmEntitiesByOID[oid].getName() + ':')
        for triggerOrAssignment in triggersAndAssignments:
            time = triggerOrAssignment['time']
            if triggerOrAssignment['type'] == 'trigger':
                trigger = triggerOrAssignment['trigger']
                timeToAssignment = ''
                if 'timeToAssignment' in triggerOrAssignment:
                    timeToAssignment = ' time to assignment: ' + str(triggerOrAssignment['timeToAssignment'])
                print(
                    "\t time: " + str(time) + " trigger: " + trigger + " (" + assignmentTriggers[int(trigger)] + ")" +
                    timeToAssignment
                )
            elif triggerOrAssignment['type'] == 'assignment':
                timeFromTrigger = ''
                if 'timeFromTrigger' in triggerOrAssignment:
                    timeFromTrigger = ' - time from trigger: ' + str(triggerOrAssignment['timeFromTrigger'])
                if 'timeToArrival' in triggerOrAssignment:
                    # Record some stats about the arrival time vs the predicted arrival time; we don't care about the source and
                    # destination locations, just the times:
                    if (triggerOrAssignment['timeToArrival'].total_seconds() > 0):
                        addTravelTimeRecord(triggerOrAssignment['timeToArrival'], triggerOrAssignment['assignments'][0])
                        testPrint("Added travel time record with travel time of " + str(triggerOrAssignment['timeToArrival']))
                print(
                    "\t time: " + str(time) + " assignment" + timeFromTrigger
                )
            elif triggerOrAssignment['type'] == 'arrival':
                timeFromAssignment = ''
                if 'timeFromAssignment' in triggerOrAssignment:
                    timeFromAssignment = ' - time from assignment: ' + str(triggerOrAssignment['timeFromAssignment'])
                print(
                    "\t time: " + str(time) + " arrival" + timeFromAssignment
                )
    printAssignmentEventsByOID(recorderReader)
    printTravelTimeRecordsAsCSV()
    print
    
if __name__ == "__main__":
    main()
