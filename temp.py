import face_recognition as fr
import numpy as np
known_image = fr.load_image_file("images/img1.jpg")
unknown_image = fr.load_image_file("images/img2.jpg")

known_image_encoding = fr.face_encodings(known_image)[0]
unknown_image_encoding = fr.face_encodings(unknown_image)[0]
strFormat = str(known_image_encoding)
print(np.ndarray(strFormat))
results = fr.compare_faces([known_image_encoding],unknown_image_encoding)
print(results)