document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileInfo = document.getElementById('file-info');
    const fileName = document.getElementById('file-name');
    const removeFileBtn = document.getElementById('remove-file');
    const evaluateBtn = document.getElementById('evaluate-btn');
    const progressContainer = document.getElementById('progress-container');
    const progressFill = document.querySelector('.progress-fill');
    const progressStatus = document.getElementById('progress-status');
    const resultContainer = document.getElementById('result-container');
    const downloadBtn = document.getElementById('download-btn');

    let currentFile = null;
    let blobUrl = null;
    let evalFilename = null;

    // Handle drag events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });

    // Handle drop
    dropZone.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }

    // Handle click to upload
    dropZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });

    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            if (file.name.endsWith('.docx') || file.name.endsWith('.doc')) {
                currentFile = file;
                fileName.textContent = file.name;
                fileInfo.style.display = 'flex';
                evaluateBtn.disabled = false;
                resultContainer.style.display = 'none';
            } else {
                alert('Please upload a .docx file.');
            }
        }
    }

    // Remove file
    removeFileBtn.addEventListener('click', () => {
        currentFile = null;
        fileInput.value = '';
        fileInfo.style.display = 'none';
        evaluateBtn.disabled = true;
        resultContainer.style.display = 'none';
    });

    // Evaluate
    evaluateBtn.addEventListener('click', async () => {
        if (!currentFile) return;

        // Reset UI
        evaluateBtn.style.display = 'none';
        progressContainer.style.display = 'block';
        resultContainer.style.display = 'none';
        dropZone.style.pointerEvents = 'none';
        removeFileBtn.style.pointerEvents = 'none';
        
        // Start live progress polling
        progressStatus.textContent = "Connecting to backend...";
        progressFill.style.width = "0%";
        
        let isPolling = true;
        
        const pollProgress = async () => {
            if (!isPolling) return;
            try {
                const res = await fetch('http://127.0.0.1:8000/status');
                const data = await res.json();
                // Ensure progress only moves forward to prevent any visual jumps
                const currentWidth = parseFloat(progressFill.style.width) || 0;
                if (data.progress >= currentWidth) {
                    progressFill.style.width = `${data.progress}%`;
                    progressStatus.textContent = data.message;
                }
            } catch (e) {
                // Ignore transient network errors
            }
            if (isPolling) {
                setTimeout(pollProgress, 200);
            }
        };
        
        pollProgress();

        // Upload and Evaluate
        const formData = new FormData();
        formData.append('file', currentFile);

        try {
            const API_URL = 'http://127.0.0.1:8000/evaluate';
            const response = await fetch(API_URL, {
                method: 'POST',
                body: formData
            });

            isPolling = false;

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Server error');
            }

            const blob = await response.blob();
            
            // Generate a download link
            if (blobUrl) {
                URL.revokeObjectURL(blobUrl);
            }
            blobUrl = URL.createObjectURL(blob);
            evalFilename = `eval_${currentFile.name}`;

            progressFill.style.width = '100%';
            progressStatus.textContent = "Complete!";
            
            setTimeout(() => {
                progressContainer.style.display = 'none';
                evaluateBtn.style.display = 'block';
                evaluateBtn.textContent = 'Evaluate Another Document';
                evaluateBtn.disabled = true; // Wait for new file
                resultContainer.style.display = 'block';
                
                // Allow new uploads
                dropZone.style.pointerEvents = 'auto';
                removeFileBtn.style.pointerEvents = 'auto';
                currentFile = null;
                fileInfo.style.display = 'none';
                fileInput.value = '';
            }, 600);

        } catch (error) {
            isPolling = false;
            console.error('Error:', error);
            alert(`An error occurred: ${error.message}`);
            
            progressContainer.style.display = 'none';
            evaluateBtn.style.display = 'block';
            dropZone.style.pointerEvents = 'auto';
            removeFileBtn.style.pointerEvents = 'auto';
        }
    });

    // Download file
    downloadBtn.addEventListener('click', () => {
        if (blobUrl) {
            const a = document.createElement('a');
            a.href = blobUrl;
            a.download = evalFilename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }
    });
});
