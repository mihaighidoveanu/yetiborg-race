import cv2

img = cv2.imread("photos/1582815603.45.png", cv2.IMREAD_COLOR)
cv2.imshow("test", img)
cv2.waitKey(0)
cv2.destroyAllWindows()
