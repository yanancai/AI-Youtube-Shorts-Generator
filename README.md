# AI Youtube Shorts Generator

AI Youtube Shorts Generator is a Python tool designed to generate engaging YouTube shorts from long-form videos. By leveraging the power of GPT-4 and Whisper, it extracts the most interesting highlights, detects speakers, and crops the content vertically for shorts. The tool supports both YouTube URLs and local video files (with relative/absolute path support). This tool is currently in version 0.1 and might have some bugs.

If you wish to add shorts generation into your application, here is an api to create shorts from long form videos :- https://docs.vadoo.tv/docs/guide/create-ai-clips

### Youtube tutorial -> https://youtu.be/dKMueTMW1Nw

### Medium tutorial -> https://medium.com/@anilmatcha/ai-youtube-shorts-generator-in-python-a-complete-tutorial-c3df6523b362

![longshorts](https://github.com/user-attachments/assets/3f5d1abf-bf3b-475f-8abf-5e253003453a)

[Demo Input Video](https://github.com/SamurAIGPT/AI-Youtube-Shorts-Generator/blob/main/videos/Blinken%20Admires%20'Friend%20Jai'%20As%20Indian%20EAM%20Gets%20Savage%20In%20Munich%3B%20'I'm%20Smart%20Enough...'%20%7C%20Watch.mp4)

[Demo Output Video](https://github.com/SamurAIGPT/AI-Youtube-Shorts-Generator/blob/main/Final.mp4)

## Features

- **Video Input**: Supports both YouTube URLs and local video files (with relative/absolute path support).
- **Video Download**: Given a YouTube URL, the tool downloads the video.
- **Transcription**: Uses Whisper to transcribe the video.
- **Highlight Extraction**: Utilizes OpenAI's GPT-4 to identify the most engaging parts of the video.
- **Speaker Detection**: Detects speakers in the video.
- **Vertical Cropping**: Crops the highlighted sections vertically, making them perfect for shorts.

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
```

For Azure OpenAI:

```bash
USE_AZURE_OPENAI=true
AZURE_OPENAI_KEY=your_azure_openai_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=your_deployment_name
```

## Usage

1. Ensure your `.env` file is correctly set up with your OpenAI or Azure OpenAI API configuration.

2. Run the main script with one of the following options:

   **Option 1: Interactive Mode**

   ```bash
   python main.py
   ```

   You'll be prompted to enter either a YouTube URL or local video file path.

   **Option 2: Command Line with YouTube URL**

   ```bash
   python main.py "https://youtube.com/watch?v=VIDEO_ID"
   ```

   **Option 3: Command Line with Local Video File**

   ```bash
   python main.py "path/to/your/video.mp4"
   ```

   The tool automatically detects whether your input is a YouTube URL or a local file path. For local files, both relative and absolute paths are supported and will be converted to absolute paths automatically.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License.

## Disclaimer

This is a v0.1 release and might have some bugs. Please report any issues on the [GitHub Repository](https://github.com/SamurAIGPT/AI-Youtube-Shorts-Generator).

### Other useful Video AI Projects

[AI Influencer generator](https://github.com/SamurAIGPT/AI-Influencer-Generator)

[Text to Video AI](https://github.com/SamurAIGPT/Text-To-Video-AI)

[Faceless Video Generator](https://github.com/SamurAIGPT/Faceless-Video-Generator)

[AI B-roll generator](https://github.com/Anil-matcha/AI-B-roll)

[No-code AI Youtube Shorts Generator](https://www.vadoo.tv/clip-youtube-video)

[Sora AI Video Generator](https://www.vadoo.tv/sora-ai-video-generator)
