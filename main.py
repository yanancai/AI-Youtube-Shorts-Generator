import os
import sys
import argparse
from datetime import datetime
from Components.YoutubeDownloader import download_youtube_video
from Components.Edit import extractAudio, crop_video, process_individual_clips, create_clips_summary
from Components.Transcription import transcribeAudio
from Components.LanguageTasks import GetHighlight, GetMultipleHighlights, refine_segments_with_word_timestamps
from Components.FaceCrop import crop_to_vertical, combine_videos

# Create organized outputs directory structure with timestamp
def create_run_directory():
    """Create a timestamped run directory with organized subdirectories"""
    # Create base outputs directory
    base_outputs_dir = "outputs"
    if not os.path.exists(base_outputs_dir):
        os.makedirs(base_outputs_dir)
    
    # Create timestamped run directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(base_outputs_dir, f"run_{timestamp}")
    
    # Create subdirectories for better organization
    subdirs = [
        "audio",           # For audio files
        "transcription",   # For transcription files
        "clips",          # For video clips
        "gpt_interactions", # For GPT logs
        "timestamp_refinement", # For timestamp refinement data
        "face_detection"   # For face detection outputs
    ]
    
    for subdir in subdirs:
        subdir_path = os.path.join(run_dir, subdir)
        os.makedirs(subdir_path, exist_ok=True)
    
    print(f"Created run directory: {run_dir}")
    return run_dir

# Legacy function for backward compatibility
def ensure_outputs_dir():
    """Ensure the outputs directory exists (legacy function)"""
    outputs_dir = "outputs"
    if not os.path.exists(outputs_dir):
        os.makedirs(outputs_dir)
    return outputs_dir

def is_url(input_string):
    """Check if the input string is a URL"""
    return input_string.startswith(('http://', 'https://', 'www.')) or 'youtube.com' in input_string or 'youtu.be' in input_string

def get_video_file():
    """Get video file either from YouTube URL or local file path"""
    parser = argparse.ArgumentParser(description='AI YouTube Shorts Generator - Individual Clips Mode')
    parser.add_argument('input', nargs='?', help='YouTube URL or local video file path (supports relative paths)')
    parser.add_argument('--single-segment', action='store_true', help='Use single segment mode (legacy behavior)')
    parser.add_argument('--process-face-crop', action='store_true', help='Apply face detection and vertical cropping to clips')
    
    args = parser.parse_args()
    
    # If command line argument is provided, use it
    if args.input:
        if is_url(args.input):
            print(f"Detected YouTube URL: {args.input}")
            return download_youtube_video(args.input), args.single_segment, args.process_face_crop
        else:
            # Treat as local file path
            video_path = os.path.abspath(args.input)
            if not os.path.exists(video_path):
                print(f"Error: Video file '{video_path}' not found.")
                return None, args.single_segment, args.process_face_crop
            print(f"Using local video file: {video_path}")
            return video_path, args.single_segment, args.process_face_crop
    else:
        # Interactive mode - ask user for input
        user_input = input("Enter YouTube URL or local video file path: ").strip()
        
        # Ask about mode in interactive mode
        mode_choice = input("Use individual clips mode? (y/n, default: y): ").strip().lower()
        single_segment = mode_choice == 'n'
        
        face_crop_choice = input("Apply face detection and vertical cropping? (y/n, default: n): ").strip().lower()
        process_face_crop = face_crop_choice == 'y'
        
        if is_url(user_input):
            print(f"Detected YouTube URL: {user_input}")
            return download_youtube_video(user_input), single_segment, process_face_crop
        else:
            # Treat as local file path
            video_path = os.path.abspath(user_input)
            if not os.path.exists(video_path):
                print(f"Error: Video file '{video_path}' not found.")
                return None, single_segment, process_face_crop
            print(f"Using local video file: {video_path}")
            return video_path, single_segment, process_face_crop

