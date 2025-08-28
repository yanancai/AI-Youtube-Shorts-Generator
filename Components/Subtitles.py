import os
import pysubs2
from pysubs2 import SSAEvent, SSAStyle
import ffmpeg
from moviepy.editor import VideoFileClip

def create_karaoke_subtitles(word_segments, output_path, style_config=None, max_words_per_line=4):
    """
    Create ASS subtitle file with karaoke effects for word-by-word highlighting
    
    Args:
        word_segments: List of word dictionaries with 'word', 'start', 'end' keys
        output_path: Path to save the .ass subtitle file
        style_config: Optional dictionary with style configuration
        max_words_per_line: Maximum number of words per subtitle line (default: 4)
    
    Returns:
        Path to created subtitle file
    """
    try:
        subs = pysubs2.SSAFile()
        
        # Default style configuration
        default_style = {
            'fontname': 'Arial Black',
            'fontsize': 32,
            'primarycolor': pysubs2.Color(255, 255, 255),      # White text
            'secondarycolor': pysubs2.Color(255, 255, 0),      # Yellow highlight
            'outlinecolor': pysubs2.Color(0, 0, 0),            # Black outline
            'backcolor': pysubs2.Color(0, 0, 0, 100),          # Semi-transparent black background
            'outline': 2,
            'shadow': 1,
            'alignment': 2,  # Bottom center
            'marginv': 50    # Bottom margin
        }
        
        # Update with user configuration if provided
        if style_config:
            default_style.update(style_config)
        
        # Create karaoke style
        karaoke_style = SSAStyle(
            fontname=default_style['fontname'],
            fontsize=default_style['fontsize'],
            primarycolor=default_style['primarycolor'],
            secondarycolor=default_style['secondarycolor'],
            outlinecolor=default_style['outlinecolor'],
            backcolor=default_style['backcolor'],
            outline=default_style['outline'],
            shadow=default_style['shadow'],
            alignment=default_style['alignment'],
            marginv=default_style['marginv']
        )
        
        # Add the style to the subtitle file
        subs.styles["Karaoke"] = karaoke_style
        
        # Group words into short chunks (3-5 words) for better readability on mobile
        current_chunk = []
        chunk_start = None
        
        for i, word_data in enumerate(word_segments):
            word = word_data['word'].strip()
            start_time = word_data['start']
            end_time = word_data['end']
            
            # Initialize chunk timing
            if chunk_start is None:
                chunk_start = start_time
            
            current_chunk.append({
                'word': word,
                'start': start_time,
                'end': end_time,
                'duration_cs': int((end_time - start_time) * 100)  # Convert to centiseconds
            })
            
            # Check if we should end this chunk
            should_end_chunk = (
                len(current_chunk) >= max_words_per_line or  # Max words reached
                word.endswith(('.', '!', '?', ',')) or       # Natural break points
                (i < len(word_segments) - 1 and word_segments[i + 1]['start'] - end_time > 0.8) or  # Pause
                i == len(word_segments) - 1  # Last word
            )
            
            if should_end_chunk and current_chunk:
                chunk_end = end_time
                
                # Create karaoke line for this chunk
                karaoke_text = ""
                for word_info in current_chunk:
                    # Add karaoke timing tag - \\k followed by centiseconds
                    karaoke_text += f"{{\\k{word_info['duration_cs']}}}{word_info['word']} "
                
                # Clean up extra space
                karaoke_text = karaoke_text.rstrip()
                
                # Create subtitle event
                event = SSAEvent(
                    start=int(chunk_start * 1000),  # Convert to milliseconds
                    end=int(chunk_end * 1000),
                    text=karaoke_text,
                    style="Karaoke"
                )
                subs.append(event)
                
                # Reset for next chunk
                current_chunk = []
                chunk_start = None
        
        # Save the subtitle file
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        subs.save(output_path)
        print(f"✓ Karaoke subtitles saved: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Error creating karaoke subtitles: {e}")
        return None


