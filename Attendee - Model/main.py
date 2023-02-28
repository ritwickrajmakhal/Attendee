import face_recognition
import cv2
import numpy as np

vid = cv2.VideoCapture(0)

ritwick_image = face_recognition.load_image_file("images/img8.jpg")
ritwick_face_encoding = face_recognition.face_encodings(ritwick_image)[0]

known_face_encoding = [ritwick_face_encoding]
known_face_name = ["Ritwick"]

while True:
    ret, frame = vid.read()
    
    rgb_frame = frame[:, :, ::-1]
    face_locations = face_recognition.face_locations(frame)
    face_encodings = face_recognition.face_encodings(frame,face_locations)
    
    for(top,right, bottom ,left ),face_encoding in zip(face_locations,face_encodings):
        matches = face_recognition.compare_faces(known_face_encoding,face_encoding)
        name = "Unknown"
        
        face_distances = face_recognition.face_distance(known_face_encoding, face_encoding)
        best_match_index = np.argmin(face_distances)
        if matches[best_match_index]:
            name = known_face_name[best_match_index]

        print(name)

    # Display the resulting image
    cv2.imshow('Video', frame)

    # Hit 'q' on the keyboard to quit!
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release handle to the webcam
vid.release()
cv2.destroyAllWindows()
