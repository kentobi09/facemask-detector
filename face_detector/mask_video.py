from tensorflow import keras
from imutils.video import VideoStream
import numpy as np
import imutils
import cv2
import os
import pygame
import threading
import time

pygame.mixer.init()
alarm_sound = pygame.mixer.Sound('alarm.mp3')
alarm_active = False

def play_alarm():
    global alarm_active
    
    if not alarm_active:
        alarm_active = True
        alarm_sound.play()
        time.sleep(3)  
        alarm_sound.stop()
        alarm_active = False

def detect_mask(frame,faceNet,maskNet):

    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1.0, (224, 224),
        (104.0, 177.0, 123.0))
    
    faceNet.setInput(blob)
    detections = faceNet.forward()
    print(detections.shape)

    faces = []
    locs = []
    preds = []

    for i in range(0, detections.shape[2]):

        confidence = detections[0, 0, i, 2]

        if confidence > 0.5:
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")

            (startX, startY) = (max(0, startX), max(0, startY))
            (endX, endY) = (min(w - 1, endX), min(h - 1, endY))

            face = frame[startY:endY, startX:endX]
            face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
            face = cv2.resize(face, (224, 224))
            face = keras.utils.img_to_array(face)
            face = keras.applications.mobilenet_v2.preprocess_input(face)

            faces.append(face)
            locs.append((startX, startY, endX, endY))

    if len(faces) > 0:
        faces = np.array(faces, dtype="float32")
        preds = maskNet.predict(faces, batch_size=32)

    return (locs, preds)

prototxtPath = os.path.sep.join(["face_detector", "deploy.prototxt"])
weightsPath = os.path.sep.join(["face_detector",
    "res10_300x300_ssd_iter_140000.caffemodel"])
faceNet = cv2.dnn.readNet(prototxtPath, weightsPath)

maskNet = keras.models.load_model("mask_detector.h5")

print("[INFO] starting video stream...")
vs = VideoStream(src=0).start()


while True:

    frame = vs.read()
    frame = imutils.resize(frame, width=400)

    (locs, preds) = detect_mask(frame, faceNet, maskNet)

    no_mask_detected = False

    for (box, pred) in zip(locs, preds):
        (startX, startY, endX, endY) = box
        (mask, withoutMask) = pred

        label = "Mask" if mask > withoutMask else "No Mask"
        color = (0, 255, 0) if label == "Mask" else (0, 0, 255)

        if label == "No Mask":
            no_mask_detected = True

        label = "{}: {:.2f}%".format(label, max(mask, withoutMask) * 100)

        cv2.putText(frame, label, (startX, startY - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 2)
        cv2.rectangle(frame, (startX, startY), (endX, endY), color, 2)

    if no_mask_detected and not alarm_active:
        threading.Thread(target=play_alarm, daemon=True).start()
    
    
    cv2.imshow("Frame", frame)
    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

cv2.destroyAllWindows()
vs.stop()
