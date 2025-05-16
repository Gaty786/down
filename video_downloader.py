#!/usr/bin/env python3
import os
import re
import sys
import requests
import random
import time
import subprocess
import json
from urllib.parse import urlparse
import logging

# Import youtube-dl for video extraction
try:
    import youtube_dl
except ImportError:
    youtube_dl = None

# Import ffmpeg if available
try:
    import ffmpeg
    ffmpeg_available = True
except ImportError:
    ffmpeg_available = False

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('video_downloader')

# Download directory
DOWNLOAD_DIR = "./downloads"

# User agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 11.5; rv:90.0) Gecko/20100101 Firefox/90.0"
]

def get_random_user_agent():
    """Get a random user agent from the list"""
    return random.choice(USER_AGENTS)

def clean_filename(filename):
    """Clean filename from invalid characters"""
    return re.sub(r'[\\/*?:"<>|]', "_", filename)

def get_file_size(url, headers=None):
    """Get file size from Content-Length header"""
    try:
        if headers is None:
            headers = {'User-Agent': get_random_user_agent()}
        
        response = requests.head(url, headers=headers, timeout=10)
        if 'Content-Length' in response.headers:
            return int(response.headers['Content-Length'])
        return 0
    except Exception as e:
        logger.error(f"Error getting file size: {e}")
        return 0

def download_file(url, filepath, headers=None, chunk_size=8192):
    """Download file with progress tracking"""
    if headers is None:
        headers = {'User-Agent': get_random_user_agent()}
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Check if file exists
        if os.path.exists(filepath):
            logger.info(f"File already exists: {filepath}")
            return filepath
        
        # Get file size
        file_size = get_file_size(url, headers)
        
        # Start download
        logger.info(f"Downloading {url} to {filepath}")
        logger.info(f"File size: {file_size/1024/1024:.2f} MB")
        
        start_time = time.time()
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        downloaded = 0
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Calculate progress
                    percent = (downloaded / file_size * 100) if file_size else 0
                    elapsed = time.time() - start_time
                    speed = downloaded / elapsed if elapsed > 0 else 0
                    
                    # Display progress
                    sys.stdout.write(f"\rProgress: {percent:.1f}% | "
                                    f"{downloaded/1024/1024:.2f} MB / {file_size/1024/1024:.2f} MB | "
                                    f"Speed: {speed/1024/1024:.2f} MB/s")
                    sys.stdout.flush()
        
        print()  # New line after progress
        logger.info(f"Download completed: {filepath}")
        return filepath
            
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        return None

def get_xvideos_info(url):
    """Extract video information from xvideos.com"""
    logger.info(f"Processing XVideos URL: {url}")
    headers = {'User-Agent': get_random_user_agent()}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        content = response.text
        
        # Extract title
        title_match = re.search(r'<title>(.*?)</title>', content)
        title = title_match.group(1).strip() if title_match else "xvideos_video"
        title = title.replace(' - XVIDEOS.COM', '').strip()
        title = clean_filename(title)
        
        logger.info(f"Video title: {title}")
        
        # Find video URLs
        video_url = None
        extension = "mp4"  # Default extension
        
        # Try to find HLS (m3u8) stream
        hls_match = re.search(r'html5player\.setVideoHLS\([\'"](.+?)[\'"]\)', content)
        if hls_match:
            logger.info("Found HLS stream")
            video_url = hls_match.group(1)
            extension = "m3u8"
        
        # Try to find high quality MP4
        if not video_url:
            high_quality_match = re.search(r'html5player\.setVideoUrlHigh\([\'"](.+?)[\'"]\)', content)
            if high_quality_match:
                logger.info("Found high quality MP4")
                video_url = high_quality_match.group(1)
                extension = "mp4"
        
        # Try to find low quality MP4
        if not video_url:
            low_quality_match = re.search(r'html5player\.setVideoUrlLow\([\'"](.+?)[\'"]\)', content)
            if low_quality_match:
                logger.info("Found low quality MP4")
                video_url = low_quality_match.group(1)
                extension = "mp4"
        
        # Last resort: look for any MP4 URL
        if not video_url:
            mp4_match = re.search(r'(https?://(?:www\.)?cdn[^\'"\s]+\.mp4[^\'"\s]*)', content)
            if mp4_match:
                logger.info("Found generic MP4 URL")
                video_url = mp4_match.group(1)
                extension = "mp4"
        
        if not video_url:
            logger.error("No video URL found")
            return None
        
        # Set output filename
        output_filename = f"{title}.{extension}"
        output_path = os.path.join(DOWNLOAD_DIR, output_filename)
        
        return {
            "title": title,
            "url": video_url,
            "extension": extension,
            "output_path": output_path
        }
        
    except Exception as e:
        logger.error(f"Error extracting XVideos info: {e}")
        return None

