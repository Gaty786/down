import os
import json
import time
import threading
from flask import Flask, render_template, request, jsonify, send_from_directory, abort, session
from werkzeug.utils import secure_filename
import video_downloader

# Configure app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Configure download directory
DOWNLOAD_DIR = "./downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Store active downloads
active_downloads = {}

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/download', methods=['POST'])
def download_video():
    """API endpoint to download a video"""
    video_url = request.form.get('url')
    
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400
    
    # Generate a download ID
    download_id = str(int(time.time()))
    
    # Initialize download status
    active_downloads[download_id] = {
        "status": "initializing",
        "progress": 0,
        "title": None,
        "url": video_url,
        "file_path": None,
        "error": None
    }
    
    # Start download in a separate thread
    thread = threading.Thread(
        target=process_download,
        args=(download_id, video_url)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "download_id": download_id,
        "message": "Download started"
    })

def process_download(download_id, url):
    """Process video download in background"""
    try:
        # Update status
        active_downloads[download_id]["status"] = "extracting_info"
        
        # Get video info
        video_info = video_downloader.get_video_info(url)
        
        if not video_info:
            active_downloads[download_id]["status"] = "failed"
            active_downloads[download_id]["error"] = "Failed to extract video information"
            return
        
        # Update status with video info
        active_downloads[download_id]["title"] = video_info.get("title", "Unknown Title")
        active_downloads[download_id]["file_path"] = video_info.get("output_path")
        active_downloads[download_id]["status"] = "downloading"
        
        # Start download
        result = video_downloader.download_video(url)
        
        if not result:
            active_downloads[download_id]["status"] = "failed"
            active_downloads[download_id]["error"] = "Download failed"
            return
            
        # Update status to complete
        active_downloads[download_id]["status"] = "completed"
        active_downloads[download_id]["progress"] = 100
        
    except Exception as e:
        active_downloads[download_id]["status"] = "failed"
        active_downloads[download_id]["error"] = str(e)

@app.route('/api/download-status/<download_id>')
def download_status(download_id):
    """API endpoint to check download status"""
    if download_id not in active_downloads:
        return jsonify({"error": "Download not found"}), 404
    
    return jsonify(active_downloads[download_id])

@app.route('/api/downloads')
def list_downloads():
    """API endpoint to list all downloads"""
    # List both active downloads and files in download directory
    downloads = []
    
    # Add active downloads
    for download_id, download_info in active_downloads.items():
        downloads.append({
            "id": download_id,
            "title": download_info.get("title", "Unknown"),
            "status": download_info.get("status"),
            "progress": download_info.get("progress", 0),
            "file_path": download_info.get("file_path")
        })
    
    # Add completed downloads that might not be in active_downloads
    if os.path.exists(DOWNLOAD_DIR):
        for filename in os.listdir(DOWNLOAD_DIR):
            filepath = os.path.join(DOWNLOAD_DIR, filename)
            if os.path.isfile(filepath):
                # Check if file is already in the list
                if not any(d.get("file_path") == filepath for d in downloads):
                    file_size = os.path.getsize(filepath)
                    downloads.append({
                        "id": "file_" + secure_filename(filename),
                        "title": filename,
                        "status": "completed",
                        "progress": 100,
                        "file_path": filepath,
                        "file_size": file_size
                    })
    
    return jsonify({"downloads": downloads})

@app.route('/api/delete-download', methods=['POST'])
def delete_download():
    """API endpoint to delete a downloaded file"""
    file_path = request.form.get('file_path')
    
    if not file_path:
        return jsonify({"error": "No file path provided"}), 400
    
    # Security check to make sure we're only deleting from downloads directory
    if not os.path.abspath(file_path).startswith(os.path.abspath(DOWNLOAD_DIR)):
        return jsonify({"error": "Invalid file path"}), 403
    
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({"success": True, "message": "File deleted successfully"})
        else:
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to delete file: {str(e)}"}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Download a file from the download directory"""
    try:
        return send_from_directory(
            DOWNLOAD_DIR, 
            filename, 
            as_attachment=True
        )
    except Exception as e:
        abort(404)

@app.route('/stream/<filename>')
def stream_file(filename):
    """Stream a file for playback"""
    try:
        return send_from_directory(
            DOWNLOAD_DIR, 
            filename, 
            as_attachment=False
        )
    except Exception as e:
        abort(404)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
