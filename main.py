"""
Desktop Application for Translating Videos/Audio and SRT Subtitles
Supports: Whisper (Offline), Argos Translate (Offline), ChatGPT (Online)

Author: AI Assistant
Date: 2026
"""

import sys
import os
import re
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple

from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QFileDialog, QProgressBar, QComboBox, QLineEdit, QTextEdit
)
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QFont

# Try importing optional libraries with graceful fallbacks
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    from argostranslate import translate, package
    ARGOS_AVAILABLE = True
except ImportError:
    ARGOS_AVAILABLE = False

try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# ===================== UTILITIES =====================

class SRTParser:
    """Parse and format SRT subtitle files."""

    @staticmethod
    def parse(content: str) -> List[Dict[str, str]]:
        """Parse SRT content into subtitle blocks."""
        blocks = content.strip().split('\n\n')
        subtitles = []

        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                try:
                    subtitles.append({
                        'index': lines[0].strip(),
                        'timestamp': lines[1].strip(),
                        'text': '\n'.join(lines[2:]).strip()
                    })
                except Exception:
                    pass

        return subtitles

    @staticmethod
    def format(subtitles: List[Dict[str, str]]) -> str:
        """Format subtitles back to SRT content."""
        output = []
        for sub in subtitles:
            output.append(sub['index'])
            output.append(sub['timestamp'])
            output.append(sub['text'])
            output.append('')  # Empty line between blocks
        return '\n'.join(output).strip() + '\n'


class CodeDetector:
    """Detect and protect code snippets and technical terms."""

    PATTERNS = [
        r"[{}();<>[\]|]",  # Code brackets
        r"\b(def|class|function|return|if|else|for|while|try|except|import|from|async|await)\b",
        r"=>\s*|::\s*",  # Arrow functions, scope resolution
        r"\w+\.\w+\(",  # Method calls
        r"console\.|print\(|log\(",  # Console/print statements
        r"^\s*#|^\s*//",  # Comments
        r"\$\w+|\b\w+\s*=\s*",  # Variables
        r"`[^`]+`",  # Code blocks
    ]

    @staticmethod
    def is_code_or_technical(text: str) -> bool:
        """Check if text contains code or technical terms."""
        if not text.strip():
            return False
        
        for pattern in CodeDetector.PATTERNS:
            if re.search(pattern, text):
                return True
        return False


class FFmpegHandler:
    """Handle FFmpeg operations for audio extraction."""

    @staticmethod
    def is_available() -> bool:
        """Check if FFmpeg is installed and accessible."""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                check=False,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def extract_audio(video_path: str, output_audio_path: str) -> bool:
        """Extract audio from video using FFmpeg."""
        try:
            video_path = os.path.abspath(video_path)
            output_audio_path = os.path.abspath(output_audio_path)

            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")

            # Check if FFmpeg is available
            if not FFmpegHandler.is_available():
                raise RuntimeError(
                    "FFmpeg not found. Please install it:\n"
                    "Windows: Download from https://ffmpeg.org/download.html\n"
                    "Add to PATH or install via: choco install ffmpeg\n"
                    "Then restart your terminal."
                )

            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output file
                '-i', video_path,
                '-ar', '16000',  # Sample rate for Whisper
                '-ac', '1',  # Mono audio
                output_audio_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=600  # 10 minute timeout
            )

            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg error: {result.stderr}")

            if not os.path.exists(output_audio_path):
                raise RuntimeError("Audio extraction failed: output file not created")

            return True

        except Exception as e:
            raise Exception(f"Audio extraction failed: {str(e)}")


# ===================== TRANSLATION THREADS =====================

