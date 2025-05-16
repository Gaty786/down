# Video Downloader

A web-based video downloader application that allows users to input video URLs and download videos with progress tracking.

![Video Downloader](unnamed.png)

## Features

- **Multiple Platform Support:** Download videos from various video platforms including YouTube, Vimeo, and more
- **Real-time Progress Tracking:** Monitor download progress in real-time
- **Video Management:** View, download, stream, and delete your downloaded videos
- **User-friendly Interface:** Clean, responsive design that works on desktop and mobile devices
- **Error Handling:** Robust error handling for failed downloads

## Tech Stack

- **Backend:** Python, Flask
- **Frontend:** HTML, CSS, JavaScript, Bootstrap
- **Video Processing:** youtube-dl, ffmpeg
- **HTTP Handling:** Requests

## How to Use

1. **Start the Application**
   ```bash
   gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
   ```

2. **Access the Application**
   Open your browser and navigate to `http://localhost:5000`

3. **Download a Video**
   - Enter the URL of the video you want to download in the input field
   - Click the "Download Video" button
   - Wait for the download to complete
   - Access your downloaded video from the "Your Downloads" section

## API Endpoints

- **`/api/download`** - Start a video download
- **`/api/download-status/<download_id>`** - Check the status of a download
- **`/api/downloads`** - List all downloads
- **`/api/delete-download`** - Delete a downloaded file
- **`/download/<filename>`** - Download a file
- **`/stream/<filename>`** - Stream a file for playback

## Project Structure

```
video-downloader/
│
├── app.py                # Main application file with Flask routes
├── main.py               # Entry point for the application
├── video_downloader.py   # Core video downloading functionality
│
├── static/               # Static assets
│   ├── css/              # CSS styles
│   └── js/               # JavaScript files
│
├── templates/            # HTML templates
│   ├── index.html        # Main page template
│   └── layout.html       # Base layout template
│
└── downloads/            # Directory for downloaded videos
```

## Requirements

- Python 3.6+
- Flask
- youtube-dl
- ffmpeg (optional, for better video processing)
- Requests

## Legal Disclaimer

This tool is intended for downloading videos for personal use only. Please respect copyright laws and terms of service of the websites you use.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
