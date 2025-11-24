/**
 * Camera Upload Module
 * ====================
 * Ermöglicht Foto-Uploads via Smartphone-Kamera oder Datei-Upload
 *
 * Erstellt von: Hans Hahn - Alle Rechte vorbehalten
 */

class CameraUpload {
    constructor(options = {}) {
        this.options = {
            targetElement: options.targetElement || '#camera-container',
            uploadUrl: options.uploadUrl || '/api/photos/upload',
            photoType: options.photoType || 'other',
            maxFileSize: options.maxFileSize || 10 * 1024 * 1024, // 10MB
            onSuccess: options.onSuccess || this.defaultSuccessHandler,
            onError: options.onError || this.defaultErrorHandler,
            onProgress: options.onProgress || null,
            ...options
        };

        this.stream = null;
        this.isStreaming = false;
        this.init();
    }

    init() {
        this.createUI();
        this.attachEventListeners();
    }

    createUI() {
        const container = document.querySelector(this.options.targetElement);
        if (!container) {
            console.error('Target element not found:', this.options.targetElement);
            return;
        }

        container.innerHTML = `
            <div class="camera-upload-container">
                <!-- Camera Preview -->
                <div class="camera-preview" id="camera-preview" style="display: none;">
                    <video id="camera-video" autoplay playsinline></video>
                    <canvas id="camera-canvas" style="display: none;"></canvas>
                    <div class="camera-controls">
                        <button type="button" class="btn btn-primary btn-lg" id="capture-btn">
                            <i class="fas fa-camera"></i> Foto aufnehmen
                        </button>
                        <button type="button" class="btn btn-secondary btn-lg" id="stop-camera-btn">
                            <i class="fas fa-times"></i> Abbrechen
                        </button>
                    </div>
                </div>

                <!-- Upload Options -->
                <div class="upload-options" id="upload-options">
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <button type="button" class="btn btn-primary btn-block btn-lg" id="start-camera-btn">
                                <i class="fas fa-camera"></i> Kamera öffnen
                            </button>
                        </div>
                        <div class="col-md-6 mb-3">
                            <label for="file-upload" class="btn btn-secondary btn-block btn-lg mb-0">
                                <i class="fas fa-upload"></i> Datei wählen
                            </label>
                            <input type="file" id="file-upload" accept="image/*" style="display: none;">
                        </div>
                    </div>
                    <div class="row">
                        <div class="col-12">
                            <label for="photo-description">Beschreibung (optional):</label>
                            <input type="text" class="form-control" id="photo-description" placeholder="z.B. 'Fadenfarbe Rot'">
                        </div>
                    </div>
                </div>

                <!-- Preview Area -->
                <div class="photo-preview-area mt-3" id="photo-preview-area" style="display: none;">
                    <h5>Vorschau:</h5>
                    <img id="preview-image" src="" alt="Preview" class="img-fluid mb-2" style="max-height: 300px;">
                    <div class="progress" id="upload-progress" style="display: none;">
                        <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 0%"></div>
                    </div>
                    <div class="btn-group mt-2">
                        <button type="button" class="btn btn-success" id="confirm-upload-btn">
                            <i class="fas fa-check"></i> Hochladen
                        </button>
                        <button type="button" class="btn btn-danger" id="cancel-preview-btn">
                            <i class="fas fa-times"></i> Verwerfen
                        </button>
                    </div>
                </div>

                <!-- Uploaded Photos -->
                <div class="uploaded-photos mt-4" id="uploaded-photos">
                    <h5>Hochgeladene Fotos:</h5>
                    <div class="row" id="photos-list"></div>
                </div>
            </div>
        `;
    }

    attachEventListeners() {
        // Start camera
        const startCameraBtn = document.getElementById('start-camera-btn');
        if (startCameraBtn) {
            startCameraBtn.addEventListener('click', () => this.startCamera());
        }

        // Stop camera
        const stopCameraBtn = document.getElementById('stop-camera-btn');
        if (stopCameraBtn) {
            stopCameraBtn.addEventListener('click', () => this.stopCamera());
        }

        // Capture photo
        const captureBtn = document.getElementById('capture-btn');
        if (captureBtn) {
            captureBtn.addEventListener('click', () => this.capturePhoto());
        }

        // File upload
        const fileUpload = document.getElementById('file-upload');
        if (fileUpload) {
            fileUpload.addEventListener('change', (e) => this.handleFileUpload(e));
        }

        // Confirm upload
        const confirmBtn = document.getElementById('confirm-upload-btn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => this.uploadPhoto());
        }

        // Cancel preview
        const cancelBtn = document.getElementById('cancel-preview-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.cancelPreview());
        }
    }

