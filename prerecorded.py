# need to read this: https://stackoverflow.com/questions/52068277/change-frame-rate-in-opencv-3-4-2
import cv2
import sys
# from PyQt5.QtCore import * 
# from PyQt5.QtGui import * 

from PyQt5.QtCore import * 
from PyQt5.QtGui import * 
from PyQt5.QtWidgets import * 

import mediapipe as mp

import time
import threading

mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles


mp_hands = mp.solutions.hands
mp_face_mesh = mp.solutions.face_mesh
mp_pose = mp.solutions.pose

WIDTH = 640
HEIGHT = 480

WIDTH = 1000
HEIGHT = 800


#TODO: Get frame reading from mp4 in one thread
#TODO: Run processing of frames in other thread

hand_detection_toggle = False
face_mesh_toggle = False
pose_detection_toggle = False



class Thread(QThread):
    
    changePixmap = pyqtSignal(QImage)
    frame_buffer = []

    def read_frames(self, path_to_video_file):
        """method to read all frames in video regardless (to be run in a parallel thread to processing code)"""
        global frame_buffer
        cap = cv2.VideoCapture(path_to_video_file)
        done = False
        while not done:
            ret, image = cap.read()
            if not ret:
                done = True
                return
            else:
                self.frame_buffer.append(image)
    

    def process_image(self, image):
        """adds annotations to image for the models you have selected, 
        For now, it just depict results from hand detection
        TODO: add all models, and link with radio buttons on UI
        """
        global hand_detection_toggle
        global face_mesh_toggle
        global pose_detection_toggle


        hand_detection_results = None
        face_mesh_results = None
        pose_results = None

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        # hand detection
        if hand_detection_toggle:
            with mp_hands.Hands(
                model_complexity=0,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5) as hands:
                hand_detection_results = hands.process(image)


        # face mesh
        if face_mesh_toggle:
            with mp_face_mesh.FaceMesh(
                static_image_mode=True,
                refine_landmarks=True,
                max_num_faces=2,
                min_detection_confidence=0.5) as face_mesh:
                face_mesh_results = face_mesh.process(image)
        

        if pose_detection_toggle:
            with mp_pose.Pose(
                static_image_mode=True, min_detection_confidence=0.5, model_complexity=2) as pose:
                pose_results = pose.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        


        # annotations of results onto image
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        
        # hand-detection annotations
        if hand_detection_toggle and hand_detection_results and hand_detection_results.multi_hand_landmarks:
            for hand_landmarks in hand_detection_results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    image,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS,
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style())
        
        # face-mesh annotations
        if face_mesh_toggle and face_mesh_results and face_mesh_results.multi_face_landmarks:
            for face_landmarks in face_mesh_results.multi_face_landmarks:
                mp_drawing.draw_landmarks(
                    image=image,
                    landmark_list=face_landmarks,
                    connections=mp_face_mesh.FACEMESH_TESSELATION,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing_styles
                    .get_default_face_mesh_tesselation_style())
                mp_drawing.draw_landmarks(
                    image=image,
                    landmark_list=face_landmarks,
                    connections=mp_face_mesh.FACEMESH_CONTOURS,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing_styles
                    .get_default_face_mesh_contours_style())
                mp_drawing.draw_landmarks(
                    image=image,
                    landmark_list=face_landmarks,
                    connections=mp_face_mesh.FACEMESH_IRISES,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=mp_drawing_styles
                    .get_default_face_mesh_iris_connections_style())
        
        # pose detection annotations
        if pose_detection_toggle and pose_results and pose_results.pose_landmarks:
            mp_drawing.draw_landmarks(
                image,
                pose_results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style())    

        return image


    def emit_signal(self, image):
        rgbImage = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgbImage.shape
        bytesPerLine = ch * w
        convertToQtFormat = QImage(rgbImage.data, w, h, bytesPerLine, QImage.Format_RGB888)
        p = convertToQtFormat.scaled(HEIGHT, WIDTH, Qt.KeepAspectRatio)
        self.changePixmap.emit(p)
        return


    def window_update_prerecorded(self, PATH):
        # PATH = "/Users/saahith/Desktop/mediapipe-GUI/test2.mp4"
        cap = cv2.VideoCapture(PATH)
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        duration = frames/fps
        start = time.time()
        
        while True:
            current_time = time.time()
            frame_index = int((current_time - start)/duration * frames)
            if frame_index < len(self.frame_buffer):
                print("index: ", frame_index)
                print("length of buffer: ", len(self.frame_buffer))
                image = self.frame_buffer[frame_index]
                image = self.process_image(image)
                self.emit_signal(image)

    def window_update_webcam(self):
        while True:
            if len(self.frame_buffer) > 0:
                image = self.frame_buffer[-1]
                image = self.process_image(image)
                self.emit_signal(image)


    def run(self):
        use_webcam = True
        PATH = "/Users/saahith/Desktop/mediapipe-GUI/test.mp4"
        if use_webcam:
            PATH = 0
        t1 = threading.Thread(target=self.read_frames, args=(PATH,))
        if use_webcam:
            t2 = threading.Thread(target=self.window_update_webcam, args=())
        else:
            t2 = threading.Thread(target=self.window_update_prerecorded, args=(PATH,))

        # 

        t1.start()
        t2.start()

        t1.join()
        t2.join()




