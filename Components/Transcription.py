from faster_whisper import WhisperModel
import torch
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from .TimestampUtils import find_word_timestamps

# Load environment variables
load_dotenv()

try:
    from pyannote.audio import Pipeline
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False
    print("Warning: pyannote.audio not available. Speaker diarization will be disabled.")

def transcribeAudio(audio_path, transcription_output_dir="outputs", enable_word_timestamps=True, enable_speaker_diarization=True):
    """
    Transcribe audio with optional word-level timestamps and speaker diarization
    
    Args:
        audio_path: Path to audio file
        transcription_output_dir: Directory to save transcription outputs
        enable_word_timestamps: Whether to enable word-level timestamps
        enable_speaker_diarization: Whether to perform speaker diarization
    
    Returns:
        dict containing:
        - segments: List of [text, start, end] for backward compatibility
        - word_segments: List of word-level segments with timestamps
        - speaker_segments: List of speaker-labeled segments
        - clean_transcript: Clean text without timestamps for GPT
    """
    try:
        print("Transcribing audio...")
        # Auto-detect device with fallback to CPU
        Device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {Device}")
        
        # Load Whisper model
        model = WhisperModel("base.en", device=Device)
        print("Whisper model loaded")
        
        # Transcribe with word-level timestamps
        segments, info = model.transcribe(
            audio=audio_path, 
            beam_size=5, 
            language="en", 
            max_new_tokens=128, 
            condition_on_previous_text=False,
            word_timestamps=enable_word_timestamps
        )
        segments = list(segments)
        
        # Extract word-level data
        word_segments = []
        extracted_texts = []
        
        for segment in segments:
            # For backward compatibility
            extracted_texts.append([segment.text, segment.start, segment.end])
            
            # Extract word-level timestamps if available
            if enable_word_timestamps and hasattr(segment, 'words') and segment.words:
                for word in segment.words:
                    word_segments.append({
                        'word': word.word.strip(),
                        'start': word.start,
                        'end': word.end,
                        'segment_id': len(extracted_texts) - 1
                    })
        
        # Perform speaker diarization if enabled and available
        speaker_segments = []
        if enable_speaker_diarization and PYANNOTE_AVAILABLE:
            try:
                speaker_segments = perform_speaker_diarization(audio_path, transcription_output_dir)
            except Exception as e:
                print(f"Warning: Speaker diarization failed: {e}")
                speaker_segments = []
        
        # Create speaker-labeled transcript
        clean_transcript = create_speaker_labeled_transcript(extracted_texts, speaker_segments)
        
        # Create clean conversation format for GPT
        conversation_transcript = create_clean_conversation_transcript(extracted_texts, speaker_segments)
        
        # Package results
        transcription_result = {
            'segments': extracted_texts,
            'word_segments': word_segments,
            'speaker_segments': speaker_segments,
            'clean_transcript': clean_transcript,  # For backward compatibility
            'conversation_transcript': conversation_transcript  # New format for GPT
        }
        
        # Save transcription data
        save_enhanced_transcription(transcription_result, transcription_output_dir)
        
        return transcription_result
        
    except Exception as e:
        print("Transcription Error:", e)
        return {
            'segments': [],
            'word_segments': [],
            'speaker_segments': [],
            'clean_transcript': ""
        }

def perform_speaker_diarization(audio_path, outputs_dir):
    """Perform speaker diarization using pyannote.audio"""
    try:
        print("Performing speaker diarization...")
        
        # Get Hugging Face token from environment
        hf_token = os.getenv('HF_TOKEN')
        if not hf_token or hf_token == 'your_huggingface_token_here':
            print("Warning: HF_TOKEN not set or using placeholder value. Please set your Hugging Face token in .env file")
            print("You can get a token from: https://huggingface.co/settings/tokens")
            return []
        
        # Suppress tqdm warnings during model loading and inference
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            # Initialize the pipeline with the token
            # Note: You need to accept the pyannote model license at https://huggingface.co/pyannote/speaker-diarization-3.1
            pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", use_auth_token=True)
            pipeline.to(torch.device("cuda"))
            
            # Perform diarization with error handling for tqdm issues
            try:
                diarization = pipeline(audio_path)
            except (AttributeError, KeyError) as e:
                if 'last_print_t' in str(e) or 'tqdm' in str(e):
                    # This is a tqdm cleanup error, ignore it and continue
                    print("Warning: Progress bar cleanup error (ignored)")
                    diarization = pipeline(audio_path)
                else:
                    raise e
        
        # Convert to our format
        speaker_segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            speaker_segments.append({
                'start': turn.start,
                'end': turn.end,
                'speaker': speaker,
                'duration': turn.end - turn.start
            })
        
        print(f"Found {len(set([seg['speaker'] for seg in speaker_segments]))} unique speakers")
        return speaker_segments
        
    except Exception as e:
        print(f"Speaker diarization error: {e}")
        # Return empty list so no speaker tags are added to transcript
        return []

