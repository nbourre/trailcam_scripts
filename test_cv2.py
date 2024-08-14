# Test openCV2 to display a video
#
import cv2
import numpy as np

# Load a video file
cap = cv2.VideoCapture(r'd:\temp\100DSCIM\PICT0001.AVI')

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    cv2.imshow('Video', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break