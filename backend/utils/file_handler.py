import os
import shutil
import logging

logger = logging.getLogger(__name__)

def save_uploaded_files(files, save_dir):
    """
    Save uploaded files to directory
    Returns list of file paths
    """
    os.makedirs(save_dir, exist_ok=True)
    saved_paths = []
    
    for idx, file in enumerate(files):
        # Get file extension
        filename = file.filename
        ext = os.path.splitext(filename)[1]
        
        # Create safe filename
        safe_filename = f"video_{idx}{ext}"
        file_path = os.path.join(save_dir, safe_filename)
        
        # Save file
        file.save(file_path)
        saved_paths.append(file_path)
        logger.info(f"Saved file: {file_path}")
    
    return saved_paths

def cleanup_files(directory):
    """
    Remove directory and all contents
    """
    try:
        if os.path.exists(directory):
            shutil.rmtree(directory)
            logger.info(f"Cleaned up directory: {directory}")
    except Exception as e:
        logger.warning(f"Could not cleanup {directory}: {str(e)}")
