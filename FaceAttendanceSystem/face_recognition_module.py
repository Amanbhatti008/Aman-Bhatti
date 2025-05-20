import cv2
import face_recognition
import numpy as np
import os
import pickle
from datetime import datetime
import sqlite3


class FaceRecognitionSystem:
    def __init__(self):
        self.known_face_encodings = []
        self.known_face_names = []
        self.initialize_database()
        self.load_known_faces()

    def initialize_database(self):
        self.conn = sqlite3.connect('attendance.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                time TEXT NOT NULL,
                date TEXT NOT NULL
            )
        ''')
        self.conn.commit()

    def load_known_faces(self):
        if not os.path.exists('faces'):
            os.makedirs('faces')

        if os.path.exists('faces/encodings.pkl'):
            with open('faces/encodings.pkl', 'rb') as f:
                data = pickle.load(f)
                self.known_face_encodings = data['encodings']
                self.known_face_names = data['names']

    def save_known_faces(self):
        with open('faces/encodings.pkl', 'wb') as f:
            pickle.dump({
                'encodings': self.known_face_encodings,
                'names': self.known_face_names
            }, f)

    def register_new_face(self, name, image):
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_image)
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)

        if len(face_encodings) > 0:
            self.known_face_encodings.append(face_encodings[0])
            self.known_face_names.append(name)
            self.save_known_faces()
            return True
        return False

    def recognize_faces(self, frame):
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        face_names = []
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.6)
            name = "Unknown"

            face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)

            if matches[best_match_index]:
                name = self.known_face_names[best_match_index]
                self.record_attendance(name)

            face_names.append(name)

        face_locations = [(top * 4, right * 4, bottom * 4, left * 4) for (top, right, bottom, left) in face_locations]

        return face_locations, face_names

    def record_attendance(self, name):
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        current_date = now.strftime("%Y-%m-%d")

        self.cursor.execute('''
            SELECT * FROM attendance 
            WHERE name=? AND date=?
        ''', (name, current_date))

        if not self.cursor.fetchone():
            self.cursor.execute('''
                INSERT INTO attendance (name, time, date)
                VALUES (?, ?, ?)
            ''', (name, current_time, current_date))
            self.conn.commit()