# ----------------------------------
#
#	Manakin camera motion analysis
#	Working scripts 2022-11-09
#   L. U. Taylor 
#	MAIN PROGRAM FILE
#
# ----------------------------------

from FileVideoStream import FileVideoStream
import cv2
import time
import math
import argparse
import os
import sys
import gc

#
# VISION PARAMETERS
#
FPS_VAL = 30.0				# must match camera, must be hard-coded

END_BUFFER_CAP = 2 * FPS_VAL

RESIZE_FACTOR = 0.25 		# smaller videos are faster but may lose small motion

GAUSSIAN_BOX = 31			# blurring factor (larger is blurrier, must be odd)

DIFF_THRESHOLD = 30
SUM_THRESHOLD = 80000		# how many motion pixels for a reading? (*255)

CLIP_STORAGE_FILENAME = "tmp_clip_storage"
METADATA_STORAGE_FILENAME = "motiondetection_metadata.csv"

ACCEPTABLE_FILETYPES = [".mp4", ".MP4", ".avi", ".AVI"]

def convertFrame(orgFrame):
	resize = cv2.resize(orgFrame, (0, 0), fx=RESIZE_FACTOR, fy=RESIZE_FACTOR)
	frame = cv2.cvtColor(resize, cv2.COLOR_BGR2GRAY)
	frame = cv2.GaussianBlur(frame, (GAUSSIAN_BOX, GAUSSIAN_BOX), 0)
	return frame

def getFrameDiffs(frame, prev_frame, prev_prev_frame):
	d1 = cv2.absdiff(frame, prev_frame)
	d2 = cv2.absdiff(prev_frame, prev_prev_frame)
	diffFrame = cv2.bitwise_xor(d1, d2)
	return diffFrame

def getThreshold(frameDiff):
	thresh = cv2.threshold(frameDiff, DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)[1]
	return thresh

def getPixelSum(frame):
	return cv2.sumElems(frame)

def hmsString(secValue):
	secs = secValue
	hrs = math.floor(secs / 3600)
	secs = secs - (3600 * hrs)

	mins = math.floor(secs / 60)
	secs = secs - (60 * mins)

	s = str(int(hrs)) + ":" + str(int(mins)) + ":" + str(round(secs,2))
	return s

def getAllFiles(headPath):
	fullPathList = os.listdir(headPath)
	files = []
	for potentialFile in fullPathList:
		fileName = headPath + potentialFile
		if (os.path.isfile(fileName) and 
			potentialFile[-4:] in ACCEPTABLE_FILETYPES):
			files.append(fileName)

		elif os.path.isdir(fileName+"/"):
			recursiveFiles = getAllFiles(fileName+"/")
			for file in recursiveFiles:
				files.append(file)
	return files

def readClipFromStorage(clipLength, fvs):
	clip = []
	for frameIndex in range(0, clipLength):
		grabbed, frame = fvs.read()
		if not grabbed:
			print("UH OH! Weird error, clip lengths don't align with clip.")
			return

		clip.append(frame)
	return clip

def writeClipToStorage(clip, clipStorage, clipStorageLengths):
	for frame in clip:
		clipStorage.write(frame)

	clipStorageLengths.append(len(clip))
	clip = []

	return clip, clipStorageLengths

