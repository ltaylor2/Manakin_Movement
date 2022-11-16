# ----------------------------------
#
#	Manakin camera motion analysis
#	Working scripts 2022-11-09
#   L. U. Taylor 
# 	FVS CLASS FOR MULTI-THREADING VIDEO READ-IN
#
# ----------------------------------

from threading import Thread
import queue
import time
import sys
import cv2

class FileVideoStream:
	def __init__(self, filePath):
		self.stream = cv2.VideoCapture(filePath)

		self.width = int(self.stream.get(3))
		self.height = int(self.stream.get(4))

		self.stopped = False
		self.locked = False
		self.Q = queue.Queue()

	def start(self):
		t = Thread(target=self.update, args=())
		t.daemon = True
		t.start()
		return self

	def update(self):
			while True:
				if self.locked or self.Q.qsize() > 1000:
					continue

				if self.stopped:
					return

				(grabbed, frame) = self.stream.read()
				if not grabbed:
					self.stop()
					return

				self.Q.put(frame)

	def read(self):
		return self.Q.get()

	def more(self):
		return self.Q.qsize() > 0

	def stop(self):
		self.stopped = True

	def isDone(self):
		return self.stopped and not self.more()

	def getWidth(self):
		return self.width

	def getHeight(self):
		return self.height

	def taskDone(self):
		self.Q.task_done()

	def getSize(self):
		return self.Q.qsize()