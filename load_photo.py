import cv2
import numpy as np
import matplotlib.pyplot as plt


def transform_to_topdown_coordinates(img, pixels_per_centimer):
    src = np.float32([[113-20, 36], [242-20, 40], [11-20, 120], [334-20, 122]])

    pixels_per_centimer = 2
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


img = cv2.imread("photos/1582815603.45.png", cv2.IMREAD_COLOR)
topdown = transform_to_topdown_coordinates(img, 2)

kernel_size = 3
blur = cv2.GaussianBlur(topdown, (kernel_size, kernel_size), 2)

# hsvblur = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
# lower_range = np.array([5, 50, 0])
# upper_range = np.array([40, 200, 150])
# color_mask = cv2.inRange(hsvblur, lower_range, upper_range)

# blur[color_mask > 0 ] = (255, 0, 255)


# image, contours, hierarchy = cv2.findContours(blur,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)

# edges = cv2.drawContours(blur, contours, -1, (0,255,0), 1)

plt.imshow(cv2.cvtColor(cv2.flip(blur, 0), cv2.COLOR_BGR2RGB))
plt.show()