def analyzeVideo(inFile, storageName, numCurrFile, numTotalFiles):
	t0 = time.time()

	motionPeriod = False

	prev_frame = None
	prev_prev_frame = None

	frameCount = 0
	startBuffer = 0
	endBuffer = 0

	motionTimes = []
	endTimes = []

	clipStartTimes = []

	clipCounter = 0
	clip = []
	clipStorageLengths = []

	written = False

	fvs = FileVideoStream(inFile).start()

	clipStorage = cv2.VideoWriter(storageName, cv2.VideoWriter_fourcc(*"XVID"), int(FPS_VAL),
							   	  (fvs.getWidth(), fvs.getHeight()))

	while not fvs.isDone():

		if not fvs.more():
			continue

		orgFrame = fvs.read()

		frameCount += 1
		
		frame = convertFrame(orgFrame)

		if frameCount == 1:
			prev_prev_frame = frame
			continue
		elif frameCount == 2:
			prev_frame = frame
			continue		

		frameDiff = getFrameDiffs(frame, prev_frame, prev_prev_frame)
		thresh = getThreshold(frameDiff)
		pixelSum = getPixelSum(thresh)

		if watch:
			cv2.imshow("Threshold Image", thresh)
			if cv2.waitKey(1) & 0xFF == ord('q'):
				break

		if pixelSum[0] > SUM_THRESHOLD:
			if not motionPeriod:
				startTimeString = hmsString(frameCount / FPS_VAL)
				clipStartTimes.append(startTimeString)

			endBuffer = 0
			motionPeriod = True

		elif motionPeriod:
			endBuffer += 1

		if motionPeriod and (len(clip) < 2 * FPS_VAL):
			clip.append(orgFrame)

		if endBuffer >= END_BUFFER_CAP:
			endBuffer = 0
			motionPeriod = False
			clip, clipStorageLengths = writeClipToStorage(clip, clipStorage, clipStorageLengths)

		# progress update
		if frameCount % 100 == 0:
			print("Working on frame " + str(frameCount) + " in file " + inFile +
				   " (" + str(numCurrFile) + " of " + str(numTotalFiles) + ")")
			print("  " + str(len(clipStartTimes)) + " clips so far.")

		prev_prev_frame = prev_frame
		prev_frame = frame

	# append the final clip if the video ends during motion
	if motionPeriod:
		clip, clipStorageLengths = writeClipToStorage(clip, clipStorage, clipStorageLengths)
		print("  " + str(len(clipStartTimes)) + " clips so far.")

	if watch:
		cv2.destroyAllWindows()

	if frameCount == 0:
		print("Error reading input! Not a video? Try again.")
		sys.exit()

	clipStorage.release()

	t1 = time.time()
	analysisTime = t1 - t0
	return clipStartTimes, clipStorageLengths, frameCount, analysisTime

def clipDisplay(inFile, storageName, clipStartTimes, clipStorageLengths):
	longestYesStreak = 0
	yesStreak = 0

	if len(clipStorageLengths) > 0:
		while True:
			isReady = input("Starting to display clips for file " + inFile +
								 " (" + str(len(clipStartTimes)) + " clips). Ready? [y]")
			if isReady == "y":
				print("Instructions: 'y' =  Retain // 'c' = Clear // anything else = replay")
				break

		clipCounter = 0
		numClipsDisplayed = 1

		# NOTE here we're going to single thread it, for now,
		# because imshow has its own thread as well, which bugs out
		fvs = cv2.VideoCapture(storageName)

		while clipCounter < len(clipStartTimes):
			print("Displaying clip " + str(numClipsDisplayed) + ".")
			print("Clip start time: " + str(clipStartTimes[clipCounter]))

			clipLength = clipStorageLengths[clipCounter]

			clip = readClipFromStorage(clipLength, fvs)

			while True:
				for frame in clip:
					resize = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
					cv2.imshow("preview", resize)
					if cv2.waitKey(30) & 0xFF == ord('q'):
						break

				clipResponse = ""
				if clipCounter == len(clipStartTimes):
					clipResponse = input("This is the last clip. Response? [y/c/...]")
				else:
					clipResponse = input("Response? [y/c/...]")

				if clipResponse == "y":
					clipCounter += 1
					numClipsDisplayed += 1
					yesStreak += 1
					if yesStreak > longestYesStreak:
						longestYesStreak = yesStreak
					break
				elif clipResponse == "c":
					removedTimeStr = clipStartTimes.pop(clipCounter)
					clipStorageLengths.pop(clipCounter)
					numClipsDisplayed += 1
					yesStreak = 0
					print("Removed clip at " + removedTimeStr)
					break
				else:
					print("Replaying clip " + str(numClipsDisplayed) + ".")

	else:
		print("No clips to display!")

	return clipStartTimes, longestYesStreak

def infoPrint(clipStartTimes, analysisTime, sortingTime, fileName, 
			  frameCount, hasOutput, outFile, numClips, numYes,
			  observerName, date, yesStreak):

	videoLength = round(frameCount / FPS_VAL, 2)

	messageString = "\n\n"
	messageString += "For video file " + os.path.split(fileName)[1] + "\n"
	messageString += "Video length was about " + str(videoLength) + " seconds\n"
	messageString += "Frame analysis done in " + str(round(analysisTime)) + " seconds.\n"
	messageString += "User sorting done in " + str(round(sortingTime)) + " seconds.\n"
	messageString += "------------------------\n"
	messageString += "   Final Movement Clip Times: " + "\n------------------------\n"

	if len(clipStartTimes) == 0:
		messageString += "NO MOTION DETECTED\n"
	else:
		for timeStr in clipStartTimes:
			messageString += "    " + timeStr + "\n"

	print(messageString)

	if hasOutput:
		f = open(outFile, "a")
		f.write(messageString)
		f.close()
		print("Wrote motion info to file " + outFile)

	# metadata
	f = open(METADATA_STORAGE_FILENAME, "a")
	f.write(os.path.split(fileName)[1] + ",")
	f.write(observerName + ",")
	f.write(date + ",")
	f.write(str(numClips) + ",")
	f.write(str(numYes) + ",")
	f.write(str(yesStreak) + ",")
	f.write(str(videoLength) + ",")

	noteStr = input("Want to add a note? (just skip if not. No commas!):\n")
	f.write(noteStr + "\n")

	f.close()
	print("Wrote metadata info to file " + METADATA_STORAGE_FILENAME)

