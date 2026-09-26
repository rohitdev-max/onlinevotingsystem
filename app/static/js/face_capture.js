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

        const startCamera = async () => {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                setMessage('Live camera is not supported in this browser. Registration requires a camera.', true);
                return;
            }

            try {
                stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: 'user' },
                    audio: false,
                });
                video.srcObject = stream;
                video.classList.remove('d-none');
                preview.classList.add('d-none');
                captureButton.classList.remove('d-none');
                startButton.classList.add('d-none');
                setMessage('Camera ready. Center the face and capture an image.');
            } catch (error) {
                setMessage('Camera access was denied or unavailable. Registration requires camera access.', true);
            }
        };

        const captureFace = () => {
            if (!stream) return;
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
            canvas.toBlob((blob) => {
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
            if (!captured && !fileInput.files.length) {
                event.preventDefault();
                setMessage('Capture a live face image before submitting.', true);
            }
            stopCamera();
        });
    });
});