Vid, single_segment_mode, process_face_crop = get_video_file()
if Vid:
    # Create organized run directory with timestamp
    outputs_dir = create_run_directory()
    
    # Only convert webm to mp4 for downloaded YouTube videos
    if Vid.endswith(".webm"):
        Vid = Vid.replace(".webm", ".mp4")
        print(f"Downloaded video and audio files successfully! at {Vid}")
    else:
        print(f"Using video file: {Vid}")

    # Extract audio to the audio subdirectory
    Audio = extractAudio(Vid, os.path.join(outputs_dir, "audio"))
    if Audio:
        # Enhanced transcription with word-level timestamps and speaker diarization
        # Pass the transcription subdirectory
        transcription_result = transcribeAudio(Audio, os.path.join(outputs_dir, "transcription"), 
                                             enable_word_timestamps=True, 
                                             enable_speaker_diarization=True)
        
        if transcription_result and len(transcription_result.get('segments', [])) > 0:
            # For backward compatibility, extract the segments in the old format
            transcriptions = transcription_result['segments']
            
            # Build the old format text for legacy compatibility
            TransText = ""
            for text, start, end in transcriptions:
                TransText += (f"{start} - {end}: {text}")

            if single_segment_mode:
                print("Using single segment mode...")
                # Original single highlight method - pass the full transcription result
                start, stop = GetHighlight(transcription_result, os.path.join(outputs_dir, "gpt_interactions"))
                if start != 0 and stop != 0:
                    print(f"Start: {start} , End: {stop}")
                    
                    Output = os.path.join(outputs_dir, "clips", "Out.mp4")
                    crop_video(Vid, Output, start, stop)
                    
                    if process_face_crop:
                        croped = os.path.join(outputs_dir, "face_detection", "croped.mp4")
                        crop_to_vertical(Output, croped, os.path.join(outputs_dir, "face_detection"))
                        combine_videos(Output, croped, os.path.join(outputs_dir, "clips", "Final.mp4"))
                        print("Single segment video with face cropping created successfully!")
                    else:
                        print("Single segment video created successfully!")
                else:
                    print("Error in getting highlight")
            else:
                print("Using individual clips mode...")
                # Get multiple highlights for individual clips - pass the full transcription result
                segments = GetMultipleHighlights(transcription_result, os.path.join(outputs_dir, "gpt_interactions"))
                
                if segments:
                    # Refine segments with word-level timestamps for more precision
                    print("Refining segment timestamps using word-level matching...")
                    refined_segments = refine_segments_with_word_timestamps(segments, transcription_result, os.path.join(outputs_dir, "timestamp_refinement"))
                    
                    print(f"Found {len(refined_segments)} engaging segments:")
                    for i, segment in enumerate(refined_segments):
                        duration = segment.get('duration', segment['end'] - segment['start'])
                        confidence_info = ""
                        if 'word_match_confidence' in segment:
                            confidence_info = f" (confidence: {segment['word_match_confidence']:.2f})"
                        print(f"  {i+1}. '{segment.get('title', f'Clip {i+1}')}' ({segment['start']}-{segment['end']}s, {duration:.1f}s){confidence_info}")
                        print(f"     Priority {segment['priority']}: {segment['content']}")
                    
                    # Process each clip individually with refined timestamps
                    processed_clips = process_individual_clips(Vid, refined_segments, os.path.join(outputs_dir, "clips"))
                    
                    if processed_clips:
                        # Optionally apply face cropping to each clip
                        if process_face_crop:
                            print("\nApplying face detection and vertical cropping to clips...")
                            for clip in processed_clips:
                                if clip.get('status') == 'success':
                                    try:
                                        input_path = clip['path']
                                        cropped_filename = f"cropped_{clip['filename']}"
                                        cropped_path = os.path.join(outputs_dir, "face_detection", cropped_filename)
                                        
                                        crop_to_vertical(input_path, cropped_path, os.path.join(outputs_dir, "face_detection"))
                                        
                                        # Update clip info
                                        clip['cropped_filename'] = cropped_filename
                                        clip['cropped_path'] = cropped_path
                                        
                                        print(f"✓ Face-cropped: {cropped_filename}")
                                    except Exception as e:
                                        print(f"✗ Face cropping failed for {clip['filename']}: {e}")
                        
                        # Create summary
                        create_clips_summary(processed_clips, os.path.join(outputs_dir, "clips"))
                        
                        print(f"\n🎉 Successfully created {len([c for c in processed_clips if c.get('status') == 'success'])} individual clips!")
                        print(f"📁 Files saved in: {outputs_dir}")
                    else:
                        print("No clips were successfully processed")
                else:
                    print("Error in getting highlights - falling back to single highlight")
                    # Fallback to original single highlight method
                    start, stop = GetHighlight(transcription_result, os.path.join(outputs_dir, "gpt_interactions"))
                    if start != 0 and stop != 0:
                        print(f"Fallback - Start: {start} , End: {stop}")
                        
                        Output = os.path.join(outputs_dir, "clips", "Out.mp4")
                        crop_video(Vid, Output, start, stop)
                        
                        if process_face_crop:
                            croped = os.path.join(outputs_dir, "face_detection", "croped.mp4")
                            crop_to_vertical(Output, croped, os.path.join(outputs_dir, "face_detection"))
                            combine_videos(Output, croped, os.path.join(outputs_dir, "clips", "Final.mp4"))
                        
                        print("Fallback single segment video created!")
                    else:
                        print("Error in getting highlight")
        else:
            print("No transcriptions found")
    else:
        print("No audio file found")
else:
    print("Unable to Download the video")