def get_pornhub_info(url):
    """Extract video information from pornhub.com"""
    logger.info(f"Processing PornHub URL: {url}")
    headers = {'User-Agent': get_random_user_agent()}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        content = response.text
        
        # Extract title
        title_match = re.search(r'<title>(.*?)</title>', content)
        title = title_match.group(1).strip() if title_match else "pornhub_video"
        title = title.replace(' - Pornhub.com', '').strip()
        title = clean_filename(title)
        
        logger.info(f"Video title: {title}")
        
        # Find video URLs
        # PornHub uses a more complex system with flashvars
        flashvars_match = re.search(r'var\s+flashvars_\d+\s*=\s*({.*?});', content, re.DOTALL)
        if not flashvars_match:
            logger.error("Couldn't find flashvars data")
            return None
        
        # Try to extract quality options
        quality_match = re.search(r'"quality_720p":"([^"]+)"', flashvars_match.group(1))
        if not quality_match:
            quality_match = re.search(r'"quality_480p":"([^"]+)"', flashvars_match.group(1))
        if not quality_match:
            quality_match = re.search(r'"quality_240p":"([^"]+)"', flashvars_match.group(1))
        
        video_url = None
        if quality_match:
            video_url = quality_match.group(1).replace('\\/', '/')
            extension = "mp4"
        
        # Try the mediaDefinitions approach if quality not found
        if not video_url:
            definitions_match = re.search(r'"mediaDefinitions":\[(.*?)\]', flashvars_match.group(1), re.DOTALL)
            if definitions_match:
                # Find highest quality MP4
                mp4_matches = re.findall(r'"quality":"([^"]+)"[^}]+"videoUrl":"([^"]+)"', definitions_match.group(1))
                if mp4_matches:
                    # Sort by quality, highest first
                    mp4_matches.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 0, reverse=True)
                    video_url = mp4_matches[0][1].replace('\\/', '/')
                    extension = "mp4"
        
        if not video_url:
            logger.error("No video URL found")
            return None
        
        # Set output filename
        output_filename = f"{title}.{extension}"
        output_path = os.path.join(DOWNLOAD_DIR, output_filename)
        
        return {
            "title": title,
            "url": video_url,
            "extension": extension,
            "output_path": output_path
        }
        
    except Exception as e:
        logger.error(f"Error extracting PornHub info: {e}")
        return None

def download_with_youtube_dl(url, output_path):
    """Download video using youtube-dl"""
    if youtube_dl is None:
        logger.error("YouTube-DL not available")
        return None
        
    try:
        # Base filename (without extension)
        output_template = os.path.splitext(output_path)[0]
        
        # YouTube-DL options
        ydl_opts = {
            'format': 'best[ext=mp4]/best',  # Try to get MP4, otherwise best available
            'outtmpl': output_template + '.%(ext)s',  # Output filename template
            'noplaylist': True,  # Only download single video, not playlist
            'quiet': False,  # Show progress
            'no_warnings': False,
            'ignoreerrors': False,
            'noprogress': False,
            'user_agent': get_random_user_agent(),
        }
        
        logger.info(f"Downloading video with youtube-dl: {url}")
        
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Get the actual downloaded file path
            if 'ext' in info:
                downloaded_file = f"{output_template}.{info['ext']}"
            else:
                # Default to mp4 if extension not found in info
                downloaded_file = f"{output_template}.mp4"
            
            if os.path.exists(downloaded_file):
                logger.info(f"Download completed: {downloaded_file}")
                return downloaded_file
            else:
                logger.error(f"Downloaded file not found: {downloaded_file}")
                return None
    
    except Exception as e:
        logger.error(f"YouTube-DL error: {str(e)}")
        return None

