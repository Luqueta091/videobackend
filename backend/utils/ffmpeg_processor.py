import os
import ffmpeg
import logging

logger = logging.getLogger(__name__)

def get_video_duration(video_path):
    """Get video duration in seconds"""
    try:
        probe = ffmpeg.probe(video_path)
        duration = float(probe['streams'][0]['duration'])
        return duration
    except Exception as e:
        logger.error(f"Error getting duration for {video_path}: {str(e)}")
        raise

def cut_video_chunk(input_path, output_path, start_time, duration=6):
    """
    Cut a 6-second chunk from video starting at start_time
    """
    try:
        (
            ffmpeg
            .input(input_path, ss=start_time, t=duration)
            .output(output_path, c='copy', avoid_negative_ts='make_zero')
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True, quiet=True)
        )
        logger.info(f"Created chunk: {output_path}")
    except ffmpeg.Error as e:
        logger.error(f"FFmpeg error: {e.stderr.decode()}")
        raise

def concatenate_videos(chunk_paths, output_path):
    """
    Concatenate multiple video chunks using FFmpeg concat demuxer
    """
    try:
        # Create concat file
        concat_file = output_path.replace('.mp4', '_concat.txt')
        with open(concat_file, 'w') as f:
            for chunk_path in chunk_paths:
                f.write(f"file '{os.path.abspath(chunk_path)}'\n")
        
        # Concatenate using concat demuxer
        (
            ffmpeg
            .input(concat_file, format='concat', safe=0)
            .output(output_path, c='copy')
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True, quiet=True)
        )
        
        # Remove concat file
        os.remove(concat_file)
        logger.info(f"Concatenated {len(chunk_paths)} chunks to {output_path}")
        
    except ffmpeg.Error as e:
        logger.error(f"FFmpeg concatenation error: {e.stderr.decode()}")
        raise

def process_videos(video_paths, target_duration, output_path, temp_dir):
    """
    Main processing function: interleave videos in 6-second chunks
    """
    logger.info(f"Processing {len(video_paths)} videos for {target_duration}s")
    
    # Get durations
    durations = [get_video_duration(path) for path in video_paths]
    logger.info(f"Video durations: {durations}")
    
    # Calculate number of rounds
    chunk_duration = 6
    num_chunks_per_video = target_duration // (chunk_duration * len(video_paths))
    total_chunks = num_chunks_per_video * len(video_paths)
    
    logger.info(f"Will create {num_chunks_per_video} rounds with {len(video_paths)} chunks each")
    
    # Track current position in each video
    current_positions = [0] * len(video_paths)
    all_chunks = []
    
    # Generate chunks in interleaved order
    for round_num in range(num_chunks_per_video):
        for video_idx, video_path in enumerate(video_paths):
            # Check if we still have content in this video
            if current_positions[video_idx] + chunk_duration <= durations[video_idx]:
                chunk_name = f"chunk_r{round_num}_v{video_idx}.mp4"
                chunk_path = os.path.join(temp_dir, chunk_name)
                
                cut_video_chunk(
                    video_path,
                    chunk_path,
                    current_positions[video_idx],
                    chunk_duration
                )
                
                all_chunks.append(chunk_path)
                current_positions[video_idx] += chunk_duration
            else:
                logger.warning(f"Video {video_idx} exhausted at round {round_num}")
    
    if not all_chunks:
        raise ValueError("No chunks were created. Videos might be too short.")
    
    logger.info(f"Created {len(all_chunks)} chunks, concatenating...")
    
    # Concatenate all chunks
    concatenate_videos(all_chunks, output_path)
    
    # Cleanup chunk files
    for chunk in all_chunks:
        try:
            os.remove(chunk)
        except Exception as e:
            logger.warning(f"Could not remove chunk {chunk}: {str(e)}")
    
    logger.info(f"Processing complete: {output_path}")