def create_speaker_labeled_transcript(segments, speaker_segments):
    """Create a clean transcript with speaker labels but without timestamps"""
    if not speaker_segments:
        # No speaker info, just return clean text
        clean_lines = []
        for text, start, end in segments:
            clean_lines.append(text.strip())
        return " ".join(clean_lines)
    
    transcript_lines = []
    current_speaker = None
    
    for text, start, end in segments:
        # Find which speaker is talking during this segment
        segment_speaker = find_speaker_for_time(start, end, speaker_segments)
        
        if segment_speaker != current_speaker:
            # New speaker - add speaker label on new line
            if current_speaker is not None:  # Not the first speaker
                transcript_lines.append("\n")
            transcript_lines.append(f"{segment_speaker}: ")
            current_speaker = segment_speaker
        else:
            # Same speaker continuing - add space
            transcript_lines.append(" ")
        
        # Add the clean text (no timestamps)
        transcript_lines.append(text.strip())
    
    return "".join(transcript_lines).strip()

def create_clean_conversation_transcript(segments, speaker_segments):
    """
    Create a completely clean conversation transcript without timestamps,
    formatted as natural dialogue for GPT analysis
    """
    if not speaker_segments:
        # No speaker info - treat as monologue
        clean_text = []
        for text, start, end in segments:
            clean_text.append(text.strip())
        return " ".join(clean_text)
    
    conversation = []
    current_speaker = None
    current_speaker_text = []
    
    for text, start, end in segments:
        segment_speaker = find_speaker_for_time(start, end, speaker_segments)
        
        if segment_speaker != current_speaker:
            # Save previous speaker's text if any
            if current_speaker is not None and current_speaker_text:
                speaker_text = " ".join(current_speaker_text).strip()
                conversation.append(f"{current_speaker}: {speaker_text}")
                current_speaker_text = []
            
            current_speaker = segment_speaker
        
        # Add text to current speaker's content
        current_speaker_text.append(text.strip())
    
    # Don't forget the last speaker
    if current_speaker is not None and current_speaker_text:
        speaker_text = " ".join(current_speaker_text).strip()
        conversation.append(f"{current_speaker}: {speaker_text}")
    
    return "\n\n".join(conversation)

def find_speaker_for_time(start, end, speaker_segments):
    """Find the speaker who is talking during the given time range"""
    segment_center = (start + end) / 2
    
    for speaker_seg in speaker_segments:
        if speaker_seg['start'] <= segment_center <= speaker_seg['end']:
            return speaker_seg['speaker']
    
    return "SPEAKER_UNKNOWN"

