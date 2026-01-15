# Translation Studio 🎬

Professional desktop application for translating videos, audio files, and SRT subtitles to Arabic. Supports multiple translation engines including offline options.

**Made by Mahmoud Gado**

## Features

✨ **Multiple Translation Modes**
- **Video/Audio → Arabic SRT** using OpenAI Whisper (offline transcription + translation)
- **SRT → Arabic** using Argos Translate (completely offline)
- **SRT → Arabic** using ChatGPT API (online, highest quality)

🚀 **Key Capabilities**
- Extract audio from video files and transcribe using Whisper
- Convert transcriptions to SRT subtitle format
- Preserve code snippets and technical terms during translation
- Support for multiple video formats (MP4, MKV, AVI, MOV, WebM)
- Real-time progress tracking and logging
- Batch processing with multiple AI models

🔧 **Supported Engines**
1. **OpenAI Whisper** - Offline speech-to-text (multiple model sizes)
2. **Argos Translate** - Offline neural machine translation
3. **ChatGPT API** - Online high-quality translation (gpt-4, gpt-4-turbo, gpt-4o, etc.)

## Requirements

### System Requirements
- Python 3.10
- FFmpeg (for video/audio processing)
- 8GB RAM recommended
- CUDA-compatible GPU (optional, for faster processing)

### Installation Steps

#### 1. Install FFmpeg

**Windows:**
```bash
# Using Chocolatey
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install ffmpeg
```

#### 2. Clone or Download the Repository
```bash
git clone https://github.com/yourusername/translation-studio.git
cd translation-studio
```

#### 3. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

#### 4. Install Python Dependencies
```bash
pip install -r requirements.txt
```

#### 5. (Optional) Configure OpenAI API Key
If using ChatGPT for translation:
- Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
- You can input it in the application GUI or set it as an environment variable

## Usage

### Running the Application
```bash
python main.py
```

### Translation Workflows

#### Option 1: Translate Video to Arabic SRT (Whisper)
1. Click "Select Video File"
2. Choose your video file (MP4, MKV, AVI, MOV, WebM)
3. Select Whisper model size (medium or large)
4. Wait for transcription and translation to complete
5. Output: `your_video.ar.srt`

**Requirements:** Whisper (comes with requirements.txt)

#### Option 2: Translate SRT with Argos (Offline)
1. Click "Select SRT File (Argos)"
2. Choose your English SRT file
3. Wait for translation to complete
4. Output: `your_file.ar.srt`

**Requirements:** Argos Translate (fully offline)
**No internet required after installation**

#### Option 3: Translate SRT with ChatGPT (Online)
1. Enter your OpenAI API key in the text field
2. Click "Select SRT File (ChatGPT)"
3. Choose your SRT file
4. Select ChatGPT model (gpt-4, gpt-4-turbo, gpt-4o, etc.)
5. Wait for translation
6. Output: `your_file.ar.srt`

**Requirements:** OpenAI API key with available credits

## Docker Setup

### Build Docker Image
```bash
docker build -t translation-studio .
```

### Run with Docker
```bash
# With GPU support (NVIDIA)
docker run --gpus all \
  -v $(pwd)/videos:/app/videos \
  -v $(pwd)/output:/app/output \
  -e OPENAI_API_KEY=your_key_here \
  translation-studio

# Without GPU
docker run \
  -v $(pwd)/videos:/app/videos \
  -v $(pwd)/output:/app/output \
  -e OPENAI_API_KEY=your_key_here \
  translation-studio
```

### Docker Compose
```bash
docker-compose up
```

## Configuration

### Environment Variables
```bash
# OpenAI API Key (for ChatGPT translation)
export OPENAI_API_KEY="sk-..."

# Whisper Model Size (tiny, base, small, medium, large)
export WHISPER_MODEL="medium"
```

## File Format Support

### Input Formats
- **Video:** MP4, MKV, AVI, MOV, WebM
- **Audio:** WAV, MP3, M4A, FLAC
- **Subtitles:** SRT (SubRip format)

### Output Format
- **Subtitles:** SRT (SubRip) with Arabic text

## Model Information

### Whisper Models
- **tiny:** Fastest, ~39M params (recommended for quick processing)
- **base:** Balanced, ~74M params
- **small:** Better accuracy, ~244M params
- **medium:** Good accuracy, ~769M params (default)
- **large:** Best accuracy, ~1550M params

### ChatGPT Models
- **gpt-4-turbo:** Recommended for production
- **gpt-4:** More accurate but slower
- **gpt-4o:** Latest multimodal model
- **gpt-4o-mini:** Fast, cost-effective
- **gpt-3.5-turbo:** Fast but less accurate

## Code Protection

The application intelligently protects code snippets and technical terms:
- Preserves function names, variables, and code syntax
- Detects and skips programming language keywords
- Maintains URL and file path integrity
- Protects command-line syntax

## Performance Tips

1. **For faster processing:** Use the "tiny" or "base" Whisper model
2. **For better accuracy:** Use "medium" or "large" Whisper model
3. **For best translation quality:** Use ChatGPT (gpt-4-turbo or gpt-4o)
4. **For offline translation:** Use Argos Translate (no API key needed)
5. **GPU acceleration:** Install CUDA-compatible PyTorch for 3-5x speedup

## Troubleshooting

### FFmpeg not found
```bash
# Windows: Add FFmpeg to PATH
# macOS: brew install ffmpeg
# Linux: sudo apt-get install ffmpeg
```

### Whisper model download issues
```bash
# Manual model download
python -c "import whisper; whisper.load_model('medium')"
```

### API Key not working
- Verify API key from [OpenAI Platform](https://platform.openai.com/api-keys)
- Check that your account has available credits
- Ensure API key has permissions for chat.completions

### Out of memory errors
- Use smaller Whisper model (tiny or base)
- Close other applications
- Use GPU acceleration if available

### Translation not working
- Verify internet connection (for ChatGPT)
- Ensure language packages downloaded (Argos)
- Check SRT file format is correct

## Output Files

After successful translation, you'll find:
- `your_file.ar.srt` - Arabic subtitle file with timestamps

## Security Notes

- API keys are never stored or logged
- Local files remain on your machine
- Argos Translate works completely offline
- No telemetry or data collection

## Limitations

- Maximum subtitle file size: Depends on API rate limits (ChatGPT)
- Offline translation (Argos) may be less accurate than ChatGPT
- Video formats depend on FFmpeg availability

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is provided as-is for personal and educational use.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Verify all dependencies are installed
3. Ensure FFmpeg is in your system PATH

## Credits

**Made by Mahmoud Gado**

Built with:
- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition
- [Argos Translate](https://www.argosopentech.com/) - Neural translation
- [OpenAI API](https://openai.com/api/) - ChatGPT integration
- [PySide6](https://wiki.qt.io/Qt_for_Python) - GUI framework

## Changelog

### v1.0.0 (2026-01-15)
- Initial release
- Whisper integration for video transcription
- Argos Translate for offline translation
- ChatGPT API integration
- Code protection and technical term preservation
- Real-time progress tracking