def add_subtitles_to_video(video_path, subtitle_path, output_path, burn_subtitles=True):
    """
    Add subtitles to video using FFmpeg
    
    Args:
        video_path: Input video file path
        subtitle_path: ASS subtitle file path
        output_path: Output video file path
        burn_subtitles: If True, burn subtitles into video. If False, add as subtitle track
    
    Returns:
        Path to output video or None if failed
    """
    try:
        if burn_subtitles:
            # Check if video has audio stream
            probe = ffmpeg.probe(video_path)
            audio_streams = [stream for stream in probe['streams'] if stream['codec_type'] == 'audio']
            
            if audio_streams:
                # Use the same audio codec as regular video output (MP3) for consistency
                audio_codec_output = 'libmp3lame'
                print(f"  Using MP3 audio codec for consistency with non-subtitle output")
                
                # Create input stream
                input_stream = ffmpeg.input(video_path)
                # Apply subtitle filter to video stream
                video_stream = ffmpeg.filter(input_stream['v'], 'subtitles', subtitle_path, 
                                           force_style='FontName=Arial Black,FontSize=32')
                # Keep audio stream as is
                audio_stream = input_stream['a']
                # Output with both streams
                stream = ffmpeg.output(video_stream, audio_stream, output_path, 
                                     vcodec='libx264', acodec=audio_codec_output)
                ffmpeg.run(stream, overwrite_output=True, quiet=True)
            else:
                # No audio stream, just burn subtitles
                stream = ffmpeg.input(video_path)
                stream = ffmpeg.filter(stream, 'subtitles', subtitle_path, 
                                     force_style='FontName=Arial Black,FontSize=32')
                stream = ffmpeg.output(stream, output_path, vcodec='libx264')
                ffmpeg.run(stream, overwrite_output=True, quiet=True)
        else:
            # Add subtitle track (external subtitles)
            video_stream = ffmpeg.input(video_path)
            subtitle_stream = ffmpeg.input(subtitle_path)
            stream = ffmpeg.output(video_stream, subtitle_stream, output_path, 
                                 vcodec='copy', acodec='copy', scodec='ass')
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
        
        print(f"✓ Subtitles added to video: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Error adding subtitles to video: {e}")
        return None


def create_subtitled_clip(video_path, word_segments, output_path, style_config=None, max_words_per_line=4):
    """
    Complete workflow: Create karaoke subtitles and add them to video
    
    Args:
        video_path: Input video file path
        word_segments: List of word dictionaries with timing information
        output_path: Final output video path
        style_config: Optional subtitle styling configuration
        max_words_per_line: Maximum number of words per subtitle line (default: 4)
    
    Returns:
        Path to subtitled video or None if failed
    """
    try:
        # Generate subtitle file path
        subtitle_path = output_path.replace('.mp4', '_karaoke.ass')
        
        # Create karaoke subtitles with word limit
        subtitle_file = create_karaoke_subtitles(word_segments, subtitle_path, style_config, max_words_per_line)
        if not subtitle_file:
            return None
        
        # Add subtitles to video
        final_video = add_subtitles_to_video(video_path, subtitle_file, output_path, burn_subtitles=True)
        
        # Clean up subtitle file (optional - you might want to keep it)
        # os.remove(subtitle_file)
        
        return final_video
        
    except Exception as e:
        print(f"Error creating subtitled clip: {e}")
        return None


def extract_word_segments_for_clip(full_word_segments, clip_start, clip_end):
    """
    Extract word segments that fall within a specific clip timeframe
    
    Args:
        full_word_segments: Complete list of word segments from transcription
        clip_start: Clip start time in seconds
        clip_end: Clip end time in seconds
    
    Returns:
        List of word segments adjusted for clip timing
    """
    clip_words = []
    
    for word_data in full_word_segments:
        word_start = word_data['start']
        word_end = word_data['end']
        
        # Check if word overlaps with clip timeframe
        if word_start < clip_end and word_end > clip_start:
            # Adjust timing relative to clip start
            adjusted_word = {
                'word': word_data['word'],
                'start': max(0, word_start - clip_start),
                'end': min(clip_end - clip_start, word_end - clip_start),
                'segment_id': word_data.get('segment_id', 0)
            }
            clip_words.append(adjusted_word)
    
    return clip_words


# Example usage and test functions
if __name__ == "__main__":
    # Test data
    test_words = [
        {'word': 'Hello', 'start': 0.0, 'end': 0.5},
        {'word': 'world,', 'start': 0.5, 'end': 1.0},
        {'word': 'this', 'start': 1.2, 'end': 1.5},
        {'word': 'is', 'start': 1.5, 'end': 1.7},
        {'word': 'a', 'start': 1.7, 'end': 1.8},
        {'word': 'test.', 'start': 1.8, 'end': 2.3},
    ]
    
    # Test subtitle creation
    subtitle_path = "test_karaoke.ass"
    create_karaoke_subtitles(test_words, subtitle_path)
    
    print("Test subtitle file created successfully!")
