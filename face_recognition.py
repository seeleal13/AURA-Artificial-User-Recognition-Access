import requests
import cv2
import face_recognition
import os
import numpy as np
import imutils
import time

AUTHORIZED_FACES_DIR = "authorized_faces"

known_face_encodings = []
known_face_names = []

if not os.path.exists(AUTHORIZED_FACES_DIR):
    print(f"Error: Directory '{AUTHORIZED_FACES_DIR}' not found. Create it and add seeleal13.jpg.")
    exit()

image_path = os.path.join(AUTHORIZED_FACES_DIR, "seeleal13.jpg")
if not os.path.exists(image_path):
    print(f"Error: Authorized face 'seeleal13.jpg' not found in {AUTHORIZED_FACES_DIR}.")
    exit()

image = face_recognition.load_image_file(image_path)
encodings = face_recognition.face_encodings(image)
if encodings:
    known_face_encodings.append(encodings[0])
    known_face_names.append("Seeleal13")
else:
    print(f"Error: No face found in seeleal13.jpg.")
    exit()

url = "http://192.168.11.100:8080/shot.jpg"

face_locations = []
face_encodings = []
face_names = []
process_this_frame = True
start_time = time.time()
frame_count = 0

print("Starting AURA...")
print("Press Esc to exit")

while True:
    try:
        img_resp = requests.get(url, timeout=5)
        if img_resp.status_code != 200:
            print(f"Error: Failed to fetch image (Status: {img_resp.status_code}).")
            continue

        img_arr = np.array(bytearray(img_resp.content), dtype=np.uint8)
        frame = cv2.imdecode(img_arr, -1)
        if frame is None:
            print("Error: Failed to decode image.")
            continue

        frame = imutils.resize(frame, width=1000, height=1800)

        mean_value = np.mean(frame)
        if np.all(frame == 0) or mean_value < 5.0:
            print(f"Error: Invalid frame (Mean: {mean_value:.2f}). Skipping.")
            continue

        frame_count += 1
        elapsed_time = time.time() - start_time
        fps = frame_count / elapsed_time if elapsed_time > 0 else 0
    
        if process_this_frame:
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            face_names = []
            for face_encoding in face_encodings:
                # Fixed: Use compare_faces, not face_distance
                matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                name = "Unauthorized"
                authorized = False
                
                # Fixed: Use face_encoding, not face_encodings
                face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index] and face_distances[best_match_index] < 0.5:
                    name = known_face_names[best_match_index]
                    authorized = True
                
                face_names.append(name)
                print(f"{'Authorized' if authorized else 'Not Authorized'}: {name}")

        process_this_frame = not process_this_frame

        # Fixed: Moved outside the face detection loop and fixed indentation
        access_text = "Access Denied"
        access_color = (0, 0, 255)  # red
        
        for (top, right, bottom, left), name in zip(face_locations, face_names):
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4
            color = (0, 255, 0) if name == "Seeleal13" else (0, 0, 255)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
            
            if name == "Seeleal13":
                access_text = "Access Granted"
                access_color = (0, 255, 0)  # green

        # Fixed: Moved outside loop and fixed font constants
        cv2.putText(frame, access_text, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_DUPLEX, 1.0, access_color, 2)
        cv2.putText(frame, f"FPS: {fps:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Mean: {mean_value:.2f}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.imshow('AURA - Face Recognition', frame)

        if cv2.waitKey(1) == 27:  # Esc key
            break

    except requests.RequestException as e:
        print(f"Network error: {e}")
        time.sleep(1)
        continue

cv2.destroyAllWindows()