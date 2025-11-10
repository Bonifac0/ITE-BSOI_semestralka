(function() {
    let streaming = false;
    let video = null;
    let canvas = null;
    let faceLoginBtn = null;
    let takePhotoBtn = null;
    let faceIdContainer = null;
    let faceIdError = null;
    let usernameField = null;

    const width = 320;
    let height = 0;

    function startup() {
        video = document.getElementById('video');
        canvas = document.getElementById('canvas');
        faceLoginBtn = document.getElementById('face-login-btn');
        takePhotoBtn = document.getElementById('take-photo-btn');
        faceIdContainer = document.getElementById('face-id-container');
        faceIdError = document.getElementById('face-id-error');
        usernameField = document.getElementById('username');

        faceLoginBtn.addEventListener('click', function(ev){
            startCamera();
            ev.preventDefault();
        }, false);

        takePhotoBtn.addEventListener('click', function(ev){
            takepictureAndLogin();
            ev.preventDefault();
        }, false);
    }

    function startCamera() {
        faceIdContainer.classList.remove('hidden');
        faceLoginBtn.classList.add('hidden');
        takePhotoBtn.classList.remove('hidden');
        faceIdError.classList.add('hidden');

        navigator.mediaDevices.getUserMedia({video: true, audio: false})
            .then(function(stream) {
                video.srcObject = stream;
                video.play();
            })
            .catch(function(err) {
                console.log("An error occurred: " + err);
                faceIdError.textContent = "Could not access camera. Please check permissions.";
                faceIdError.classList.remove('hidden');
            });

        video.addEventListener('canplay', function(ev){
            if (!streaming) {
                height = video.videoHeight / (video.videoWidth/width);
                if (isNaN(height)) {
                    height = width / (4/3);
                }
                video.setAttribute('width', width);
                video.setAttribute('height', height);
                canvas.setAttribute('width', width);
                canvas.setAttribute('height', height);
                streaming = true;
            }
        }, false);
    }

    function takepictureAndLogin() {
        const context = canvas.getContext('2d');
        const username = usernameField.value;

        if (!username) {
            faceIdError.textContent = "Please enter your username before using Face ID.";
            faceIdError.classList.remove('hidden');
            return;
        }
        faceIdError.classList.add('hidden');

        if (width && height) {
            canvas.width = width;
            canvas.height = height;
            context.drawImage(video, 0, 0, width, height);
            
            const dataUrl = canvas.toDataURL('image/png');
            sendFaceForLogin(dataUrl, username);
        }
    }

    function sendFaceForLogin(dataUrl, username) {
        takePhotoBtn.disabled = true;
        takePhotoBtn.textContent = "Verifying...";

        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/face_login", true);
        xhr.setRequestHeader('Content-Type', 'application/json');

        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4) {
                if (xhr.status === 200) {
                    // Success, redirect to dashboard
                    window.location.href = "/";
                } else {
                    // Failure
                    const response = JSON.parse(xhr.responseText);
                    faceIdError.textContent = response.error || "Face not recognized or does not match username.";
                    faceIdError.classList.remove('hidden');
                    takePhotoBtn.disabled = false;
                    takePhotoBtn.textContent = "Take Photo & Login";
                }
            }
        }

        const payload = JSON.stringify({ image: dataUrl, username: username });
        xhr.send(payload);
    }

    window.addEventListener('load', startup, false);
})();
