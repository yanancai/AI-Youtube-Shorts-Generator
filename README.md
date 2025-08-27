# AI Youtube Shorts Generator

AI Youtube Shorts Generator is a Python tool designed to generate engaging YouTube shorts from long-form videos. By leveraging the power of GPT-4 and Whisper, it extracts the most interesting highlights, detects speakers, and crops the content vertically for shorts. The tool supports both YouTube URLs and local video files (with relative/absolute path support).

## 🆕 Latest Features (v0.5) - Organized Output Structure

- **📁 Timestamped Run Directories**: Each run creates a timestamped directory for complete organization
- **🗂️ Categorized Subdirectories**: Separate folders for audio, transcription, clips, GPT logs, and face detection
- **🔍 Enhanced Debugging**: All intermediate files preserved in organized structure
- **📊 Better File Management**: Easy cleanup and parallel runs without conflicts
- **⏰ Chronological Organization**: Find any run by timestamp for easy tracking

## Enhanced Features (v0.4) - Enhanced Precision

- **🎯 Word-Level Timestamps**: Precise clip boundaries using word-by-word timing analysis
- **🗣️ Speaker Diarization**: Automatic speaker identification and labeled transcripts
- **🤖 Enhanced GPT Integration**: Clean speaker-labeled transcripts sent to GPT (no timestamps)
- **🔍 Smart Timestamp Refinement**: Automatically matches GPT clip suggestions to exact word positions
- **📊 Comprehensive Debugging**: Save all GPT inputs/outputs and timing analysis for debugging
- **✅ Confidence Scoring**: Quality metrics for each timestamp refinement
- **🔄 Backward Compatibility**: All existing workflows continue to work unchanged

See [OUTPUT_STRUCTURE.md](OUTPUT_STRUCTURE.md) for details on the new organized directory structure.
See [ENHANCED_FEATURES.md](ENHANCED_FEATURES.md) for detailed documentation of the precision features.

## Features (v0.3)

- **Individual Clip Generation**: Creates separate video files for each engaging segment
- **Descriptive Titles**: AI generates catchy titles for each clip suitable for social media
- **Context Preservation**: Each clip maintains its original context and makes sense standalone
- **Flexible Quantity**: Variable number of clips based on actual content quality (not forced 3-5)
- **Duration Validation**: Each clip limited to under 60 seconds for optimal engagement
- **Smart File Naming**: Clips saved with descriptive filenames based on AI-generated titles
- **Clips Summary**: Automatic generation of summary file listing all created clips
- **Transcription Debugging**: Saves Whisper transcriptions in organized subdirectories for analysis
- **Multiple Formats**: Transcriptions saved as text (for GPT), JSON (structured), and SRT (subtitles)
- **Customizable Prompts**: GPT prompts stored in external `prompt.ninja` file for easy customization
- **Optional Cropping**: Face detection and vertical cropping can be applied optionally

This tool is currently in version 0.5 and might have some bugs.

If you wish to add shorts generation into your application, here is an api to create shorts from long form videos :- https://docs.vadoo.tv/docs/guide/create-ai-clips

### Youtube tutorial -> https://youtu.be/dKMueTMW1Nw

### Medium tutorial -> https://medium.com/@anilmatcha/ai-youtube-shorts-generator-in-python-a-complete-tutorial-c3df6523b362

