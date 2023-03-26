# -------------------------Pre-Processing-------------------------------
from time import sleep
import face_recognition
import cv2
import numpy as np
from methods import * 
import threading
import os
from datetime import datetime

class Camera:
    def __init__(self,duration,className, mydb, mycursor):
        '''
        duration in seconds
        '''
        self.state = False
        self.mydb = mydb
        self.mycursor = mycursor
        self.className = className
        self.mycursor.execute("SELECT cameraIndex FROM classrooms WHERE class = %s",(className,))
        self.cameraIndex = self.mycursor.fetchone()[0]
        self.duration = duration        
        self.known_images = os.listdir(f"static/images/{self.className}")
        
    def recognition(self,face_encodings:list,classId,columnName):
        for face_encoding in face_encodings:
            # See if the face is a match for the known face(s)
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding,tolerance=0.5)
            # Or instead, use the known face with the smallest distance to the new face
            face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                loginId = self.known_images[best_match_index][:-4]
                self.mycursor.execute(f"UPDATE `{classId}_attendance` SET `{columnName}` = '1' WHERE `loginId` = %s",(loginId,))
                self.mydb.commit()
                
    def turnOn(self,classId,columnName):
        self.state = True
        self.known_face_encodings = []
        self.known_images = self.known_images
        self.video_capture = cv2.VideoCapture(self.cameraIndex)
        for image in self.known_images:
            img = face_recognition.load_image_file(f"static/images/{self.className}/{image}")
            self.known_face_encodings.append(face_recognition.face_encodings(img)[0])
            
        while self.duration!=0 and self.state:
            ret, frame = self.video_capture.read()
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = small_frame[:, :, ::-1]
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            numberOfFace_encodings = len(face_encodings)
            self.t1 = threading.Thread(target=self.recognition,args=[face_encodings[:numberOfFace_encodings//4],classId,columnName])
            self.t2 = threading.Thread(target=self.recognition,args=[face_encodings[numberOfFace_encodings//4:numberOfFace_encodings//2],classId,columnName])
            self.t3 = threading.Thread(target=self.recognition,args=[face_encodings[numberOfFace_encodings//2:int(numberOfFace_encodings/1.3)],classId,columnName])
            self.t4 = threading.Thread(target=self.recognition,args=[face_encodings[int(numberOfFace_encodings/1.3):],classId,columnName])
            
            self.t1.start()
            self.t2.start()
            self.t3.start()
            self.t4.start()
                    
            sleep(1)
            self.duration -= 1
        self.turnOff(classId)
    def turnOff(self,classId):
        self.state = False
        self.video_capture.release()
        cv2.destroyAllWindows()