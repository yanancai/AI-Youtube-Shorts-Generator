from faster_whisper import WhisperModel
import torch
import os
import json
from datetime import datetime

def transcribeAudio(audio_path, outputs_dir="outputs"):
    try:
        print("Transcribing audio...")
        Device = "cpu"  # Force CPU usage due to cuDNN compatibility issues
        print(Device)
        model = WhisperModel("base.en", device="cpu")
        print("Model loaded")
        segments, info = model.transcribe(audio=audio_path, beam_size=5, language="en", max_new_tokens=128, condition_on_previous_text=False)
        segments = list(segments)
        # print(segments)
        extracted_texts = [[segment.text, segment.start, segment.end] for segment in segments]
        
        # Save transcription for debugging
        save_transcription(extracted_texts, outputs_dir)
        
        return extracted_texts
    except Exception as e:
        print("Transcription Error:", e)
        return []

def save_transcription(transcription_data, outputs_dir="outputs"):
    """Save transcription data to files for debugging"""
    try:
        # Create transcription subdirectory
        transcription_dir = os.path.join(outputs_dir, "transcription")
        os.makedirs(transcription_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as readable text format (what gets sent to GPT)
        txt_path = os.path.join(transcription_dir, f"transcript_{timestamp}.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("=== TRANSCRIPT FOR GPT ANALYSIS ===\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("Format: start_time - end_time: text\n")
            f.write("=" * 50 + "\n\n")
            
            for text, start, end in transcription_data:
                f.write(f"{start} - {end}: {text}\n")
        
        # Save as structured JSON format
        json_path = os.path.join(transcription_dir, f"transcript_{timestamp}.json")
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
        srt_path = os.path.join(transcription_dir, f"transcript_{timestamp}.srt")
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