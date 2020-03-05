#!/usr/bin/env python
# coding: Latin-1

# Load library functions we want
import time
import os
import sys
import ZeroBorg
import io
import threading
import picamera
import picamera.array
import cv2
import numpy

# Re-direct our output to standard error, we need to ignore standard out to hide some nasty print statements from pygame
sys.stdout = sys.stderr
print 'Libraries loaded'

# Global values
global running
global ZB
global camera
global processor
running = True

# Setup the ZeroBorg
ZB = ZeroBorg.ZeroBorg()
#ZB.i2cAddress = 0x44                  # Uncomment and change the value if you have changed the board address
ZB.Init()
if not ZB.foundChip:
    boards = ZeroBorg.ScanForZeroBorg()
    if len(boards) == 0:
        print 'No ZeroBorg found, check you are attached :)'
    else:
        print 'No ZeroBorg at address %02X, but we did find boards:' % (ZB.i2cAddress)
        for board in boards:
            print '    %02X (%d)' % (board, board)
        print 'If you need to change the I²C address change the setup line so it is correct, e.g.'
        print 'ZB.i2cAddress = 0x%02X' % (boards[0])
    sys.exit()
#ZB.SetEpoIgnore(True)                 # Uncomment to disable EPO latch, needed if you do not have a switch / jumper
# Ensure the communications failsafe has been enabled!
failsafe = False
for i in range(5):
    ZB.SetCommsFailsafe(True)
    failsafe = ZB.GetCommsFailsafe()
    if failsafe:
        break
if not failsafe:
    print 'Board %02X failed to report in failsafe mode!' % (ZB.i2cAddress)
    sys.exit()
ZB.ResetEpo()

# Power settings
voltageIn = 8.4                         # Total battery voltage to the ZeroBorg (change to 9V if using a non-rechargeable battery)
voltageOut = 6.0                        # Maximum motor voltage

# Camera settings
imageWidth  = 320                       # Camera image width
imageHeight = 240                       # Camera image height
frameRate = 10                          # Camera image capture frame rate

# Auto drive settings
steeringGain = 4.0                      # Use to increase or decrease the amount of steering used
flippedImage = True                     # True if the camera needs to be rotated
showDebug = True                        # True to display detection values

# Setup the power limits
if voltageOut > voltageIn:
    maxPower = 1.0
else:
    maxPower = voltageOut / float(voltageIn)

# Image stream processing thread
class StreamProcessor(threading.Thread):
    def __init__(self):
        super(StreamProcessor, self).__init__()
        self.stream = picamera.array.PiRGBArray(camera)
        self.event = threading.Event()
        self.terminated = False
        self.reportTick = 0
        self.start()
        self.begin = 0
        self.last_photo_taken = 0

    def run(self):
        # This method runs in a separate thread
        while not self.terminated:
            # Wait for an image to be written to the stream
            if self.event.wait(1):
                try:
                    # Read the image and do some processing on it
                    self.stream.seek(0)
                    self.ProcessImage(self.stream.array)
                finally:
                    # Reset the stream and event
                    self.stream.seek(0)
                    self.stream.truncate()
                    self.event.clear()

    # Image processing function
    def ProcessImage(self, image):
        # Flip the image if needed
        if flippedImage:
            image = cv2.flip(image, -1)

        # if time.time() - self.last_photo_taken > 5:
        #     self.last_photo_taken = time.time()
        filename = "photos/" + str(time.time()) + ".png"
        cv2.imwrite(filename, image)

        # process image and get required imageData 
        #TODO 
        # replace next line with required code
        imageData = image

        self.move(imageData)

    # Set the motor speed from the motion detection
    def move(self, imageData):
        global ZB
        # TODO
        # Set the motors with the required params based on imageData
        driveRight = 1.0
        driveLeft = 1.0
        ZB.SetMotor1(-driveRight * maxPower) # Rear right
        ZB.SetMotor2(-driveRight * maxPower) # Front right
        ZB.SetMotor3(-driveLeft  * maxPower) # Front left
        ZB.SetMotor4(-driveLeft  * maxPower) # Rear left

# Image capture thread
class ImageCapture(threading.Thread):
    def __init__(self):
        super(ImageCapture, self).__init__()
        self.start()

    def run(self):
        global camera
        global processor
        print 'Start the stream using the video port'
        camera.capture_sequence(self.TriggerStream(), format='bgr', use_video_port=True)
        print 'Terminating camera processing...'
        processor.terminated = True
        processor.join()
        print 'Processing terminated.'

    # Stream delegation loop
    def TriggerStream(self):
        global running
        while running:
            if processor.event.is_set():
                time.sleep(0.01)
            else:
                yield processor.stream
                processor.event.set()

# Startup sequence
print 'Setup camera'
camera = picamera.PiCamera()
camera.resolution = (imageWidth, imageHeight)
camera.framerate = frameRate
imageCentreX = imageWidth / 2.0
imageCentreY = imageHeight / 2.0

print 'Setup the stream processing thread'
processor = StreamProcessor()

print 'Wait ...'
time.sleep(2)
captureThread = ImageCapture()

try:
    print 'Press CTRL+C to quit'
    ZB.MotorsOff()
    # Loop indefinitely
    while running:
        # # Change the LED to show if we have detected motion
        # We do this regularly to keep the communications failsafe test happy
        # ZB.SetLed(motionDetected)
        # Wait for the interval period
        time.sleep(0.1)
    # Disable all drives
    ZB.MotorsOff()
except KeyboardInterrupt:
    # CTRL+C exit, disable all drives
    print '\nUser shutdown'
    ZB.MotorsOff()
except:
    # Unexpected error, shut down!
    e = sys.exc_info()[0]
    print
    print e
    print '\nUnexpected error, shutting down!'
    ZB.MotorsOff()
# Tell each thread to stop, and wait for them to end
running = False
captureThread.join()
processor.terminated = True
processor.join()
del camera
ZB.SetLed(False)
print 'Program terminated.'
