import os

if os.path.exists("repo"):  # if run on vm
    base = "repo/faceid_files/"
else:  # if run localy
    base = "faceid_files/"

FID_LE_FILE = base + "objects/le.pickle"
FID_DEPLOY_FILE = base + "objects/deploy.prototxt"
FID_CAFFE_FILE = base + "objects/res10_300x300_ssd_iter_140000.caffemodel"
FID_OPENFACE_FILE = base + "objects/openface_nn4.small2.v1.t7"
FID_RECOGNIZER_FILE = base + "objects/recognizer.pickle"

FID_DATASET_FOLDER = base + "dataset"

FID_THRESHOLD = 0.5  # magic number


def check_files():
    files_to_check = [
        FID_LE_FILE,
        FID_DEPLOY_FILE,
        FID_CAFFE_FILE,
        FID_OPENFACE_FILE,
        FID_RECOGNIZER_FILE,
        FID_DATASET_FOLDER,
    ]
    for path in files_to_check:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File (or folder) '{path}' does not exist.")


check_files()
