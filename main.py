#!/usr/bin/env python
# coding: Latin-1

from __future__ import division
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
import numpy as np
import math

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

def transform_to_topdown_coordinates(img, pixels_per_centimer):
    src = np.float32([[113-20, 36], [242-20, 40], [11-20, 120], [334-20, 122]])

    output_w = int(100 * pixels_per_centimer)
    output_h = int(100 * pixels_per_centimer)
    paper_width = 21
    paper_height = 29.7
    paper_distance = 15

    left_x = output_w / 2 - paper_width / 2 * pixels_per_centimer
    right_x = output_w / 2 + paper_width / 2 * pixels_per_centimer
    bottom_y = paper_distance * pixels_per_centimer
    top_y = (paper_distance + paper_height) * pixels_per_centimer

    dst = np.float32([[left_x, top_y], [right_x, top_y], [left_x, bottom_y], [right_x, bottom_y]])
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(img, M, (output_w, output_h), flags=cv2.INTER_LINEAR)

def orange_line_mask(hsvimg):
    avg_saturation = np.mean(hsvimg[:,:,1])
    lower_range1 = np.array([0,         3*avg_saturation, 35/100*255])
    upper_range1 = np.array([50/360*180,       255, 80/100*255])
    lower_range2 = np.array([340/360*180, 3*avg_saturation, 35/100*255])
    upper_range2 = np.array([180,               255, 80/100*255])
    color_mask1 = cv2.inRange(hsvimg, lower_range1, upper_range1)
    color_mask2 = cv2.inRange(hsvimg, lower_range2, upper_range2)
    return (color_mask1 > 0) | (color_mask2 > 0)

def white_line_mask(hsvimg):
    lower_range = np.array([0,   0,          60/100*255])
    upper_range = np.array([255, 10/100*255, 255])
    color_mask = cv2.inRange(hsvimg, lower_range, upper_range)
    return color_mask > 0

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
    def ProcessImage(self, img):
        # Flip the image if needed
        img = cv2.flip(img, -1)

        # if time.time() - self.last_photo_taken > 5:
        #     self.last_photo_taken = time.time()
        pixels_per_centimeter = 2.0

        # process image and get required imageData 
        # replace next line with required code
        # img = cv2.flip(img, 1)
        topdown = transform_to_topdown_coordinates(img, pixels_per_centimeter)
        # topdown = img

        kernel_size = 3
        blur = cv2.GaussianBlur(topdown, (kernel_size, kernel_size), 2)

        hsvblur = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
        avg_saturation = np.mean(hsvblur[:,:,1])
        orange_line = orange_line_mask(hsvblur)
        # orange_line = np.zeros( (200, 200) , dtype = bool)
        # orange_line[:][:10] = True
        if not orange_line.any():
            print 'No Orange detected!'

        blur[orange_line] = (255, 0, 255)
        filename = "photos/" + str(time.time()) + ".png"
        cv2.imwrite(filename, blur)

        self.move(orange_line, blur)


    # Set the motor speed from the motion detection
    def move(self, orange_line, blur):
        global ZB

        if not orange_line.any():
            print 'No Orange! Just left'
            driveLeft = .75
            driveRight = 1.0
        else:
            # get average orange point
            summ = np.array([0,0]);
            count = 0.0
            for i in range(len(orange_line)):
                for j in range(len(orange_line[i])):
                    if orange_line[i,j]==True:
                        summ[0]+=i
                        summ[1]+=j
                        count += 1.0
            summ = (summ / count)
            # reference point
            point = np.array([summ[0], summ[1]-len(blur)/2.0])
            angle = math.atan2(point[0],point[1]) #angle in radians 
            print 'Angle ', angle
            # Set the motors with the required params based on imageData
            beta = abs(math.pi / 2 - angle) / (math.pi / 2)
            if angle <= math.pi / 2:
                print 'Beta ', beta, ' to the right'
                driveRight = 1 - beta
                driveLeft = 1.0
            else:
                print 'Beta ', beta, ' to the left'
                driveLeft = 1 - beta
                driveRight = 1.0

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
