import os
import sys
import argparse
from Components.YoutubeDownloader import download_youtube_video
from Components.Edit import extractAudio, crop_video, process_individual_clips, create_clips_summary
from Components.Transcription import transcribeAudio
from Components.LanguageTasks import GetHighlight, GetMultipleHighlights
from Components.FaceCrop import crop_to_vertical, combine_videos

# Create outputs directory if it doesn't exist
def ensure_outputs_dir():
    """Ensure the outputs directory exists"""
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
    # Ensure outputs directory exists
    outputs_dir = ensure_outputs_dir()
    
    # Only convert webm to mp4 for downloaded YouTube videos
    if Vid.endswith(".webm"):
        Vid = Vid.replace(".webm", ".mp4")
        print(f"Downloaded video and audio files successfully! at {Vid}")
    else:
        print(f"Using video file: {Vid}")

    Audio = extractAudio(Vid, outputs_dir)
    if Audio:

        transcriptions = transcribeAudio(Audio, outputs_dir)
        if len(transcriptions) > 0:
            TransText = ""

            for text, start, end in transcriptions:
                TransText += (f"{start} - {end}: {text}")

            if single_segment_mode:
                print("Using single segment mode...")
                # Original single highlight method
                start, stop = GetHighlight(TransText)
                if start != 0 and stop != 0:
                    print(f"Start: {start} , End: {stop}")
                    
                    Output = os.path.join(outputs_dir, "Out.mp4")
                    crop_video(Vid, Output, start, stop)
                    
                    if process_face_crop:
                        croped = os.path.join(outputs_dir, "croped.mp4")
                        crop_to_vertical(Output, croped, outputs_dir)
                        combine_videos(Output, croped, os.path.join(outputs_dir, "Final.mp4"))
                        print("Single segment video with face cropping created successfully!")
                    else:
                        print("Single segment video created successfully!")
                else:
                    print("Error in getting highlight")
            else:
                print("Using individual clips mode...")
                # Get multiple highlights for individual clips
                segments = GetMultipleHighlights(TransText)
                
                if segments:
                    print(f"Found {len(segments)} engaging segments:")
                    for i, segment in enumerate(segments):
                        duration = segment.get('duration', segment['end'] - segment['start'])
                        print(f"  {i+1}. '{segment.get('title', f'Clip {i+1}')}' ({segment['start']}-{segment['end']}s, {duration:.1f}s)")
                        print(f"     Priority {segment['priority']}: {segment['content']}")
                    
                    # Process each clip individually
                    processed_clips = process_individual_clips(Vid, segments, outputs_dir)
                    
                    if processed_clips:
                        # Optionally apply face cropping to each clip
                        if process_face_crop:
                            print("\nApplying face detection and vertical cropping to clips...")
                            for clip in processed_clips:
                                if clip.get('status') == 'success':
                                    try:
                                        input_path = clip['path']
                                        cropped_filename = f"cropped_{clip['filename']}"
                                        cropped_path = os.path.join(outputs_dir, cropped_filename)
                                        
                                        crop_to_vertical(input_path, cropped_path, outputs_dir)
                                        
                                        # Update clip info
                                        clip['cropped_filename'] = cropped_filename
                                        clip['cropped_path'] = cropped_path
                                        
                                        print(f"✓ Face-cropped: {cropped_filename}")
                                    except Exception as e:
                                        print(f"✗ Face cropping failed for {clip['filename']}: {e}")
                        
                        # Create summary
                        create_clips_summary(processed_clips, outputs_dir)
                        
                        print(f"\n🎉 Successfully created {len([c for c in processed_clips if c.get('status') == 'success'])} individual clips!")
                        print(f"📁 Files saved in: {outputs_dir}")
                    else:
                        print("No clips were successfully processed")
                else:
                    print("Error in getting highlights - falling back to single highlight")
                    # Fallback to original single highlight method
                    start, stop = GetHighlight(TransText)
                    if start != 0 and stop != 0:
                        print(f"Fallback - Start: {start} , End: {stop}")
                        
                        Output = os.path.join(outputs_dir, "Out.mp4")
                        crop_video(Vid, Output, start, stop)
                        
                        if process_face_crop:
                            croped = os.path.join(outputs_dir, "croped.mp4")
                            crop_to_vertical(Output, croped, outputs_dir)
                            combine_videos(Output, croped, os.path.join(outputs_dir, "Final.mp4"))
                        
                        print("Fallback single segment video created!")
                    else:
                        print("Error in getting highlight")
        else:
            print("No transcriptions found")
    else:
        print("No audio file found")
else:
    print("Unable to Download the video")