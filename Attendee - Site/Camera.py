# -------------------------Pre-Processing-------------------------------
from time import sleep
import face_recognition
import cv2
import numpy as np
from methods import * 
from concurrent.futures import ThreadPoolExecutor
import os
import json

with open('config.json','r') as f:
    params = json.loads(f.read())['params']

class CameraNotAvailableException(Exception):
    pass

class Camera:
    def __init__(self,duration,classId,className,subject_name):
        '''
        duration in seconds
        '''
        self.state = False
        self.className = className
        self.duration = duration      
        self.mydb = connectWithServer(params=params)   
        self.mycursor = self.mydb.cursor()
        self.mycursor.execute("SELECT cameraIndex FROM classrooms WHERE subject_name = %s",(subject_name,))
        self.cameraIndex = self.mycursor.fetchone()[0]
        self.mycursor.execute("SELECT * from classrooms WHERE cameraIndex = %s AND status = %s",(self.cameraIndex,1,))
        cameraStatus = self.mycursor.fetchone()
        if cameraStatus:
            raise CameraNotAvailableException("Camera is busy right now")
        else:
            self.mycursor.execute(f"UPDATE `classrooms` SET `status` = '1' WHERE `id` = {classId}")
            self.mydb.commit()
        
            
        face_encodings_folder_location = os.path.join(params['face_encodings_folder_location'],f"{className}")
        self.known_face_encoding_files = os.listdir(face_encodings_folder_location)  
        self.known_face_encodings = []

        for filename in os.listdir(face_encodings_folder_location):
            if filename.endswith(".npy"):
                encoding_path = os.path.join(face_encodings_folder_location, filename)
                face_encoding = np.load(encoding_path)
                self.known_face_encodings.append(face_encoding)
        
    def recognition(self,face_encoding):
        mydb = connectWithServer(params=params)   
        mycursor = mydb.cursor()
        # See if the face is a match for the known face(s)
        matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
        # Or instead, use the known face with the smallest distance to the new face
        face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
        best_match_index = np.argmin(face_distances)
        if matches[best_match_index]:
            loginId = self.known_face_encoding_files[best_match_index][:-4]
            mycursor.execute(f"UPDATE `{self.classId}_attendance` SET `{self.columnName}` = '1' WHERE `loginId` = %s",(loginId,))
            mydb.commit()
        mycursor.close()
        mydb.close()
                
    def turnOn(self,classId,columnName):
        self.state = True
        self.classId = classId
        self.columnName = columnName
        self.video_capture = cv2.VideoCapture(int(self.cameraIndex))      
        while self.duration!=0 and self.state:
            ret, frame = self.video_capture.read()
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = small_frame[:, :, ::-1]
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            with ThreadPoolExecutor() as executor:
                executor.map(self.recognition,face_encodings)
                
            sleep(1)
            self.duration -= 1
        self.turnOff(classId)
    def turnOff(self,classId):
        self.state = False
        self.video_capture.release()
        cv2.destroyAllWindows()
        self.mycursor.execute(f"UPDATE `classrooms` SET `status` = '0' WHERE `id` = {classId}")
        self.mydb.commit()