class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.title = 'PyQt5 Video'
        self.left = 100
        self.top = 100
        self.width = HEIGHT
        self.height = WIDTH
        self.initUI()

    @pyqtSlot(QImage)
    def setImage(self, image):
        self.label.setPixmap(QPixmap.fromImage(image))

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.resize(1800, 1200)
        # create a label
        self.label = QLabel(self)
        self.label.move(280, 120)


        self.label.resize(WIDTH, HEIGHT)
        th = Thread(self)
        th.changePixmap.connect(self.setImage)
        th.start()


        # Hand detection toggle button
        self.hand_detection_button = QPushButton("Hand Detection", self)
        self.hand_detection_button.setGeometry(200, 150, 100, 40)
        self.hand_detection_button.setCheckable(True)
        self.hand_detection_button.clicked.connect(self.hand_detection_toggle_switch)
        self.hand_detection_button.setStyleSheet("background-color : lightgrey")


        # face mesh toggle
        self.face_mesh_button = QPushButton("Face Mesh", self)
        self.face_mesh_button.setGeometry(350, 150, 100, 40)
        self.face_mesh_button.setCheckable(True)
        self.face_mesh_button.clicked.connect(self.face_mesh_toggle_switch)
        self.face_mesh_button.setStyleSheet("background-color : lightgrey")

        # pose_detection toggle
        self.pose_detection_button = QPushButton("Pose Detection", self)
        self.pose_detection_button.setGeometry(500, 150, 100, 40)
        self.pose_detection_button.setCheckable(True)
        self.pose_detection_button.clicked.connect(self.pose_detection_toggle_switch)
        self.pose_detection_button.setStyleSheet("background-color : lightgrey")



        self.update()
        self.show()


    def hand_detection_toggle_switch(self):
        global hand_detection_toggle
        hand_detection_toggle = not hand_detection_toggle
        if self.hand_detection_button.isChecked():
            self.hand_detection_button.setStyleSheet("background-color : lightblue")
        else:
            self.hand_detection_button.setStyleSheet("background-color : lightgrey")
    
    def face_mesh_toggle_switch(self):
        global face_mesh_toggle
        face_mesh_toggle = not face_mesh_toggle
        if self.face_mesh_button.isChecked():
            self.face_mesh_button.setStyleSheet("background-color : lightblue")
        else:
            self.face_mesh_button.setStyleSheet("background-color : lightgrey")
    
    def pose_detection_toggle_switch(self):
        global pose_detection_toggle
        pose_detection_toggle = not pose_detection_toggle
        if self.pose_detection_button.isChecked():
            self.pose_detection_button.setStyleSheet("background-color : lightblue")
        else:
            self.pose_detection_button.setStyleSheet("background-color : lightgrey")





if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())