import os
import sys
import argparse
from Components.YoutubeDownloader import download_youtube_video
from Components.Edit import extractAudio, crop_video
from Components.Transcription import transcribeAudio
from Components.LanguageTasks import GetHighlight
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
    parser = argparse.ArgumentParser(description='AI YouTube Shorts Generator')
    parser.add_argument('input', nargs='?', help='YouTube URL or local video file path (supports relative paths)')
    
    args = parser.parse_args()
    
    # If command line argument is provided, use it
    if args.input:
        if is_url(args.input):
            print(f"Detected YouTube URL: {args.input}")
            return download_youtube_video(args.input)
        else:
            # Treat as local file path
            video_path = os.path.abspath(args.input)
            if not os.path.exists(video_path):
                print(f"Error: Video file '{video_path}' not found.")
                return None
            print(f"Using local video file: {video_path}")
            return video_path
    else:
        # Interactive mode - ask user for input
        user_input = input("Enter YouTube URL or local video file path: ").strip()
        
        if is_url(user_input):
            print(f"Detected YouTube URL: {user_input}")
            return download_youtube_video(user_input)
        else:
            # Treat as local file path
            video_path = os.path.abspath(user_input)
            if not os.path.exists(video_path):
                print(f"Error: Video file '{video_path}' not found.")
                return None
            print(f"Using local video file: {video_path}")
            return video_path

Vid = get_video_file()
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

        transcriptions = transcribeAudio(Audio)
        if len(transcriptions) > 0:
            TransText = ""

            for text, start, end in transcriptions:
                TransText += (f"{start} - {end}: {text}")

            start , stop = GetHighlight(TransText)
            if start != 0 and stop != 0:
                print(f"Start: {start} , End: {stop}")

                Output = os.path.join(outputs_dir, "Out.mp4")

                crop_video(Vid, Output, start, stop)
                croped = os.path.join(outputs_dir, "croped.mp4")

                crop_to_vertical(Output, croped, outputs_dir)
                combine_videos(Output, croped, os.path.join(outputs_dir, "Final.mp4"))
            else:
                print("Error in getting highlight")
        else:
            print("No transcriptions found")
    else:
        print("No audio file found")
else:
    print("Unable to Download the video")