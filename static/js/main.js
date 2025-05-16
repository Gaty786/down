// Global variables for tracking downloads
let activeDownloads = {};
let pollInterval = null;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the page
    initDownloadForm();
    initDownloadList();
    
    // Set up polling for download status
    startStatusPolling();
});

function initDownloadForm() {
    const downloadForm = document.getElementById('downloadForm');
    const urlInput = document.getElementById('videoUrl');
    const submitButton = document.getElementById('submitBtn');
    const downloadStatus = document.getElementById('downloadStatus');
    
    downloadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const url = urlInput.value.trim();
        if (!url) {
            showAlert('Please enter a valid URL', 'danger');
            return;
        }
        
        // Disable form during submission
        urlInput.disabled = true;
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
        
        // Clear previous status
        downloadStatus.innerHTML = '';
        downloadStatus.classList.remove('d-none');
        
        // Create status card
        const statusCard = document.createElement('div');
        statusCard.className = 'card mb-3';
        statusCard.innerHTML = `
            <div class="card-body">
                <h5 class="card-title">Processing URL</h5>
                <p class="card-text text-truncate">${url}</p>
                <div class="progress">
                    <div class="progress-bar progress-bar-striped progress-bar-animated" 
                         role="progressbar" style="width: 0%" aria-valuenow="0" 
                         aria-valuemin="0" aria-valuemax="100"></div>
                </div>
                <p class="mt-2 text-muted status-text">Initializing download...</p>
            </div>
        `;
        
        downloadStatus.appendChild(statusCard);
        
        // Send download request
        const formData = new FormData();
        formData.append('url', url);
        
        fetch('/api/download', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Store download ID for status tracking
                const downloadId = data.download_id;
                activeDownloads[downloadId] = {
                    element: statusCard,
                    url: url
                };
                
                // Update status element with download ID
                statusCard.dataset.downloadId = downloadId;
                
                // Reset form for new input
                urlInput.value = '';
                
                // Show success message
                showAlert('Download started', 'success');
            } else {
                showAlert(data.error || 'Failed to start download', 'danger');
                downloadStatus.removeChild(statusCard);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('An error occurred while processing your request', 'danger');
            downloadStatus.removeChild(statusCard);
        })
        .finally(() => {
            // Re-enable form
            urlInput.disabled = false;
            submitButton.disabled = false;
            submitButton.innerHTML = '<i class="fas fa-download"></i> Download';
        });
    });
}

function startStatusPolling() {
    // Clear any existing poll interval
    if (pollInterval) {
        clearInterval(pollInterval);
    }
    
    // Poll every 2 seconds for download status updates
    pollInterval = setInterval(() => {
        updateAllDownloadStatus();
        refreshDownloadsList();
    }, 2000);
}

function updateAllDownloadStatus() {
    // Check status for all active downloads
    for (const downloadId in activeDownloads) {
        updateDownloadStatus(downloadId);
    }
}

