from __future__ import division

import cv2
import numpy as np
import matplotlib.pyplot as plt
import math

import glob

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

for photo in list(glob.glob("photos/*.png")):
    pixels_per_centimeter = 2.0

    img = cv2.imread(photo, cv2.IMREAD_COLOR)
    topdown = transform_to_topdown_coordinates(img, pixels_per_centimeter)

    kernel_size = 3
    blur = cv2.GaussianBlur(topdown, (kernel_size, kernel_size), 2)

    hsvblur = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
    avg_saturation = np.mean(hsvblur[:,:,1])
    orange_line = orange_line_mask(hsvblur)

    summ = np.array([0,0]);
    count = 0.0
    idx = np.argwhere(orange_line)
    print(summ)
    y_avg = np.mean(idx[0][:])
    x_avg = np.mean(idx[1][:])
    avgs = np.array([y_avg, x_avg])
    # for i in range(len(orange_line)):
    #     for j in range(len(orange_line[i])):
    #         if orange_line[i,j]==True:
    #             summ[0]+=i
    #             summ[1]+=j
    #             count += 1.0
    summ = (summ / count)  #2=pixelspercm
    # print(blur.shape)
    # print(avg_point)
    # print(summ)
    if not orange_line.any():
        continue
    point = np.array([summ[0], summ[1]])
    print(point)
    # point_idx = np.round(point).astype(int)
    # print(point_idx)
    # blur[point_idx[0] - 10 : point_idx[0] + 10][point_idx[1] - 10 : point_idx[1] + 10] = (0, 255, 255)
    point = np.array([summ[0], summ[1]-len(blur)/2.0])
    print(point)
    angle = math.atan2(point[0],point[1]) #angle in radians 
    print(angle)


    # print(orange_line)
    # white_line = white_line_mask(hsvblur)
    blur[orange_line] = (255, 0, 255)
    # summ = int(summ)
    # blur[int(math.ceil(summ[0]))],math.ceil(summ[1])]=(0,255,0)
    # blur[white_line] = (0, 0, 255)

    plt.figure()
    # blur = cv2.flip(blur,0)
    plt.title(photo)
    plt.imshow(cv2.cvtColor(blur, cv2.COLOR_BGR2RGB))

    plt.show()
