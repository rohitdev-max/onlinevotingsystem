document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-face-capture]').forEach((capturePanel) => {
        const form = capturePanel.closest('form');
        const video = capturePanel.querySelector('[data-face-video]');
        const preview = capturePanel.querySelector('[data-face-preview]');
        const canvas = capturePanel.querySelector('[data-face-canvas]');
        const fileInput = form.querySelector('input[name="face_image"]');
        const captureMethod = form.querySelector('input[name="face_capture_method"]');
        const startButton = capturePanel.querySelector('[data-face-start]');
        const captureButton = capturePanel.querySelector('[data-face-take]');
        const retakeButton = capturePanel.querySelector('[data-face-retake]');
        const message = capturePanel.querySelector('[data-face-message]');
        let stream;
        let captured = false;
        let starting = false;

        const setMessage = (text, isError = false) => {
            message.textContent = text;
            message.classList.toggle('text-danger', isError);
        };

        const stopCamera = () => {
            if (stream) {
                stream.getTracks().forEach((track) => track.stop());
                stream = undefined;
            }
            video.srcObject = null;
        };

        const cameraErrorMessage = (error) => {
            switch (error.name) {
                case 'NotAllowedError':
                case 'SecurityError':
                    return 'Camera permission is blocked. Allow camera access for this site in your browser settings, then try again.';
                case 'NotFoundError':
                    return 'No camera was found. Connect or enable a camera, then try again.';
                case 'NotReadableError':
                    return 'The camera is busy or unavailable. Close other apps using it, then try again.';
                case 'OverconstrainedError':
                    return 'The selected camera is unavailable. Try another camera or check its connection.';
                default:
                    return 'The camera could not start. Check browser and operating-system camera permissions, then try again.';
            }
        };

        const waitForVideoFrame = () => new Promise((resolve, reject) => {
            const cleanup = () => {
                window.clearTimeout(timeoutId);
                video.removeEventListener('loadeddata', checkReady);
                video.removeEventListener('error', onError);
            };
            const checkReady = () => {
                if (video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA && video.videoWidth > 0) {
                    cleanup();
                    resolve();
                }
            };
            const onError = () => {
                cleanup();
                reject(new Error('The camera started but did not provide a video frame.'));
            };
            const timeoutId = window.setTimeout(() => {
                cleanup();
                reject(new Error('The camera did not provide a video frame in time.'));
            }, 10000);

            video.addEventListener('loadeddata', checkReady);
            video.addEventListener('error', onError);
            checkReady();
        });

        const startCamera = async () => {
            if (starting) return;
            if (!window.isSecureContext) {
                setMessage('Camera access requires a secure page (HTTPS) or localhost.', true);
                return;
            }
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                setMessage('This browser does not support camera access. Use a current browser over HTTPS or localhost.', true);
                return;
            }

            starting = true;
            startButton.disabled = true;
            setMessage('Requesting camera access. Allow it in the browser prompt.');
            try {
                stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: { ideal: 'user' } },
                    audio: false,
                });
                video.srcObject = stream;
                video.classList.remove('d-none');
                preview.classList.add('d-none');
                await video.play();
                await waitForVideoFrame();
                captureButton.classList.remove('d-none');
                startButton.classList.add('d-none');
                retakeButton.classList.add('d-none');
                setMessage('Camera ready. Center the face and capture an image.');
            } catch (error) {
                stopCamera();
                video.classList.add('d-none');
                captureButton.classList.add('d-none');
                startButton.classList.remove('d-none');
                setMessage(error.name ? cameraErrorMessage(error) : error.message, true);
            } finally {
                starting = false;
                startButton.disabled = false;
            }
        };

        const captureFace = () => {
            if (!stream || video.videoWidth === 0 || video.videoHeight === 0) {
                setMessage('The camera is not ready yet. Wait for the live preview, then try again.', true);
                return;
            }
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const context = canvas.getContext('2d');
            if (!context) {
                setMessage('Could not prepare the captured image. Reload the page and try again.', true);
                return;
            }
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            captureButton.disabled = true;
            canvas.toBlob((blob) => {
                captureButton.disabled = false;
                if (!blob) {
                    setMessage('Could not capture the image. Please try again.', true);
                    return;
                }
                const file = new File([blob], 'live-face-capture.jpg', { type: 'image/jpeg' });
                const transfer = new DataTransfer();
                transfer.items.add(file);
                fileInput.files = transfer.files;
                captureMethod.value = 'camera';
                preview.src = URL.createObjectURL(blob);
                preview.classList.remove('d-none');
                video.classList.add('d-none');
                captureButton.classList.add('d-none');
                retakeButton.classList.remove('d-none');
                captured = true;
                stopCamera();
                setMessage('Face captured. You can retake it before submitting.');
            }, 'image/jpeg', 0.9);
        };

        const retakeFace = () => {
            captured = false;
            fileInput.value = '';
            captureMethod.value = '';
            retakeButton.classList.add('d-none');
            startCamera();
        };

        startButton.addEventListener('click', startCamera);
        captureButton.addEventListener('click', captureFace);
        retakeButton.addEventListener('click', retakeFace);
        form.addEventListener('submit', (event) => {
            if (!captured || captureMethod.value !== 'camera' || !fileInput.files.length) {
                event.preventDefault();
                setMessage('Capture a live face image before submitting.', true);
                return;
            }
            stopCamera();
        });
        window.addEventListener('pagehide', stopCamera, { once: true });
    });
});
