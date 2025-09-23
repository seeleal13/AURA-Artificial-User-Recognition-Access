import requests
import cv2
import face_recognition
import os
import numpy as np
import imutils
import time
import threading
from queue import Queue

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

# my ip virtual cam url
url = "http://192.168.11.101:8080/shot.jpg"
DISPLAY_WIDTH = 800
FACE_PROCESS_SCALE = 0.4
FACE_PROCESS_INTERVAL = 3

# esp32 config
ESP32_URL = "http://192.168.11.102:80/update"
PREVIOUS_ACCESS_GRANTED = None
SESSION = request.Session()

def send_to_esp32(status, details):

    payload = {
        "status": status,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "details": details
    }
    try:
        response = SESSION.post(ESP32_URL, json=payload, timeout=2)
        if response.status_code == 200:
            print(f"Sent to ESP32: {payload} - Response: {response.text}")
        else:
            print(f"Failed to send to ESP32: Status {response.status_code}")
    except Exception as e:
        print(f"Error sending to ESP32: {e}")


class SharedData:
    def __init__(self):
        self.lock = threading.Lock()
        self.latest_frame = None
        self.face_locations = []
        self.face_names = []
        self.access_granted = False
        self.last_face_process_time = 0

shared = SharedData()
running = True

def frame_fetcher():

    global running
    session = requests.Session()
    session.headers.update({'Connection': 'keep-alive'})
    
    while running:
        try:

            response = session.get(url, timeout=1, stream=True)
            if response.status_code == 200:
                img_arr = np.array(bytearray(response.content), dtype=np.uint8)
                frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
                
                if frame is not None:

                    frame = imutils.resize(frame, width=DISPLAY_WIDTH)
                    
                    with shared.lock:
                        shared.latest_frame = frame
                        
        except Exception as e:
            print(f"Frame fetcher error: {e}")
            time.sleep(0.05)

def face_processor():

    global running
    frame_counter = 0
    
    while running:
        current_frame = None
        
        with shared.lock:
            if shared.latest_frame is not None:
                current_frame = shared.latest_frame.copy()
        
        if current_frame is not None:
            frame_counter += 1
            

            if frame_counter % FACE_PROCESS_INTERVAL == 0:
                try:

                    small_frame = cv2.resize(current_frame, (0, 0), fx=FACE_PROCESS_SCALE, fy=FACE_PROCESS_SCALE)
                    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                    

                    face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
                    
                    if face_locations: 
                        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                        
                        face_names = []
                        access_granted = False
                        
                        for face_encoding in face_encodings:
                            matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.6)
                            name = "Unauthorized"
                            
                            if True in matches:
                                face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                                best_match_index = np.argmin(face_distances)
                                if matches[best_match_index] and face_distances[best_match_index] < 0.5:
                                    name = known_face_names[best_match_index]
                                    access_granted = True
                            
                            face_names.append(name)
                        

                        scaled_locations = []
                        scale_factor = 1.0 / FACE_PROCESS_SCALE
                        for (top, right, bottom, left) in face_locations:
                            scaled_locations.append((
                                int(top * scale_factor),
                                int(right * scale_factor),
                                int(bottom * scale_factor),
                                int(left * scale_factor)
                            ))
                        
                        with shared.lock:
                            shared.face_locations = scaled_locations
                            shared.face_names = face_names
                            shared.access_granted = access_granted
                            shared.last_face_process_time = time.time()
                    
                    else:

                        with shared.lock:
                            shared.face_locations = []
                            shared.face_names = []
                            shared.access_granted = False
                            shared.last_face_process_time = time.time()
                
                except Exception as e:
                    print(f"Face processor error: {e}")
        
        time.sleep(0.01)

threading.Thread(target=frame_fetcher, daemon=True).start()
threading.Thread(target=face_processor, daemon=True).start()

print("Press Esc to exit")

start_time = time.time()
frame_count = 0
fps_update_time = start_time

try:
    while True:
        display_frame = None
        

        with shared.lock:
            if shared.latest_frame is not None:
                display_frame = shared.latest_frame.copy()
                current_locations = shared.face_locations.copy()
                current_names = shared.face_names.copy()
                access_granted = shared.access_granted
                last_process_time = shared.last_face_process_time
        
        if display_frame is not None:
            frame_count += 1
            current_time = time.time()
            

            if current_time - fps_update_time >= 1.0:
                fps = frame_count / (current_time - fps_update_time)
                frame_count = 0
                fps_update_time = current_time
            else:
                fps = frame_count / max(current_time - start_time, 0.001)
            

            for (top, right, bottom, left), name in zip(current_locations, current_names):
                color = (0, 255, 0) if name == "Seeleal13" else (0, 0, 255)
                cv2.rectangle(display_frame, (left, top), (right, bottom), color, 2)
                cv2.rectangle(display_frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                cv2.putText(display_frame, name, (left + 6, bottom - 6), 
                           cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
            

            access_text = "Access Granted" if access_granted else "Access Denied"
            access_color = (0, 255, 0) if access_granted else (0, 0, 255)
            
            cv2.putText(display_frame, access_text, (10, display_frame.shape[0] - 10), 
                       cv2.FONT_HERSHEY_DUPLEX, 1.0, access_color, 2)
            cv2.putText(display_frame, f"FPS: {fps:.1f}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            

            process_age = current_time - last_process_time
            status_color = (0, 255, 0) if process_age < 1.0 else (0, 255, 255)
            cv2.putText(display_frame, f"Face Check: {process_age:.1f}s ago", (10, 55), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 1)
            
            cv2.imshow('AURA - Smooth Feed', display_frame)

            global PREVIOUS_ACCESS_GRANTED
            if access_granted != PREVIOUS_ACCESS_GRANTED:
                status = "granted" if access_granted else "denied"
                details = {
                    "detected_faces": current_names,
                    "fps": f"{fps:.1f}"
                }
                threading.Thread(target=send_to_esp32, args=(status, details), daemon=True).start()
                PREVIOUS_ACCESS_GRANTED = access_granted
        

        if cv2.waitKey(1) & 0xFF == 27:  # Esc key
            break

except KeyboardInterrupt:
    pass

finally:
    running = False
    cv2.destroyAllWindows()
    print("AURA stopped.")