def save_enhanced_transcription(transcription_result, transcription_output_dir="outputs"):
    """Save enhanced transcription data to files for debugging"""
    try:
        # Ensure transcription output directory exists
        os.makedirs(transcription_output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save word-level data as JSON
        word_level_path = os.path.join(transcription_output_dir, f"word_level_{timestamp}.json")
        word_data = {
            "timestamp": datetime.now().isoformat(),
            "word_segments": transcription_result['word_segments'],
            "total_words": len(transcription_result['word_segments'])
        }
        with open(word_level_path, 'w', encoding='utf-8') as f:
            json.dump(word_data, f, indent=2, ensure_ascii=False)
        
        # Save speaker diarization data
        if transcription_result['speaker_segments']:
            speaker_path = os.path.join(transcription_output_dir, f"speakers_{timestamp}.json")
            speaker_data = {
                "timestamp": datetime.now().isoformat(),
                "speaker_segments": transcription_result['speaker_segments'],
                "unique_speakers": list(set([seg['speaker'] for seg in transcription_result['speaker_segments']]))
            }
            with open(speaker_path, 'w', encoding='utf-8') as f:
                json.dump(speaker_data, f, indent=2, ensure_ascii=False)
        
        # Save clean conversation transcript (what gets sent to GPT)
        conversation_transcript_path = os.path.join(transcription_output_dir, f"conversation_transcript_{timestamp}.txt")
        with open(conversation_transcript_path, 'w', encoding='utf-8') as f:
            f.write("=== CLEAN CONVERSATION FOR GPT (NATURAL DIALOGUE) ===\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("Format: Natural conversation flow without timestamps\n")
            f.write("=" * 60 + "\n\n")
            f.write(transcription_result['conversation_transcript'])
        
        # Save clean transcript (what gets sent to GPT)
        clean_transcript_path = os.path.join(transcription_output_dir, f"clean_transcript_{timestamp}.txt")
        with open(clean_transcript_path, 'w', encoding='utf-8') as f:
            f.write("=== CLEAN TRANSCRIPT FOR GPT (WITH SPEAKERS) ===\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("Format: Speaker-labeled text without timestamps\n")
            f.write("=" * 60 + "\n\n")
            f.write(transcription_result['clean_transcript'])
        
        # Save original format for backward compatibility
        save_transcription(transcription_result['segments'], transcription_output_dir)
        
        print(f"📝 Enhanced transcription saved to:")
        print(f"   - Word-level data: {word_level_path}")
        if transcription_result['speaker_segments']:
            print(f"   - Speaker data: {speaker_path}")
        print(f"   - Conversation transcript: {conversation_transcript_path}")
        print(f"   - Clean transcript: {clean_transcript_path}")
        
    except Exception as e:
        print(f"Warning: Failed to save enhanced transcription: {e}")

def save_transcription(transcription_data, transcription_output_dir="outputs"):
    """Save transcription data to files for debugging"""
    try:
        # Ensure transcription output directory exists
        os.makedirs(transcription_output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as readable text format (what gets sent to GPT)
        txt_path = os.path.join(transcription_output_dir, f"transcript_{timestamp}.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("=== TRANSCRIPT FOR GPT ANALYSIS ===\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("Format: start_time - end_time: text\n")
            f.write("=" * 50 + "\n\n")
            
            for text, start, end in transcription_data:
                f.write(f"{start} - {end}: {text}\n")
        
        # Save as structured JSON format
        json_path = os.path.join(transcription_output_dir, f"transcript_{timestamp}.json")
        json_data = {
            "timestamp": datetime.now().isoformat(),
            "total_segments": len(transcription_data),
            "segments": [
                {
                    "text": text.strip(),
                    "start_time": float(start),
                    "end_time": float(end),
                    "duration": float(end) - float(start)
                }
                for text, start, end in transcription_data
            ]
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        # Save as SRT subtitle format for easy viewing
        srt_path = os.path.join(transcription_output_dir, f"transcript_{timestamp}.srt")
        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, (text, start, end) in enumerate(transcription_data, 1):
                start_srt = seconds_to_srt_time(float(start))
                end_srt = seconds_to_srt_time(float(end))
                f.write(f"{i}\n")
                f.write(f"{start_srt} --> {end_srt}\n")
                f.write(f"{text.strip()}\n\n")
        
        print(f"📝 Transcription saved to:")
        print(f"   - Text format: {txt_path}")
        print(f"   - JSON format: {json_path}")
        print(f"   - SRT format: {srt_path}")
        
    except Exception as e:
        print(f"Warning: Failed to save transcription: {e}")

def seconds_to_srt_time(seconds):
    """Convert seconds to SRT time format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

if __name__ == "__main__":
    import os
    audio_path = os.path.join("outputs", "audio.wav")
    transcriptions = transcribeAudio(audio_path, "outputs")
    print("Done")
    TransText = ""

    for text, start, end in transcriptions:
        TransText += (f"{start} - {end}: {text}")
    print(TransText)