    async startCamera() {
        try {
            // Request camera access
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'environment' // Rückkamera bevorzugen
                },
                audio: false
            });

            const video = document.getElementById('camera-video');
            video.srcObject = this.stream;
            this.isStreaming = true;

            // Show camera preview, hide options
            document.getElementById('camera-preview').style.display = 'block';
            document.getElementById('upload-options').style.display = 'none';

        } catch (error) {
            console.error('Camera access error:', error);
            alert('Kamera-Zugriff fehlgeschlagen. Bitte prüfen Sie die Berechtigungen.');
        }
    }

    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
            this.isStreaming = false;
        }

        // Hide camera preview, show options
        document.getElementById('camera-preview').style.display = 'none';
        document.getElementById('upload-options').style.display = 'block';
    }

    capturePhoto() {
        const video = document.getElementById('camera-video');
        const canvas = document.getElementById('camera-canvas');
        const context = canvas.getContext('2d');

        // Set canvas dimensions to video dimensions
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        // Draw video frame to canvas
        context.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Convert to blob
        canvas.toBlob((blob) => {
            this.prepareUpload(blob);
            this.stopCamera();
        }, 'image/jpeg', 0.85);
    }

    handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        // Validate file type
        if (!file.type.startsWith('image/')) {
            alert('Bitte wählen Sie eine Bilddatei aus.');
            return;
        }

        // Validate file size
        if (file.size > this.options.maxFileSize) {
            alert(`Datei ist zu groß. Maximum: ${this.options.maxFileSize / 1024 / 1024}MB`);
            return;
        }

        this.prepareUpload(file);
    }

    prepareUpload(imageData) {
        // Create preview
        const reader = new FileReader();
        reader.onload = (e) => {
            const preview = document.getElementById('preview-image');
            preview.src = e.target.result;

            // Store image data for upload
            this.currentImageData = e.target.result;

            // Show preview area, hide options
            document.getElementById('photo-preview-area').style.display = 'block';
            document.getElementById('upload-options').style.display = 'none';
        };
        reader.readAsDataURL(imageData);
    }

    cancelPreview() {
        this.currentImageData = null;

        // Hide preview, show options
        document.getElementById('photo-preview-area').style.display = 'none';
        document.getElementById('upload-options').style.display = 'block';

        // Clear file input
        document.getElementById('file-upload').value = '';
    }

    async uploadPhoto() {
        if (!this.currentImageData) return;

        const description = document.getElementById('photo-description').value;

        // Show progress
        const progressContainer = document.getElementById('upload-progress');
        const progressBar = progressContainer.querySelector('.progress-bar');
        progressContainer.style.display = 'block';
        progressBar.style.width = '30%';

        try {
            const response = await fetch(this.options.uploadUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    photo: this.currentImageData,
                    type: this.options.photoType,
                    description: description
                })
            });

            progressBar.style.width = '80%';

            const result = await response.json();

            if (response.ok && result.success) {
                progressBar.style.width = '100%';
                progressBar.classList.remove('progress-bar-animated');
                progressBar.classList.add('bg-success');

                // Success callback
                this.options.onSuccess(result);

                // Add to uploaded photos
                this.addPhotoToList(result.photo);

                // Reset
                setTimeout(() => {
                    this.resetUploadUI();
                }, 1000);

            } else {
                throw new Error(result.error || 'Upload fehlgeschlagen');
            }

        } catch (error) {
            console.error('Upload error:', error);
            this.options.onError(error);
            progressBar.classList.add('bg-danger');
        }
    }

    addPhotoToList(photo) {
        const photosList = document.getElementById('photos-list');

        const photoCard = document.createElement('div');
        photoCard.className = 'col-6 col-md-4 col-lg-3 mb-3';
        photoCard.innerHTML = `
            <div class="card">
                <img src="${photo.thumbnail_url || photo.url}" class="card-img-top" alt="Photo">
                <div class="card-body p-2">
                    <small class="text-muted">${photo.description || photo.type}</small>
                    <button type="button" class="btn btn-sm btn-danger btn-block mt-1"
                            onclick="deletePhoto('${photo.path}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;

        photosList.appendChild(photoCard);
    }

    resetUploadUI() {
        this.currentImageData = null;

        // Hide all, show options
        document.getElementById('photo-preview-area').style.display = 'none';
        document.getElementById('upload-progress').style.display = 'none';
        document.getElementById('upload-options').style.display = 'block';

        // Clear inputs
        document.getElementById('photo-description').value = '';
        document.getElementById('file-upload').value = '';

        // Reset progress bar
        const progressBar = document.querySelector('.progress-bar');
        progressBar.style.width = '0%';
        progressBar.classList.remove('bg-success', 'bg-danger');
        progressBar.classList.add('progress-bar-animated');
    }

    defaultSuccessHandler(result) {
        console.log('Upload successful:', result);
        // You can override this in options
    }

    defaultErrorHandler(error) {
        console.error('Upload error:', error);
        alert('Fehler beim Hochladen: ' + error.message);
    }
}

// Make it globally available
window.CameraUpload = CameraUpload;