#
# off to the races
#
outFile = ""
hasOutput = False

fileNames = []
allStorageNames = []
allClipStartTimes = []
allClipStorageLengths = []
allFrameCounts = []
allAnalysisTimes = []

#
# Read in arguments and helpful help messages
#
parser = argparse.ArgumentParser(description="GWMA Motion Detection")
parser.add_argument("inPath", type=str,
					help="file path for input video(s)")
parser.add_argument("-d", "--isDirectory", help="is the inPath a directory?",
					action="store_true")
parser.add_argument("-w", "--watch", help="watch threshold images",
					action="store_true")
parser.add_argument("-o", "--outFile", help="file to write final output message",
					type=str, default="none")

ARGS = parser.parse_args()

watch = ARGS.watch
isDirectory = ARGS.isDirectory

#
# First, simple I/O check
#
if ((isDirectory and os.path.isdir(ARGS.inPath)) or
    (not isDirectory and os.path.isfile(ARGS.inPath))):
	inPath = ARGS.inPath
else:
	print("\nInput file/directory does not exist. \n" +
		   "Did you forget to specify a directory [-d]? Exiting.\n")
	sys.exit()

if ARGS.outFile != "none" and os.path.isfile(ARGS.outFile):
	outFile = ARGS.outFile
	hasOutput = True
elif ARGS.outFile != "none" and not os.path.isfile(ARGS.outFile):
	print("Outfile did not exist. Creating it now")
	f = open(ARGS.outFile, "w")
	f.close()
	outFile = ARGS.outFile
	hasOutput = True
else:
	print("No outfile specified. Will not write results")

if not isDirectory:
	fileNames = [inPath]
else:
	fileNames = getAllFiles(inPath)
	print(fileNames)
	if len(fileNames) == 0:
		print("Directory contained no acceptable video files. Exiting")
		sys.exit()

numTotalFiles = len(fileNames)
numCurrFile = 0

print("\n\n Metadata. Will apply to all files")
observerName = input("Enter observer name/code:        ")
date = input("Enter video date [MM/DD/YY]:     ")

for inputFile in fileNames:
	numCurrFile += 1
	s = inputFile.replace(".","").replace("/", "")
	storageName = CLIP_STORAGE_FILENAME + "_" + s + ".avi"

	if os.path.isfile(storageName):
		print("\nThe storage file already existed (from a previous run?).")
		print("PLEASE NOTE: DELETING OLD VERSION of " + storageName + "\n")
		os.remove(storageName)

	allStorageNames.append(storageName)

	clipStartTimes, clipStorageLengths, frameCount, analysisTime = analyzeVideo(inputFile, storageName, numCurrFile, numTotalFiles)

	allClipStartTimes.append(clipStartTimes)
	allClipStorageLengths.append(clipStorageLengths)
	allFrameCounts.append(frameCount)
	allAnalysisTimes.append(analysisTime)

print("Done reading in all files! Beginning user sorting.")

for fileIndex in range(0, len(allStorageNames)):
	print(("\n\n-----------------\nStarting sorting on file " +
	       str(fileIndex + 1) + " of " + str(len(allStorageNames))))
	t0 = time.time()

	fileName = fileNames[fileIndex]
	storageName = allStorageNames[fileIndex]
	clipStartTimes = allClipStartTimes[fileIndex]
	clipStorageLengths = allClipStorageLengths[fileIndex]
	frameCount = allFrameCounts[fileIndex]
	analysisTime = allAnalysisTimes[fileIndex]

	numClips = len(clipStartTimes)
	clipStartTimes, yesStreak = clipDisplay(fileName, storageName, 
								 clipStartTimes, clipStorageLengths)
	numYes = len(clipStartTimes)

	t1 = time.time()
	sortingTime = t1 - t0
	print(outFile)
	infoPrint(clipStartTimes, analysisTime, sortingTime,
			  fileName, frameCount, hasOutput, outFile,
			  numClips, numYes, observerName, date, yesStreak)

	os.remove(storageName)

print("Done with all sorting. All storage files should be removed.")