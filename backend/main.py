import os
import uuid
import logging
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from utils.ffmpeg_processor import process_videos
from utils.file_handler import save_uploaded_files, cleanup_files

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Directories
TEMP_DIR = os.path.join(os.getcwd(), 'temp')
OUTPUT_DIR = os.path.join(os.getcwd(), 'output')

# Ensure directories exist
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200

@app.route('/process', methods=['POST'])
def process():
    """
    Process videos with interleaving
    Expected form data:
    - videos: multiple video files
    - duration: total duration in seconds (integer)
    """
    session_id = str(uuid.uuid4())
    temp_session_dir = os.path.join(TEMP_DIR, session_id)
    os.makedirs(temp_session_dir, exist_ok=True)
    
    try:
        # Validate request
        if 'videos' not in request.files:
            return jsonify({'error': 'No videos provided'}), 400
        
        videos = request.files.getlist('videos')
        
        if len(videos) < 2:
            return jsonify({'error': 'Minimum 2 videos required'}), 400
        
        if len(videos) > 10:
            return jsonify({'error': 'Maximum 10 videos allowed'}), 400
        
        # Get duration
        try:
            duration = int(request.form.get('duration', 0))
        except ValueError:
            return jsonify({'error': 'Invalid duration format'}), 400
        
        if duration < 6 or duration > 600:
            return jsonify({'error': 'Duration must be between 6 and 600 seconds'}), 400
        
        logger.info(f"Session {session_id}: Processing {len(videos)} videos for {duration}s")
        
        # Save uploaded files
        video_paths = save_uploaded_files(videos, temp_session_dir)
        logger.info(f"Session {session_id}: Saved {len(video_paths)} videos")
        
        # Process videos
        output_filename = f"output_{session_id}.mp4"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        process_videos(video_paths, duration, output_path, temp_session_dir)
        logger.info(f"Session {session_id}: Processing completed")
        
        # Cleanup temp files
        cleanup_files(temp_session_dir)
        
        return jsonify({
            'success': True,
            'download_url': f'/download/{output_filename}'
        }), 200
        
    except Exception as e:
        logger.error(f"Session {session_id}: Error - {str(e)}")
        cleanup_files(temp_session_dir)
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>', methods=['GET'])
def download(filename):
    """Download processed video"""
    try:
        file_path = os.path.join(OUTPUT_DIR, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(file_path, as_attachment=True, download_name=filename)
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