def convert_m3u8_to_mp4(m3u8_url, output_path):
    """Convert an M3U8 stream to an MP4 file using FFmpeg"""
    try:
        logger.info(f"Converting HLS stream to MP4: {output_path}")
        
        # Make sure the output path has .mp4 extension
        mp4_output_path = os.path.splitext(output_path)[0] + '.mp4'
        
        if ffmpeg_available:
            # Using ffmpeg-python library
            (
                ffmpeg
                .input(m3u8_url)
                .output(mp4_output_path, codec='copy')
                .run(capture_stdout=True, capture_stderr=True)
            )
            logger.info(f"FFmpeg conversion completed: {mp4_output_path}")
        else:
            # Using ffmpeg command
            logger.info("Using ffmpeg command")
            ffmpeg_cmd = [
                'ffmpeg', '-y', '-i', m3u8_url, 
                '-c', 'copy', 
                '-bsf:a', 'aac_adtstoasc',
                mp4_output_path
            ]
            subprocess.run(ffmpeg_cmd, check=True)
            logger.info(f"FFmpeg command conversion completed: {mp4_output_path}")
        
        if os.path.exists(mp4_output_path):
            return mp4_output_path
        else:
            logger.error(f"Converted file not found: {mp4_output_path}")
            return None
            
    except Exception as e:
        logger.error(f"FFmpeg conversion error: {str(e)}")
        return None

def get_video_info(url):
    """Get video information based on URL"""
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower()
    
    # Handle domain-specific extraction
    if 'xvideos.com' in domain:
        return get_xvideos_info(url)
    elif 'pornhub.com' in domain:
        return get_pornhub_info(url)
    else:
        # For other sites, try generic youtube-dl approach
        if youtube_dl is not None:
            # Create a temporary output path
            temp_filename = f"video_{int(time.time())}.mp4"
            output_path = os.path.join(DOWNLOAD_DIR, temp_filename)
            
            # Extract info only without downloading
            try:
                logger.info(f"Extracting info with youtube-dl: {url}")
                ydl_opts = {
                    'format': 'best[ext=mp4]/best',
                    'noplaylist': True,
                    'quiet': True,
                    'no_warnings': True,
                    'noprogress': True,
                }
                
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    if info:
                        title = info.get('title', 'video')
                        title = clean_filename(title)
                        
                        # Get extension
                        extension = info.get('ext', 'mp4')
                        
                        # Create proper output path
                        output_filename = f"{title}.{extension}"
                        output_path = os.path.join(DOWNLOAD_DIR, output_filename)
                        
                        return {
                            "title": title,
                            "url": info.get('url'),
                            "extension": extension,
                            "output_path": output_path
                        }
            except Exception as e:
                logger.error(f"Error extracting info with youtube-dl: {e}")
                return None
        
        # If youtube-dl failed or isn't available, return None
        logger.error(f"Unsupported URL or failed to extract info: {url}")
        return None

def download_video(url):
    """Main function to download video from supported sites"""
    try:
        # Create download directory if it doesn't exist
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        
        # Get video info
        video_info = get_video_info(url)
        
        if not video_info:
            logger.error("Failed to extract video information")
            return None
        
        title = video_info.get("title")
        video_url = video_info.get("url")
        extension = video_info.get("extension")
        output_path = video_info.get("output_path")
        
        logger.info(f"Title: {title}")
        logger.info(f"Output path: {output_path}")
        
        # Handle different file types
        if extension == "m3u8":
            # Convert HLS stream to MP4
            result = convert_m3u8_to_mp4(video_url, output_path)
            if result:
                return result
            
            # If FFmpeg conversion failed, try direct download
            logger.info("FFmpeg conversion failed, trying direct download")
        
        # Try direct download for MP4 files
        if extension == "mp4":
            # Download video file
            result = download_file(video_url, output_path)
            if result:
                return result
        
        # If all else fails, try youtube-dl
        logger.info("Regular download failed, trying youtube-dl")
        result = download_with_youtube_dl(url, output_path)
        if result:
            return result
        
        # If all download methods failed
        logger.error("All download methods failed")
        return None
    
    except Exception as e:
        logger.error(f"Error downloading video: {str(e)}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python video_downloader.py <url>")
        sys.exit(1)
    
    url = sys.argv[1]
    download_video(url)
