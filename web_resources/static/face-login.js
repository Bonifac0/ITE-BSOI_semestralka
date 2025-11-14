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

    // Function to hash password using Web Crypto API
    async function hashPassword(password) {
        const textEncoder = new TextEncoder();
        const data = textEncoder.encode(password);
        const hashBuffer = await crypto.subtle.digest('SHA-256', data);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hexHash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
        return hexHash;
    }

    // Function to handle login form submission
    window.handleLoginSubmit = async function(event) {
        event.preventDefault(); // Prevent default form submission

        const form = event.target;
        const usernameField = document.getElementById('username');
        const passwordField = document.getElementById('password');
        const faceIdError = document.getElementById('face-id-error'); // Assuming this element exists for error display

        // Clear previous errors
        faceIdError.classList.add('hidden');
        faceIdError.textContent = "";

        const username = usernameField.value;
        const password = passwordField.value;

        if (!username || !password) {
            faceIdError.textContent = "Please enter both username and password.";
            faceIdError.classList.remove('hidden');
            return false;
        }

        try {
            const hashedPassword = await hashPassword(password);
            // Update the password field with the hashed password before submitting
            passwordField.value = hashedPassword;
            // Set the form action to the correct endpoint
            form.action = '/login_action';
            // Now submit the form programmatically
            form.submit();
        } catch (error) {
            console.error("Error hashing password:", error);
            faceIdError.textContent = "An error occurred during password processing. Please try again.";
            faceIdError.classList.remove('hidden');
            return false;
        }
    };
})();
