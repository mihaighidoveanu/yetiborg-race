import picamera
import picamera.array
import threading
import time
import cv2

image_width  = 320                       # Camera image width
image_height = 240                       # Camera image height
frame_rate = 30                          # Camera image capture frame rate
flipped_image = True

running = True

camera = picamera.PiCamera()
camera.resolution = (image_width, image_height)
camera.framerate = frame_rate



class StreamProcessor(threading.Thread):
    def __init__(self):
        super(StreamProcessor, self).__init__()
        self.stream = picamera.array.PiRGBArray(camera)
        self.event = threading.Event()
        self.terminated = False
        self.last_photo_taken = 0
        self.start()

    def run(self):
        # This method runs in a separate thread
        while not self.terminated:
            # Wait for an image to be written to the stream
            if self.event.wait(1):
                try:
                    # Read the image and do some processing on it
                    self.stream.seek(0)
                    self.process_image(self.stream.array)
                except KeyboardInterrupt:
	            #self.terminated = True
			raise
                finally:
                    # Reset the stream and event
                    self.stream.seek(0)
                    self.stream.truncate()
                    self.event.clear()

    # Image processing function
    def process_image(self, image):
        if flipped_image:
            image = cv2.flip(image, -1)

        if time.time() - self.last_photo_taken > 5:
            self.last_photo_taken = time.time()
            filename = "photos/" + str(time.time()) + ".png"
            cv2.imwrite(filename, image)


class ImageCapture(threading.Thread):
    def __init__(self):
        super(ImageCapture, self).__init__()
        self.start()

    def run(self):
        camera.capture_sequence(self.trigger_stream(), format='bgr', use_video_port=True)
        processor.terminated = True
        processor.join()

    def trigger_stream(self):
        global running
        while running:
            if processor.event.is_set():
                time.sleep(0.001)
            else:
                yield processor.stream
                processor.event.set()

processor = StreamProcessor()
capture_thread = ImageCapture()
capture_thread.join()
processor.terminated = True
processor.join()
