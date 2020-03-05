import cv2
import numpy as np

#image = cv2.imread("photos/1582815603.45.png", cv2.IMREAD_COLOR) # Go right
image = cv2.imread("photos/1582815528.19.png", cv2.IMREAD_COLOR) # Go left
#image = cv2.imread("photos/1582815538.22.png", cv2.IMREAD_COLOR) # Go right
#image = cv2.imread("photos/1582815588.41.png", cv2.IMREAD_COLOR) # Go right

# Colors margins
x = 55
y = 20
color_orange = np.array([66,88,185])
color_white = np.array([200,200,200])

boundaries = [(color_orange - x, color_orange + x)]#,(color_white - y, color_white + y)]

for (lower, upper) in boundaries:
	lower = np.array(lower, dtype = "uint8")
	upper = np.array(upper, dtype = "uint8")
	
	# find the colors within the specified boundaries and apply the mask
	mask = cv2.inRange(image, lower, upper)
	output = cv2.bitwise_and(image, image, mask = mask)
	
	height, width = mask.shape[:2]
	
	l_mask = mask[0:height, 0:(width/2)]
	r_mask = mask[0:height, (width/2):width]
	
	l_pixels = cv2.countNonZero(l_mask)
	r_pixels = cv2.countNonZero(r_mask)
	
	if l_pixels < r_pixels:
		print "Go right"
	else:
		print "Go left"
	
	
	def get_point(mask,treshold,window_size):
		mask = mask/255
		for i,row in enumerate(mask):
			for j in range(len(row)-window_size):
				winsum = sum(row[j:(j+window_size)])
				if winsum >= treshold:
					return i,j+window_size/2
	
	
	print get_point(mask,4,4)
	
	# show the images
	#cv2.imshow("images", l_mask)
	#cv2.waitKey(0)
	#cv2.imshow("images", r_mask)
	#cv2.waitKey(0)
	#cv2.imshow("images", output)
	#cv2.waitKey(0)