![longshorts](https://github.com/user-attachments/assets/3f5d1abf-bf3b-475f-8abf-5e253003453a)

[Demo Input Video](https://github.com/SamurAIGPT/AI-Youtube-Shorts-Generator/blob/main/videos/Blinken%20Admires%20'Friend%20Jai'%20As%20Indian%20EAM%20Gets%20Savage%20In%20Munich%3B%20'I'm%20Smart%20Enough...'%20%7C%20Watch.mp4)

[Demo Output Video](https://github.com/SamurAIGPT/AI-Youtube-Shorts-Generator/blob/main/Final.mp4)

## Core Features

- **Video Input**: Supports both YouTube URLs and local video files (with relative/absolute path support).
- **Video Download**: Given a YouTube URL, the tool downloads the video.
- **Enhanced Transcription**: Uses Whisper with word-level timestamps and speaker diarization.
- **Individual Clip Generation**: Utilizes OpenAI's GPT-4 to identify engaging parts and create separate clips with titles.
- **Smart Titling**: AI generates descriptive, catchy titles for each clip.
- **Context Preservation**: Each clip maintains complete context and stands alone.
- **Precision Timing**: Word-level timestamp matching for exact clip boundaries.
- **Optional Face Detection**: Applies speaker detection and vertical cropping when requested.
- **Clips Summary**: Generates summary files with details about all created clips.

## Installation

### Prerequisites

- Python 3.7 or higher
- FFmpeg
- OpenCV

### Steps

1. Clone the repository:

   ```bash
   git clone https://github.com/SamurAIGPT/AI-Youtube-Shorts-Generator.git
   cd AI-Youtube-Shorts-Generator
   ```

2. Create a virtual environment

```bash
python3.10 -m venv venv
```

3. Activate a virtual environment:

```bash
source venv/bin/activate # On Windows: venv\Scripts\activate
```

4. Install the python dependencies:

```bash
pip install -r requirements.txt
```

---

1. Set up the environment variables.

Create a `.env` file in the project root directory and add your API configuration:

For OpenAI:

```bash
OPENAI_API=your_openai_api_key_here
HF_TOKEN=your_huggingface_token_here
```

For Azure OpenAI:

```bash
USE_AZURE_OPENAI=true
AZURE_OPENAI_KEY=your_azure_openai_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=your_deployment_name
HF_TOKEN=your_huggingface_token_here
```

**Note**: The `HF_TOKEN` is required for speaker diarization functionality. You can get a token from [Hugging Face Settings](https://huggingface.co/settings/tokens). You also need to accept the model license at [pyannote/speaker-diarization-3.1](https://huggingface.co/pyannote/speaker-diarization-3.1).

## Usage

1. Ensure your `.env` file is correctly set up with your OpenAI or Azure OpenAI API configuration.

2. Run the main script with one of the following options:

   **Option 1: Interactive Mode (Individual Clips by default)**

   ```bash
   python main.py
   ```

   You'll be prompted to enter either a YouTube URL or local video file path, and choose between individual clips or single-segment mode.

   **Option 2: Command Line with YouTube URL (Individual Clips)**

   ```bash
   python main.py "https://youtube.com/watch?v=VIDEO_ID"
   ```

   **Option 3: Command Line with Local Video File (Individual Clips)**

   ```bash
   python main.py "path/to/your/video.mp4"
   ```

   **Option 4: Single-Segment Mode (Legacy)**

   ```bash
   python main.py "https://youtube.com/watch?v=VIDEO_ID" --single-segment
   ```

   **Option 5: With Face Detection and Vertical Cropping**

   ```bash
   python main.py "path/to/video.mp4" --process-face-crop
   ```

   The tool automatically detects whether your input is a YouTube URL or a local file path. For local files, both relative and absolute paths are supported and will be converted to absolute paths automatically.

## Command Line Options

- `--single-segment`: Use the legacy single-segment mode instead of individual clips
- `--process-face-crop`: Apply face detection and vertical cropping to generated clips

## Individual Clips Mode vs Single-Segment Mode

### Individual Clips Mode (Default)

- Creates separate video files for each engaging segment
- Each clip has a descriptive title and filename
- Preserves original context in each clip
- Variable number of clips based on content quality
- Each clip under 60 seconds
- Better for creating multiple focused shorts from one video

### Single-Segment Mode (Legacy)

- Extracts one continuous segment from the video
- Preserves original video sequence
- Simpler processing with faster execution
- Good for videos with one clear highlight

## Command Line Options

- `--single-segment`: Use the legacy single-segment mode instead of multi-clip
- `--apply-cropping`: Apply face detection and vertical cropping to the generated clips

## Multi-Clip Mode vs Single-Segment Mode

### Multi-Clip Mode (Default)

- Extracts multiple engaging parts as separate video files
- Each clip gets an AI-generated title and descriptive filename
- Preserves original context for each segment
- Variable number of clips based on content quality
- Each clip under 60 seconds for optimal engagement
- Perfect for creating multiple shorts from one long video

### Single-Segment Mode (Legacy)

- Extracts one continuous segment from the video
- Preserves original video sequence
- Simpler processing with faster execution
- Good for videos with one clear highlight

## Customizing the AI Prompt

The AI prompt used to identify engaging segments is stored in `prompt.ninja` file in the project root. **This file is required** - the tool will exit with an error if it's not found.

**Creating your prompt file:**

- Copy an example: `cp prompt_examples/educational.ninja prompt.ninja`
- Or create your own custom prompt

**Example customizations:**

- Change the focus (educational vs entertainment vs news)
- Modify title requirements (length, style)
- Adjust selection criteria for your content type
- Change the priority ranking system

After editing `prompt.ninja`, the changes will be automatically used in the next run.

## Debugging and Analysis

### Transcription Files

The tool automatically saves Whisper transcriptions to `outputs/transcription/` folder for debugging and analysis:

- **`transcript_YYYYMMDD_HHMMSS.txt`**: Human-readable format showing exactly what gets sent to GPT
- **`transcript_YYYYMMDD_HHMMSS.json`**: Structured data with timestamps and segment durations
- **`transcript_YYYYMMDD_HHMMSS.srt`**: Subtitle format for viewing with video players

These files help you:

- Debug GPT performance and prompt effectiveness
- Analyze transcript quality and accuracy
- Review what content the AI is working with
- Fine-tune prompts based on actual transcription data

### Clips Summary

Each run generates `outputs/clips_summary.txt` with details about all generated clips including success/failure status, durations, and descriptions.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License.

## Disclaimer

This is a v0.2 release and might have some bugs. Please report any issues on the [GitHub Repository](https://github.com/SamurAIGPT/AI-Youtube-Shorts-Generator).

## Changelog

### v0.3

- **Major Change**: Switched from merged clips to individual clip generation
- Each engaging segment now creates a separate video file
- AI generates descriptive titles for each clip
- Smart filename generation based on clip titles
- Flexible number of clips based on content quality (no forced quantity)
- Each clip limited to under 60 seconds
- Added clips summary generation
- Made vertical cropping optional (--apply-cropping flag)
- Improved context preservation for each clip

## Changelog

### v0.3

- **Breaking Change**: Switched from merged multi-segment videos to individual clip generation
- Added AI-generated descriptive titles for each clip
- Implemented smart file naming based on clip titles
- Added context preservation - each clip stands alone
- Made face detection and vertical cropping optional
- Added clips summary generation
- Improved duration validation (clips under 60s)
- Enhanced prompt to focus on standalone content quality

### v0.2

- Added multi-segment processing (3-5 clips per short) - **Deprecated in v0.3**
- Implemented smart transitions between segments - **Deprecated in v0.3**
- Added flow optimization for better narrative structure - **Deprecated in v0.3**
- Introduced priority-based segment selection
- Added command-line options for mode selection and duration control
- Externalized GPT prompts to `prompt.ninja` file for easy customization
- Maintained backward compatibility with single-segment mode

### v0.1

- Initial release with single-segment processing

### Other useful Video AI Projects

[AI Influencer generator](https://github.com/SamurAIGPT/AI-Influencer-Generator)

[Text to Video AI](https://github.com/SamurAIGPT/Text-To-Video-AI)

[Faceless Video Generator](https://github.com/SamurAIGPT/Faceless-Video-Generator)

[AI B-roll generator](https://github.com/Anil-matcha/AI-B-roll)

[No-code AI Youtube Shorts Generator](https://www.vadoo.tv/clip-youtube-video)

[Sora AI Video Generator](https://www.vadoo.tv/sora-ai-video-generator)
