import cv2
import numpy as np
from moviepy.editor import *
from Components.Speaker import detect_faces_and_speakers, Frames
import os
import random
global Fps

def crop_to_vertical(input_video_path, output_video_path, face_detection_dir="outputs", random_seed=None):
    # Set random seed for reproducible results if provided
    if random_seed is not None:
        random.seed(random_seed)
    
    # Ensure face detection directory exists
    os.makedirs(face_detection_dir, exist_ok=True)
    
    # Skip DecOut.mp4 - we don't need it for face detection
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    cap = cv2.VideoCapture(input_video_path, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    vertical_height = int(original_height)
    vertical_width = int(vertical_height * 9 / 16)
    print(vertical_height, vertical_width)


    if original_width < vertical_width:
        print("Error: Original video width is less than the desired vertical width.")
        return

    x_start = (original_width - vertical_width) // 2
    x_end = x_start + vertical_width
    print(f"Initial crop - start: {x_start}, end: {x_end}")
    print(f"Crop width: {x_end-x_start}")
    half_width = vertical_width // 2

    # Use XVID codec for better compatibility
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (vertical_width, vertical_height))
    global Fps
    Fps = fps
    print(f"Processing video: {fps} fps, {total_frames} frames")
    count = 0
    
    # Smoothing variables for single face tracking
    current_x_center = original_width // 2  # Current smooth center position
    SMOOTHING_FACTOR = 0.15  # How quickly to move towards target
    MIN_MOVEMENT_THRESHOLD = 3  # Only move if difference is greater than this
    
    for _ in range(total_frames):
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame.")
            break
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
        
        num_faces = len(faces)
        
        if num_faces == 1:
            # Single person: crop to focus on face
            x, y, w, h = faces[0]
            face_center_x = x + (w // 2)
            
            # Apply smoothing
            center_diff = face_center_x - current_x_center
            if abs(center_diff) > MIN_MOVEMENT_THRESHOLD:
                current_x_center += center_diff * SMOOTHING_FACTOR
            
            x_start = int(current_x_center - half_width)
            x_end = int(current_x_center + half_width)
            
            # Ensure boundaries
            if x_start < 0:
                x_start = 0
                x_end = vertical_width
                current_x_center = half_width
            elif x_end > original_width:
                x_end = original_width
                x_start = original_width - vertical_width
                current_x_center = original_width - half_width
                
            cropped_frame = frame[:, x_start:x_end]
            
            if count % 60 == 0:
                print(f"Frame {count}: Single face - Center: {face_center_x:.1f}, Smooth: {current_x_center:.1f}")
                
        elif num_faces == 2:
            # Two people: split screen vertically (top/bottom)
            face1_x, face1_y, face1_w, face1_h = faces[0]
            face2_x, face2_y, face2_w, face2_h = faces[1]
            
            # Determine which face is higher (top) and which is lower (bottom)
            if face1_y + face1_h/2 < face2_y + face2_h/2:
                top_face = faces[0]
                bottom_face = faces[1]
            else:
                top_face = faces[1]
                bottom_face = faces[0]
            
            # Calculate centers for both faces
            top_center_x = top_face[0] + (top_face[2] // 2)
            bottom_center_x = bottom_face[0] + (bottom_face[2] // 2)
            
            # Use average center for horizontal positioning
            combined_center_x = (top_center_x + bottom_center_x) // 2
            
            # Apply smoothing to combined center
            center_diff = combined_center_x - current_x_center
            if abs(center_diff) > MIN_MOVEMENT_THRESHOLD:
                current_x_center += center_diff * SMOOTHING_FACTOR
            
            x_start = int(current_x_center - half_width)
            x_end = int(current_x_center + half_width)
            
            # Ensure boundaries
            if x_start < 0:
                x_start = 0
                x_end = vertical_width
                current_x_center = half_width
            elif x_end > original_width:
                x_end = original_width
                x_start = original_width - vertical_width
                current_x_center = original_width - half_width
            
            cropped_frame = frame[:, x_start:x_end]
            
            if count % 60 == 0:
                print(f"Frame {count}: Two faces - Top: {top_center_x}, Bottom: {bottom_center_x}, Center: {current_x_center:.1f}")
                
        else:
            # No faces or 3+ faces: crop to center
            x_start = (original_width - vertical_width) // 2
            x_end = x_start + vertical_width
            current_x_center = original_width // 2  # Reset center
            
            cropped_frame = frame[:, x_start:x_end]
            
            if count % 60 == 0:
                if num_faces == 0:
                    print(f"Frame {count}: No faces detected - center crop")
                else:
                    print(f"Frame {count}: {num_faces} faces detected - center crop")
        
        # Ensure cropped frame has correct dimensions
        if cropped_frame.shape[1] != vertical_width or cropped_frame.shape[0] != vertical_height:
            # Fallback to center crop if something went wrong
            x_start = (original_width - vertical_width) // 2
            x_end = x_start + vertical_width
            cropped_frame = frame[:, x_start:x_end]
        
        out.write(cropped_frame)
        count += 1

    cap.release()
    out.release()
    
    # Re-encode with MoviePy for better compatibility
    temp_output = output_video_path + "_temp.mp4"
    os.rename(output_video_path, temp_output)
    
    try:
        # Use MoviePy to re-encode with proper codec
        clip = VideoFileClip(temp_output)
        clip.write_videofile(output_video_path, codec='libx264', audio_codec='aac', temp_audiofile='temp-audio.m4a', remove_temp=True)
        clip.close()
        
        # Remove temporary file
        os.remove(temp_output)
        print("Re-encoded for better compatibility")
    except Exception as e:
        print(f"Re-encoding failed, keeping original: {e}")
        if os.path.exists(temp_output):
            os.rename(temp_output, output_video_path)
    
    print("Cropping complete. The video has been saved to", output_video_path, count)



def combine_videos(video_with_audio, video_without_audio, output_filename):
    try:
        # Use MoviePy method with working PCM codec
        clip_with_audio = VideoFileClip(video_with_audio)
        clip_without_audio = VideoFileClip(video_without_audio)
        
        audio = clip_with_audio.audio
        combined_clip = clip_without_audio.set_audio(audio)
        
        # Get FPS from the video file if Fps global variable is not set
        try:
            global Fps
            fps = Fps
        except NameError:
            fps = clip_without_audio.fps
            print(f"Using FPS from video file: {fps}")
        
        combined_clip.write_videofile(output_filename, codec='libx264', audio_codec='libmp3lame', fps=fps, preset='medium', bitrate='3000k')
        print(f"Combined video saved successfully as {output_filename}")
    
    except Exception as e:
        print(f"Error combining video and audio: {str(e)}")



if __name__ == "__main__":
    outputs_dir = "outputs"
    input_video_path = os.path.join(outputs_dir, 'Out.mp4')
    output_video_path = os.path.join(outputs_dir, 'Croped_output_video.mp4')
    final_video_path = os.path.join(outputs_dir, 'final_video_with_audio.mp4')
    dec_out_path = os.path.join(outputs_dir, "DecOut.mp4")
    detect_faces_and_speakers(input_video_path, dec_out_path, outputs_dir)
    crop_to_vertical(input_video_path, output_video_path, outputs_dir)
    combine_videos(input_video_path, output_video_path, final_video_path)