class WhisperTranslateThread(QThread):
    """Translate video/audio to Arabic SRT using Whisper (Offline)."""
    
    status_update = Signal(str)
    progress_update = Signal(int)
    translation_finished = Signal(str)

    def __init__(self, video_path: str, model: str = "medium"):
        super().__init__()
        self.video_path = video_path
        self.model_name = model
        self.model = None

    def run(self):
        """Execute translation in background."""
        try:
            if not WHISPER_AVAILABLE:
                self.translation_finished.emit("Error: Whisper not installed. Run: pip install openai-whisper")
                return

            self.status_update.emit("Loading Whisper model...")
            self.progress_update.emit(10)
            self.model = whisper.load_model(self.model_name)

            # Extract audio from video
            self.status_update.emit("Extracting audio from video...")
            self.progress_update.emit(20)

            audio_path = os.path.splitext(self.video_path)[0] + "_temp_audio.wav"
            FFmpegHandler.extract_audio(self.video_path, audio_path)

            try:
                # Transcribe with Whisper
                self.status_update.emit("Transcribing audio with Whisper...")
                self.progress_update.emit(40)

                result = self.model.transcribe(
                    audio_path,
                    language="en",
                    task="transcribe"
                )

                # Convert Whisper output to SRT format and translate to Arabic
                self.status_update.emit("Converting to SRT and translating to Arabic...")
                self.progress_update.emit(50)

                srt_content = self._format_whisper_output(result)
                
                # Parse the SRT content to get segments
                subtitles = SRTParser.parse(srt_content)
                total = len(subtitles)

                if total > 0:
                    self.status_update.emit(f"Translating {total} segments to Arabic...")
                    self.progress_update.emit(60)
                    
                    # Translate each subtitle to Arabic using Argos if available
                    if ARGOS_AVAILABLE:
                        try:
                            # Try to ensure language packages are downloaded
                            try:
                                package.update_package_index()
                            except Exception:
                                pass  # Ignore if this fails
                            
                            for i, subtitle in enumerate(subtitles):
                                if not CodeDetector.is_code_or_technical(subtitle['text']):
                                    try:
                                        translated = translate.translate(subtitle['text'], "en", "ar")
                                        subtitle['text'] = translated
                                    except Exception as e:
                                        # Keep original if translation fails
                                        pass
                                
                                progress = 60 + int((i + 1) / total * 20)
                                self.progress_update.emit(progress)
                        except Exception as e:
                            self.status_update.emit(f"⚠ Translation to Arabic unavailable: {str(e)}")
                    else:
                        self.status_update.emit("⚠ Argos Translate not installed. Subtitles will remain in English.")
                        self.status_update.emit("   Run: pip install argostranslate")
                    
                    srt_content = SRTParser.format(subtitles)

                # Save SRT file
                self.status_update.emit("Saving SRT file...")
                self.progress_update.emit(90)

                output_path = os.path.splitext(self.video_path)[0] + ".ar.srt"
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(srt_content)

                self.progress_update.emit(100)
                self.translation_finished.emit(f"✓ Done: {os.path.basename(output_path)}")

            finally:
                # Cleanup temporary audio file
                if os.path.exists(audio_path):
                    os.remove(audio_path)

        except Exception as e:
            self.translation_finished.emit(f"✗ Error: {str(e)}")

    @staticmethod
    def _format_whisper_output(result: Dict) -> str:
        """Convert Whisper JSON output to SRT format."""
        srt_lines = []
        index = 1

        for segment in result.get('segments', []):
            start_time = WhisperTranslateThread._seconds_to_srt_time(segment['start'])
            end_time = WhisperTranslateThread._seconds_to_srt_time(segment['end'])
            text = segment['text'].strip()

            if text:
                srt_lines.append(str(index))
                srt_lines.append(f"{start_time} --> {end_time}")
                srt_lines.append(text)
                srt_lines.append('')
                index += 1

        return '\n'.join(srt_lines)

    @staticmethod
    def _seconds_to_srt_time(seconds: float) -> str:
        """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


class ArgosTranslateThread(QThread):
    """Translate SRT to Arabic using Argos Translate (Offline)."""
    
    status_update = Signal(str)
    progress_update = Signal(int)
    translation_finished = Signal(str)

    def __init__(self, srt_path: str):
        super().__init__()
        self.srt_path = srt_path

    def run(self):
        """Execute translation in background."""
        try:
            if not ARGOS_AVAILABLE:
                self.translation_finished.emit("Error: Argos Translate not installed. Run: pip install argostranslate")
                return

            self.status_update.emit("Preparing language packages...")
            self.progress_update.emit(10)

            # Try to ensure language packages are available
            try:
                package.update_package_index()
            except Exception:
                pass  # Ignore if this fails

            self.status_update.emit("Reading SRT file...")
            self.progress_update.emit(20)

            with open(self.srt_path, 'r', encoding='utf-8') as f:
                content = f.read()

            subtitles = SRTParser.parse(content)
            total = len(subtitles)

            if total == 0:
                self.translation_finished.emit("✗ Error: No subtitles found in file")
                return

            self.status_update.emit(f"Translating {total} subtitles...")
            self.progress_update.emit(30)

            # Translate each subtitle
            for i, subtitle in enumerate(subtitles):
                if not CodeDetector.is_code_or_technical(subtitle['text']):
                    try:
                        translated = translate.translate(subtitle['text'], "en", "ar")
                        subtitle['text'] = translated
                    except Exception as e:
                        # Keep original if translation fails
                        pass

                progress = 30 + int((i + 1) / total * 70)
                self.progress_update.emit(progress)

            # Save translated SRT
            output_path = self.srt_path.replace('.srt', '.ar.srt')
            output_content = SRTParser.format(subtitles)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_content)

            self.progress_update.emit(100)
            self.translation_finished.emit(f"✓ Done: {os.path.basename(output_path)}")

        except Exception as e:
            self.translation_finished.emit(f"✗ Error: {str(e)}")


class ChatGPTTranslateThread(QThread):
    """Translate SRT to Arabic using ChatGPT API (Online)."""
    
    status_update = Signal(str)
    progress_update = Signal(int)
    translation_finished = Signal(str)

    SYSTEM_PROMPT = """You are a professional technical translator specializing in programming tutorials and documentation.