function updateDownloadStatus(downloadId) {
    // Get status element
    const downloadInfo = activeDownloads[downloadId];
    if (!downloadInfo || !downloadInfo.element) return;
    
    const statusCard = downloadInfo.element;
    
    // Fetch current status
    fetch(`/api/download-status/${downloadId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Download not found');
            }
            return response.json();
        })
        .then(data => {
            // Update status card
            const statusTitle = statusCard.querySelector('.card-title');
            const statusText = statusCard.querySelector('.status-text');
            const progressBar = statusCard.querySelector('.progress-bar');
            const cardText = statusCard.querySelector('.card-text');
            
            // Update title and text based on status
            if (data.title && cardText) {
                cardText.textContent = data.title;
            }
            
            switch (data.status) {
                case 'initializing':
                    statusTitle.textContent = 'Initializing';
                    statusText.textContent = 'Setting up download...';
                    progressBar.style.width = '5%';
                    progressBar.setAttribute('aria-valuenow', '5');
                    break;
                    
                case 'extracting_info':
                    statusTitle.textContent = 'Extracting Info';
                    statusText.textContent = 'Getting video information...';
                    progressBar.style.width = '10%';
                    progressBar.setAttribute('aria-valuenow', '10');
                    break;
                    
                case 'downloading':
                    statusTitle.textContent = 'Downloading';
                    statusText.textContent = `Downloading video...`;
                    // Set progress if available
                    const progress = data.progress || 0;
                    progressBar.style.width = `${progress}%`;
                    progressBar.setAttribute('aria-valuenow', progress);
                    break;
                    
                case 'completed':
                    statusTitle.textContent = 'Completed';
                    statusText.textContent = 'Download complete!';
                    progressBar.style.width = '100%';
                    progressBar.setAttribute('aria-valuenow', '100');
                    progressBar.classList.remove('progress-bar-animated', 'progress-bar-striped');
                    progressBar.classList.add('bg-success');
                    
                    // Add download button if file path is available
                    if (data.file_path) {
                        const filename = data.file_path.split('/').pop();
                        const downloadButton = document.createElement('a');
                        downloadButton.href = `/download/${encodeURIComponent(filename)}`;
                        downloadButton.className = 'btn btn-success mt-2';
                        downloadButton.innerHTML = '<i class="fas fa-download"></i> Download File';
                        
                        // Check if button already exists
                        if (!statusCard.querySelector('.btn-success')) {
                            statusCard.querySelector('.card-body').appendChild(downloadButton);
                        }
                    }
                    break;
                    
                case 'failed':
                    statusTitle.textContent = 'Failed';
                    statusText.textContent = data.error || 'Download failed';
                    progressBar.style.width = '100%';
                    progressBar.setAttribute('aria-valuenow', '100');
                    progressBar.classList.remove('progress-bar-animated', 'progress-bar-striped');
                    progressBar.classList.add('bg-danger');
                    break;
            }
            
            // Remove from active downloads if completed or failed
            if (data.status === 'completed' || data.status === 'failed') {
                setTimeout(() => {
                    delete activeDownloads[downloadId];
                }, 10000); // Keep in list for 10 seconds after completion
            }
        })
        .catch(error => {
            console.error('Error fetching download status:', error);
            
            // Handle missing downloads
            if (error.message === 'Download not found') {
                delete activeDownloads[downloadId];
                if (statusCard.parentNode) {
                    statusCard.parentNode.removeChild(statusCard);
                }
            }
        });
}

function refreshDownloadsList() {
    const downloadsList = document.getElementById('downloadsList');
    if (!downloadsList) return;
    
    fetch('/api/downloads')
        .then(response => response.json())
        .then(data => {
            // Clear current list, preserving the title
            downloadsList.innerHTML = '';
            
            if (data.downloads.length === 0) {
                downloadsList.innerHTML = '<div class="alert alert-info">No downloads available</div>';
                return;
            }
            
            // Sort downloads: active first, then completed, then alphabetically
            data.downloads.sort((a, b) => {
                // Active downloads first
                if (a.status !== 'completed' && b.status === 'completed') return -1;
                if (a.status === 'completed' && b.status !== 'completed') return 1;
                
                // Then sort by title
                return a.title.localeCompare(b.title);
            });
            
            // Create table for downloads
            const table = document.createElement('table');
            table.className = 'table table-striped';
            table.innerHTML = `
                <thead>
                    <tr>
                        <th>Title</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody></tbody>
            `;
            
            const tbody = table.querySelector('tbody');
            
            // Add each download to the table
            data.downloads.forEach(download => {
                const tr = document.createElement('tr');
                
                // Determine status class and label
                let statusClass = 'secondary';
                let statusLabel = download.status;
                
                switch (download.status) {
                    case 'completed':
                        statusClass = 'success';
                        statusLabel = 'Completed';
                        break;
                    case 'failed':
                        statusClass = 'danger';
                        statusLabel = 'Failed';
                        break;
                    case 'downloading':
                        statusClass = 'primary';
                        statusLabel = 'Downloading';
                        break;
                    case 'extracting_info':
                        statusClass = 'info';
                        statusLabel = 'Processing';
                        break;
                    case 'initializing':
                        statusClass = 'warning';
                        statusLabel = 'Initializing';
                        break;
                }
                
                // Create actions based on status
                let actions = '';
                
                if (download.status === 'completed' && download.file_path) {
                    const filename = download.file_path.split('/').pop();
                    
                    actions = `
                        <div class="btn-group" role="group">
                            <a href="/download/${encodeURIComponent(filename)}" class="btn btn-sm btn-success">
                                <i class="fas fa-download"></i> Download
                            </a>
                            <a href="/stream/${encodeURIComponent(filename)}" target="_blank" class="btn btn-sm btn-primary">
                                <i class="fas fa-play"></i> Play
                            </a>
                            <button class="btn btn-sm btn-danger delete-btn" data-filepath="${download.file_path}">
                                <i class="fas fa-trash"></i> Delete
                            </button>
                        </div>
                    `;
                }
                
                // Create table row
                tr.innerHTML = `
                    <td class="text-truncate" style="max-width: 200px;">${download.title}</td>
                    <td><span class="badge bg-${statusClass}">${statusLabel}</span></td>
                    <td>${actions}</td>
                `;
                
                tbody.appendChild(tr);
            });
            
            downloadsList.appendChild(table);
            
            // Set up delete buttons
            const deleteButtons = downloadsList.querySelectorAll('.delete-btn');
            deleteButtons.forEach(button => {
                button.addEventListener('click', function() {
                    const filepath = this.dataset.filepath;
                    if (confirm('Are you sure you want to delete this file?')) {
                        deleteDownload(filepath);
                    }
                });
            });
        })
        .catch(error => {
            console.error('Error fetching downloads list:', error);
            downloadsList.innerHTML = '<div class="alert alert-danger">Failed to load downloads</div>';
        });
}

function deleteDownload(filepath) {
    const formData = new FormData();
    formData.append('file_path', filepath);
    
    fetch('/api/delete-download', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('File deleted successfully', 'success');
            refreshDownloadsList();
        } else {
            showAlert(data.error || 'Failed to delete file', 'danger');
        }
    })
    .catch(error => {
        console.error('Error deleting file:', error);
        showAlert('An error occurred while deleting the file', 'danger');
    });
}

function showAlert(message, type) {
    const alertsContainer = document.getElementById('alerts');
    if (!alertsContainer) return;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.role = 'alert';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertsContainer.appendChild(alert);
    
    // Auto-close alert after 5 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }
    }, 5000);
}
