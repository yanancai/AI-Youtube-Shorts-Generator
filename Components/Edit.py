from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.editor import VideoFileClip
import subprocess
import os
import re

def extractAudio(video_path, audio_output_dir="outputs"):
    try:
        # Ensure the output directory exists
        os.makedirs(audio_output_dir, exist_ok=True)
        
        video_clip = VideoFileClip(video_path)
        audio_path = os.path.join(audio_output_dir, "audio.wav")
        video_clip.audio.write_audiofile(audio_path)
        video_clip.close()
        print(f"Extracted audio to: {audio_path}")
        return audio_path
    except Exception as e:
        print(f"An error occurred while extracting audio: {e}")
        return None


def crop_video(input_file, output_file, start_time, end_time):
    """
    Crop video with precise timestamp handling
    
    Args:
        input_file: Path to input video
        output_file: Path to output video  
        start_time: Start time in seconds (float for precision)
        end_time: End time in seconds (float for precision)
    """
    with VideoFileClip(input_file) as video:
        # Use precise floating-point timestamps
        expected_duration = end_time - start_time
        print(f"   Cropping: {start_time:.3f}s to {end_time:.3f}s (expected duration: {expected_duration:.3f}s)")
        
        cropped_video = video.subclip(start_time, end_time)
        
        # Write with high quality settings to preserve timing precision
        cropped_video.write_videofile(
            output_file, 
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True
        )


def sanitize_filename(title):
    """Convert title to a safe filename"""
    # Remove or replace invalid filename characters
    safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
    safe_title = re.sub(r'\s+', '_', safe_title.strip())
    # Limit length to avoid filesystem issues
    safe_title = safe_title[:50]
    return safe_title


def process_individual_clips(input_file, segments, clips_output_dir):
    """
    Process each segment as a separate video file with descriptive names
    
    Args:
        input_file: Path to input video file
        segments: List of segments with start/end times, titles, and metadata
        clips_output_dir: Directory to save output clip files
        
    Returns:
        List of dictionaries with clip info and file paths
    """
    processed_clips = []
    
    try:
        # Ensure the clips output directory exists
        os.makedirs(clips_output_dir, exist_ok=True)
        
        print(f"Processing {len(segments)} individual clips...")
        
        for i, segment in enumerate(segments):
            start_time = segment['start']
            end_time = segment['end']
            title = segment.get('title', f'Clip_{i+1}')
            content = segment.get('content', 'No description')
            priority = segment.get('priority', 5)
            duration = segment.get('duration', end_time - start_time)
            
            print(f"\nProcessing clip {i+1}/{len(segments)}:")
            print(f"  Title: {title}")
            print(f"  Time: {start_time}s - {end_time}s ({duration:.1f}s)")
            print(f"  Priority: {priority}")
            print(f"  Description: {content}")
            
            # Create safe filename
            safe_title = sanitize_filename(title)
            clip_filename = f"clip_{i+1:02d}_{safe_title}.mp4"
            clip_output_path = os.path.join(clips_output_dir, clip_filename)
            
            # Extract the clip
            try:
                crop_video(input_file, clip_output_path, start_time, end_time)
                
                clip_info = {
                    'index': i + 1,
                    'title': title,
                    'filename': clip_filename,
                    'filepath': clip_output_path,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': duration,
                    'content': content,
                    'priority': priority,
                    'status': 'success'
                }
                
                processed_clips.append(clip_info)
                print(f"  ✓ Saved: {clip_filename}")
                
            except Exception as e:
                print(f"  ✗ Error processing clip: {e}")
                clip_info = {
                    'index': i + 1,
                    'title': title,
                    'error': str(e),
                    'status': 'failed'
                }
                processed_clips.append(clip_info)
                
    except Exception as e:
        print(f"Error in process_individual_clips: {e}")
        
    return processed_clips


def create_clips_summary(processed_clips, clips_output_dir):
    """Create a summary file listing all generated clips"""
    # Ensure the output directory exists
    os.makedirs(clips_output_dir, exist_ok=True)
    
    summary_path = os.path.join(clips_output_dir, "clips_summary.txt")
    
    try:
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("AI YouTube Shorts Generator - Clips Summary\n")
            f.write("=" * 50 + "\n\n")
            
            successful_clips = [clip for clip in processed_clips if clip.get('status') == 'success']
            failed_clips = [clip for clip in processed_clips if clip.get('status') == 'failed']
            
            f.write(f"Total clips processed: {len(processed_clips)}\n")
            f.write(f"Successful: {len(successful_clips)}\n")
            f.write(f"Failed: {len(failed_clips)}\n\n")
            
            if successful_clips:
                f.write("SUCCESSFUL CLIPS:\n")
                f.write("-" * 20 + "\n")
                for clip in successful_clips:
                    f.write(f"{clip['index']:02d}. {clip['title']}\n")
                    f.write(f"    File: {clip['filename']}\n")
                    f.write(f"    Duration: {clip['duration']:.1f}s\n")
                    f.write(f"    Priority: {clip['priority']}\n")
                    f.write(f"    Description: {clip['content']}\n\n")
            
            if failed_clips:
                f.write("FAILED CLIPS:\n")
                f.write("-" * 15 + "\n")
                for clip in failed_clips:
                    f.write(f"{clip['index']:02d}. {clip['title']}\n")
                    f.write(f"    Error: {clip['error']}\n\n")
        
        print(f"\n📋 Summary saved to: {summary_path}")
        return summary_path
        
    except Exception as e:
        print(f"Error creating summary: {e}")
        return None

# Example usage:
if __name__ == "__main__":
    input_file = r"Example.mp4" ## Test
    print(input_file)
    output_file = os.path.join("outputs", "Short.mp4")
    start_time = 31.92 
    end_time = 49.2   

    crop_video(input_file, output_file, start_time, end_time)

