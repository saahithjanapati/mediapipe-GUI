# need to read this: https://stackoverflow.com/questions/52068277/change-frame-rate-in-opencv-3-4-2
import cv2
import sys
from PyQt5.QtWidgets import  QWidget, QLabel, QApplication
from PyQt5.QtCore import QThread, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap

import mediapipe as mp

import time
import threading

mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_hands = mp.solutions.hands

WIDTH = 640
HEIGHT = 480


#TODO: Get frame reading from mp4 in one thread
#TODO: Run processing of frames in other thread


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
        with mp_hands.Hands(
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5) as hands:

            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = hands.process(image)
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(
                    image,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS,
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style())
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
        use_webcam = False
        PATH = "/Users/saahith/Desktop/mediapipe-GUI/test.mp4"
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




class App(QWidget):
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
        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())