Your task is to translate subtitle text from English to Arabic with these rules:

1. PRESERVE all code snippets, function names, variable names, and technical terms in English
2. Preserve URLs, file paths, and command-line syntax
3. Translate ONLY natural language explanations and descriptions to Arabic
4. Maintain the context and meaning accurately
5. Keep the translation concise and suitable for subtitles
6. Never modify timestamps, numbering, or formatting markers

Output ONLY the translated text, nothing else."""

    def __init__(self, srt_path: str, api_key: str, model: str = "gpt-4-turbo"):
        super().__init__()
        self.srt_path = srt_path
        self.api_key = api_key
        self.model = model
        self.translated_count = 0
        self.skipped_count = 0

    def run(self):
        """Execute translation in background."""
        try:
            if not OPENAI_AVAILABLE:
                self.translation_finished.emit("Error: OpenAI library not installed. Run: pip install openai")
                return

            if not self.api_key or self.api_key.strip() == "":
                self.translation_finished.emit("✗ Error: OpenAI API key not provided")
                return

            # Initialize OpenAI client with API key
            client = OpenAI(api_key=self.api_key)

            self.status_update.emit("Reading SRT file...")
            self.progress_update.emit(10)

            with open(self.srt_path, 'r', encoding='utf-8') as f:
                content = f.read()

            subtitles = SRTParser.parse(content)
            total = len(subtitles)

            if total == 0:
                self.translation_finished.emit("✗ Error: No subtitles found in file")
                return

            self.status_update.emit(f"Translating {total} subtitles with ChatGPT...")
            self.progress_update.emit(20)
            self.translated_count = 0
            self.skipped_count = 0

            # Translate each subtitle
            for i, subtitle in enumerate(subtitles):
                text_to_translate = subtitle['text'].strip()
                
                # Skip if text is empty or is pure code/technical
                if not text_to_translate:
                    self.skipped_count += 1
                elif CodeDetector.is_code_or_technical(text_to_translate):
                    self.skipped_count += 1
                else:
                    try:
                        # Call ChatGPT with modern API
                        response = client.chat.completions.create(
                            model=self.model,
                            messages=[
                                {"role": "system", "content": self.SYSTEM_PROMPT},
                                {"role": "user", "content": text_to_translate}
                            ],
                            temperature=0.3,
                            max_tokens=500
                        )
                        
                        if response.choices and len(response.choices) > 0:
                            translated = response.choices[0].message.content.strip()
                            if translated:
                                subtitle['text'] = translated
                                self.translated_count += 1
                            else:
                                self.skipped_count += 1
                        else:
                            self.skipped_count += 1
                            
                    except Exception as e:
                        error_msg = str(e)
                        # Provide helpful error diagnostics
                        if "model_not_found" in error_msg or "does not have access" in error_msg:
                            self.status_update.emit(f"⚠ Model '{self.model}' not available. Try: gpt-4, gpt-4-turbo, gpt-4o, gpt-4o-mini")
                        else:
                            self.status_update.emit(f"⚠ API Error: {error_msg[:100]}")
                        self.skipped_count += 1

                progress = 20 + int((i + 1) / total * 75)
                self.progress_update.emit(progress)

            # Save translated SRT
            self.status_update.emit("Saving translated file...")
            self.progress_update.emit(95)
            
            output_path = self.srt_path.replace('.srt', '.ar.srt')
            output_content = SRTParser.format(subtitles)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_content)

            self.progress_update.emit(100)
            summary = f"✓ Done: {os.path.basename(output_path)} (Translated: {self.translated_count}, Skipped: {self.skipped_count})"
            self.translation_finished.emit(summary)

        except Exception as e:
            self.translation_finished.emit(f"✗ Error: {str(e)}")


# ===================== GUI APPLICATION =====================

class TranslatorApp(QWidget):
    """Main GUI application for translation."""

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.thread = None

    def init_ui(self):
        """Initialize UI components."""
        self.setWindowTitle("Translation Studio - Video/Audio/SRT to Arabic")
        self.setGeometry(100, 100, 550, 750)

        main_layout = QVBoxLayout()

        # ===== Header with Author =====
        header_label = QLabel("Translation Studio")
        header_label.setFont(QFont("Arial", 14, QFont.Bold))
        main_layout.addWidget(header_label)
        
        author_label = QLabel("Made by Mahmoud Gado")
        author_label.setFont(QFont("Arial", 9))
        author_label.setStyleSheet("color: gray;")
        main_layout.addWidget(author_label)
        
        separator = QLabel("─" * 60)
        main_layout.addWidget(separator)

        # ===== Video Translation Section =====
        video_title = QLabel("🎥 VIDEO/AUDIO TRANSLATION (Whisper - Offline)")
        video_title.setFont(QFont("Arial", 11, QFont.Bold))
        main_layout.addWidget(video_title)

        video_layout = QHBoxLayout()
        self.video_btn = QPushButton("Select Video File")
        self.video_btn.clicked.connect(self.select_video)
        self.video_model_combo = QComboBox()
        self.video_model_combo.addItems(["medium", "large"])
        video_layout.addWidget(self.video_btn)
        video_layout.addWidget(QLabel("Model:"))
        video_layout.addWidget(self.video_model_combo)
        main_layout.addLayout(video_layout)

        # ===== SRT Translation Section - Argos =====
        srt_argos_title = QLabel("📝 SRT TRANSLATION - OFFLINE (Argos Translate)")
        srt_argos_title.setFont(QFont("Arial", 11, QFont.Bold))
        main_layout.addWidget(srt_argos_title)

        self.srt_argos_btn = QPushButton("Select SRT File (Argos)")
        self.srt_argos_btn.clicked.connect(self.select_srt_argos)
        main_layout.addWidget(self.srt_argos_btn)

        # ===== SRT Translation Section - ChatGPT =====
        srt_chatgpt_title = QLabel("📝 SRT TRANSLATION - ONLINE (ChatGPT)")
        srt_chatgpt_title.setFont(QFont("Arial", 11, QFont.Bold))
        main_layout.addWidget(srt_chatgpt_title)

        srt_chatgpt_layout = QHBoxLayout()
        self.srt_chatgpt_btn = QPushButton("Select SRT File (ChatGPT)")
        self.srt_chatgpt_btn.clicked.connect(self.select_srt_chatgpt)
        self.chatgpt_model_combo = QComboBox()
        self.chatgpt_model_combo.addItems(["gpt-4-turbo", "gpt-4", "gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini"])
        srt_chatgpt_layout.addWidget(self.srt_chatgpt_btn)
        srt_chatgpt_layout.addWidget(QLabel("Model:"))
        srt_chatgpt_layout.addWidget(self.chatgpt_model_combo)
        main_layout.addLayout(srt_chatgpt_layout)

        # API Key input
        self.api_key_label = QLabel("OpenAI API Key:")
        main_layout.addWidget(self.api_key_label)
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("sk-...")
        main_layout.addWidget(self.api_key_input)

        # ===== Progress and Status =====
        separator = QLabel("─" * 60)
        main_layout.addWidget(separator)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        main_layout.addWidget(self.progress)

        self.status_label = QLabel("Status: Idle")
        self.status_label.setFont(QFont("Courier", 10))
        main_layout.addWidget(self.status_label)

        # Log area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(150)
        self.log_area.setPlaceholderText("Translation logs will appear here...")
        main_layout.addWidget(self.log_area)

        self.setLayout(main_layout)

    def select_video(self):
        """Select video file for Whisper translation."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Video File",
            "",
            "Video Files (*.mp4 *.mkv *.avi *.mov *.webm);;All Files (*)"
        )

        if file_path:
            model = self.video_model_combo.currentText()
            self.log_area.append(f"[Video] Selected: {os.path.basename(file_path)}")
            self.log_area.append(f"[Video] Model: {model}")
            self.disable_ui()
            self.thread = WhisperTranslateThread(file_path, model)
            self.thread.status_update.connect(self.update_status)
            self.thread.progress_update.connect(self.update_progress)
            self.thread.translation_finished.connect(self.on_translation_finished)
            self.thread.start()

    def select_srt_argos(self):
        """Select SRT file for Argos translation."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select SRT File",
            "",
            "SRT Files (*.srt);;All Files (*)"
        )

        if file_path:
            self.log_area.append(f"[Argos] Selected: {os.path.basename(file_path)}")
            self.disable_ui()
            self.thread = ArgosTranslateThread(file_path)
            self.thread.status_update.connect(self.update_status)
            self.thread.progress_update.connect(self.update_progress)
            self.thread.translation_finished.connect(self.on_translation_finished)
            self.thread.start()

    def select_srt_chatgpt(self):
        """Select SRT file for ChatGPT translation."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select SRT File",
            "",
            "SRT Files (*.srt);;All Files (*)"
        )

        if file_path:
            api_key = self.api_key_input.text().strip()
            if not api_key:
                self.log_area.append("[ChatGPT] ✗ Error: API key not provided")
                return

            model = self.chatgpt_model_combo.currentText()
            self.log_area.append(f"[ChatGPT] Selected: {os.path.basename(file_path)}")
            self.log_area.append(f"[ChatGPT] Model: {model}")
            self.disable_ui()
            self.thread = ChatGPTTranslateThread(file_path, api_key, model)
            self.thread.status_update.connect(self.update_status)
            self.thread.progress_update.connect(self.update_progress)
            self.thread.translation_finished.connect(self.on_translation_finished)
            self.thread.start()

    def disable_ui(self):
        """Disable UI during translation."""
        self.video_btn.setEnabled(False)
        self.video_model_combo.setEnabled(False)
        self.srt_argos_btn.setEnabled(False)
        self.srt_chatgpt_btn.setEnabled(False)
        self.api_key_input.setEnabled(False)
        self.progress.setValue(0)

    def enable_ui(self):
        """Enable UI after translation."""
        self.video_btn.setEnabled(True)
        self.video_model_combo.setEnabled(True)
        self.srt_argos_btn.setEnabled(True)
        self.srt_chatgpt_btn.setEnabled(True)
        self.api_key_input.setEnabled(True)

    def update_status(self, status: str):
        """Update status label."""
        self.status_label.setText(f"Status: {status}")
        self.log_area.append(f"➜ {status}")

    def update_progress(self, value: int):
        """Update progress bar."""
        self.progress.setValue(value)

    def on_translation_finished(self, message: str):
        """Handle translation completion."""
        self.status_label.setText(message)
        self.log_area.append(f"\n{message}\n")
        self.progress.setValue(100)
        self.enable_ui()


# ===================== MAIN =====================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TranslatorApp()
    window.show()
    sys.exit(app.exec())