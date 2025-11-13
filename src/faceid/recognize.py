import numpy as np
import imutils
import cv2
import pickle
import face_config as FID_CFG


class Recognizer:
    def __init__(self) -> None:
        self.detector = cv2.dnn.readNetFromCaffe(
            FID_CFG.FID_DEPLOY_FILE, FID_CFG.FID_CAFFE_FILE
        )
        self.embedder = cv2.dnn.readNetFromTorch(FID_CFG.FID_OPENFACE_FILE)
        self.recognizer = pickle.loads(open(FID_CFG.FID_RECOGNIZER_FILE, "rb").read())
        self.le = pickle.loads(open(FID_CFG.FID_LE_FILE, "rb").read())

    def recognize(self, image):
        image = imutils.resize(image, width=600)
        (h, w) = image.shape[:2]

        print("Processing image")

        imageBlob = cv2.dnn.blobFromImage(
            cv2.resize(image, (300, 300)),
            1.0,
            (300, 300),
            (104.0, 177.0, 123.0),
            swapRB=False,
            crop=False,
        )

        self.detector.setInput(imageBlob)
        detections = self.detector.forward()

        faces: dict[str, int] = {}

        # loop over the detections
        for i in range(0, detections.shape[2]):
            # extract the confidence (i.e., probability) associated with the
            # prediction
            confidence = detections[0, 0, i, 2]

            # filter out weak detections
            if confidence > 0.5:
                # compute the (x, y)-coordinates of the bounding box for the
                # face
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype("int")

                # extract the face ROI
                face = image[startY:endY, startX:endX]
                (fH, fW) = face.shape[:2]

                # ensure the face width and height are sufficiently large
                if fW < 20 or fH < 20:
                    continue

                # construct a blob for the face ROI, then pass the blob
                # through our face embedding model to obtain the 128-d
                # quantification of the face
                faceBlob = cv2.dnn.blobFromImage(
                    face, 1.0 / 255, (96, 96), (0, 0, 0), swapRB=True, crop=False
                )
                self.embedder.setInput(faceBlob)
                vec = self.embedder.forward()

                # perform classification to recognize the face
                preds = self.recognizer.predict_proba(vec)[0]
                j = np.argmax(preds)
                proba = preds[j]
                name = self.le.classes_[j]

                faces[name] = proba
        return max(faces.items(), key=lambda x: x[1])[0]  # fancy argmax


if __name__ == "__main__":
    rec = Recognizer()
    img = cv2.imread("test_faceid2.png")
    print(rec.recognize(img))
