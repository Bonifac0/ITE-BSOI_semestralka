from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC
import pickle

try:
    import face_config as FID_CFG
    from extract_embeddings import embeddings
except:  # noqa: E722
    import faceid.face_config as FID_CFG
    from faceid.extract_embeddings import embeddings

# load the face embeddings
print("[INFO] loading face embeddings...")
names, embedds = embeddings()

# encode the labels
print("[INFO] encoding labels...")
le = LabelEncoder()
labels = le.fit_transform(names)

# train the model used to accept the 128-d embeddings of the face and
# then produce the actual face recognition
print("[INFO] training model...")
recognizer = SVC(C=1.0, kernel="linear", probability=True)
recognizer.fit(embedds, labels)

# write the actual face recognition model to disk
f = open(FID_CFG.FID_RECOGNIZER_FILE, "wb")
f.write(pickle.dumps(recognizer))
f.close()

# write the label encoder to disk
f = open(FID_CFG.FID_LE_FILE, "wb")
f.write(pickle.dumps(le))
f.close()
