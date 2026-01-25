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
    QFileDialog, QProgressBar, QComboBox, QLineEdit, QTextEdit, QListWidget,
    QListWidgetItem, QSpinBox, QTabWidget, QCheckBox
)
from PySide6.QtCore import QThread, Signal, Qt, QTimer
from PySide6.QtGui import QFont, QColor

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

# Import batch processing modules
from batch_processor import TranslationEngineType, TranslationStatus, TranslationJob
from simple_batch import SimpleBatchProcessor


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
        r"[{}<>[\]|]",  # Code brackets (removed () as they are common in text)
        r"\b(def|function|async|await|const|var|val|let)\b",  # Strict keywords only
        r"=>\s*|::\s*",  # Arrow functions, scope resolution
        r"(console\.|print\(|log\()",  # Console/print statements
        r"^\s*#|^\s*//",  # Comments
        r"\$\w+",  # Variables (removed generic assignment to avoid false positives)
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


class TranslationValidator:
    """Validate that all subtitles have been properly translated."""

    @staticmethod
    def validate_translation(subtitles: List[Dict[str, str]], original_subtitles: List[Dict[str, str]]) -> Dict:
        """
        Validate translation quality and completeness.
        
        Args:
            subtitles: Translated subtitles
            original_subtitles: Original subtitles (before translation)
            
        Returns:
            Validation report with issues found
        """
        report = {
            "total": len(subtitles),
            "empty": 0,
            "unchanged": 0,
            "issues": []
        }
        
        if len(subtitles) != len(original_subtitles):
            report["issues"].append(f"Subtitle count mismatch: {len(original_subtitles)} original vs {len(subtitles)} translated")
        
        for i, (trans, orig) in enumerate(zip(subtitles, original_subtitles)):
            # Check for empty translations
            if not trans['text'].strip():
                report["empty"] += 1
                report["issues"].append(f"Subtitle {i+1}: Empty translation")
            
            # Check if translation is identical to original (likely untranslated)
            elif trans['text'].strip() == orig['text'].strip():
                report["unchanged"] += 1
        
        return report
    
    @staticmethod
    def report_validation(report: Dict) -> str:
        """Generate human-readable validation report."""
        msg = f"Translation Validation Report:\n"
        msg += f"  Total subtitles: {report['total']}\n"
        msg += f"  Empty translations: {report['empty']}\n"
        msg += f"  Unchanged from original: {report['unchanged']}\n"
        
        if report["issues"]:
            msg += f"\nIssues found ({len(report['issues'])}):\n"
            for issue in report["issues"][:10]:  # Show first 10 issues
                msg += f"  - {issue}\n"
            if len(report["issues"]) > 10:
                msg += f"  ... and {len(report['issues']) - 10} more issues\n"
        
        return msg


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
                '-y',
                '-err_detect', 'ignore_err',  # Ignore decoding errors
                '-i', video_path,
                '-vn',
                '-ar', '16000',
                '-af', 'pan=mono|c0=c0',  # Force use of first channel only
                '-c:a', 'pcm_s16le',
                '-ac', '1',
                output_audio_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=3600  # 1 hour timeout for large files
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

    def __init__(self, video_path: str, model: str = "medium", extract_only: bool = False):
        super().__init__()
        self.video_path = video_path
        self.model_name = model
        self.extract_only = extract_only
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
                # Configure Whisper task based on mode
                if self.extract_only:
                    # Original language extraction (Auto-detect language)
                    transcribe_options = {"task": "transcribe"}
                    self.status_update.emit("Transcribing audio (Auto-detecting language)...")
                else:
                    # Translate to English first (Whisper only translates to English), then Argos does En->Ar
                    transcribe_options = {"task": "translate"}
                    self.status_update.emit("Transcribing and translating to English (for conversion)...")

                result = self.model.transcribe(
                    audio_path,
                    **transcribe_options
                )

                # Convert Whisper output to SRT format and translate to Arabic
                self.status_update.emit("Converting to SRT and translating to Arabic...")
                self.progress_update.emit(50)

                srt_content = self._format_whisper_output(result)
                
                # Parse the SRT content to get segments
                subtitles = SRTParser.parse(srt_content)
                total = len(subtitles)

                if total > 0:
                    if self.extract_only:
                        self.status_update.emit(f"✓ Extracted {total} segments (Original Language)")
                        self.progress_update.emit(80)
                    else:
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
                                
                                translated_count = 0
                                for i, subtitle in enumerate(subtitles):
                                    if not CodeDetector.is_code_or_technical(subtitle['text']):
                                        try:
                                            original_text = subtitle['text']
                                            translated = translate.translate(subtitle['text'], "en", "ar")
                                            # Validate that translation is not empty
                                            if translated and len(translated.strip()) > 0:
                                                subtitle['text'] = translated
                                                translated_count += 1
                                            else:
                                                # Keep original if translation resulted in empty text
                                                self.status_update.emit(f"⚠ Subtitle {i+1}: Translation resulted in empty, kept original")
                                        except Exception as e:
                                            # Keep original if translation fails
                                            self.status_update.emit(f"⚠ Subtitle {i+1} translation error: {str(e)[:50]}")
                                    
                                    progress = 60 + int((i + 1) / total * 20)
                                    self.progress_update.emit(progress)
                                self.status_update.emit(f"✓ Translated {translated_count}/{total} subtitles to Arabic")
                            except Exception as e:
                                self.status_update.emit(f"⚠ Translation to Arabic unavailable: {str(e)}")
                        else:
                            self.status_update.emit("⚠ Argos Translate not installed. Subtitles will remain in English.")
                            self.status_update.emit("   Run: pip install argostranslate")
                        
                        srt_content = SRTParser.format(subtitles)

                # Save SRT file
                self.status_update.emit("Saving SRT file...")
                self.progress_update.emit(90)

                # Get detected language if available
                detected_lang = result.get('language', 'original')
                
                # Output filename logic:
                # If extract_only: use detected language (e.g. "video en.srt", "video fr.srt")
                # If translation: forced to "ar" (e.g. "video ar.srt")
                suffix = detected_lang if self.extract_only else "ar"
                
                # Create 'subs' folder if it doesn't exist
                source_dir = os.path.dirname(self.video_path)
                output_dir = os.path.join(source_dir, "subs")
                os.makedirs(output_dir, exist_ok=True)
                
                base_name = os.path.splitext(os.path.basename(self.video_path))[0]
                output_path = os.path.join(output_dir, f"{base_name} {suffix}.srt")

                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(srt_content)

                self.progress_update.emit(100)
                translated_segments = SRTParser.parse(srt_content)
                # Count translated segments (non-empty)
                translated_count = sum(1 for s in translated_segments if s['text'].strip())
                self.translation_finished.emit(f"✓ Done: {os.path.basename(output_path)} ({'Extracted' if self.extract_only else 'Translated'}: {translated_count}/{total})")

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
            translated_count = 0
            for i, subtitle in enumerate(subtitles):
                if not CodeDetector.is_code_or_technical(subtitle['text']):
                    try:
                        original_text = subtitle['text']
                        translated = translate.translate(subtitle['text'], "en", "ar")
                        # Validate translation output - never leave blank
                        if translated and len(translated.strip()) > 0:
                            subtitle['text'] = translated
                            translated_count += 1
                        else:
                            # If translation returned empty, keep original and log
                            self.status_update.emit(f"⚠ Subtitle {i+1}: Translation resulted in empty text, keeping original")
                    except Exception as e:
                        # Keep original if translation fails - log the issue
                        self.status_update.emit(f"⚠ Subtitle {i+1} translation error: {str(e)[:50]}")

                progress = 30 + int((i + 1) / total * 70)
                self.progress_update.emit(progress)
            
            self.status_update.emit(f"✓ Translated {translated_count}/{total} subtitles to Arabic")

            # Save translated SRT
            output_path = self.srt_path.replace('.srt', '.ar.srt')
            output_content = SRTParser.format(subtitles)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_content)

            self.progress_update.emit(100)
            self.translation_finished.emit(f"✓ Done: {os.path.basename(output_path)} (Translated: {translated_count}/{total})")

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
                original_text = subtitle['text']  # Save original before any modification
                
                # Skip if text is empty - strict code checking is DISABLED for generic AI models as they handle context better
                if not text_to_translate:
                    self.skipped_count += 1
                # elif CodeDetector.is_code_or_technical(text_to_translate):
                #     self.skipped_count += 1
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
                            # IMPORTANT: Never leave text blank - fallback to original if translation fails
                            if translated and len(translated) > 0:
                                subtitle['text'] = translated
                                self.translated_count += 1
                            else:
                                # Fallback: keep original text to avoid losing content
                                subtitle['text'] = original_text
                                self.status_update.emit(f"⚠ Subtitle {i+1}: Empty response, kept original text")
                                self.skipped_count += 1
                        else:
                            # No response received - keep original text
                            subtitle['text'] = original_text
                            self.status_update.emit(f"⚠ Subtitle {i+1}: No response received, kept original text")
                            self.skipped_count += 1
                            
                    except Exception as e:
                        error_msg = str(e)
                        # IMPORTANT: Keep original text on any error to ensure no data loss
                        subtitle['text'] = original_text
                        # Provide helpful error diagnostics
                        if "model_not_found" in error_msg or "does not have access" in error_msg:
                            self.status_update.emit(f"⚠ Model '{self.model}' not available. Try: gpt-4, gpt-4-turbo, gpt-4o, gpt-4o-mini")
                        else:
                            self.status_update.emit(f"⚠ API Error for subtitle {i+1}: {error_msg[:100]}")
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
    """Main GUI application for translation with batch processing support."""

    def __init__(self):
        super().__init__()
        self.thread = None
        self.batch_processor = None  # Will be created when needed
        self.batch_jobs = []  # List of jobs to process
        self.batch_manager = None
        self.current_engine = None
        self.init_ui()

    def closeEvent(self, event):
        """Handle application close event - clean up threads."""
        self.cleanup_threads()
        event.accept()

    def cleanup_threads(self):
        """Properly clean up all running threads."""
        # Stop batch manager if running
        if self.batch_manager and self.batch_manager.isRunning():
            self.batch_manager.stop()
            self.batch_manager.wait(timeout=5000)  # Wait up to 5 seconds

        # Stop single file translation thread if running
        if self.thread and self.thread.isRunning():
            self.thread.wait(timeout=5000)

    def init_ui(self):
        """Initialize UI components."""
        self.setWindowTitle("Translation Studio - Batch Translation to Arabic")
        self.setGeometry(100, 100, 900, 900)

        main_layout = QVBoxLayout()

        # ===== Header with Author =====
        header_label = QLabel("Translation Studio - Batch Processing")
        header_label.setFont(QFont("Arial", 14, QFont.Bold))
        main_layout.addWidget(header_label)
        
        author_label = QLabel("Made by Mahmoud Gado | Batch Mode Enabled")
        author_label.setFont(QFont("Arial", 9))
        author_label.setStyleSheet("color: gray;")
        main_layout.addWidget(author_label)
        
        separator = QLabel("─" * 100)
        main_layout.addWidget(separator)

        # Create tabs for single and batch mode
        self.tabs = QTabWidget()
        
        # ===== SINGLE FILE TAB =====
        single_widget = QWidget()
        single_layout = QVBoxLayout()
        
        # Video Translation Section
        video_title = QLabel("🎥 VIDEO/AUDIO TRANSLATION (Whisper - Offline)")
        video_title.setFont(QFont("Arial", 11, QFont.Bold))
        single_layout.addWidget(video_title)

        video_layout = QHBoxLayout()
        self.video_btn = QPushButton("Select Video File")
        self.video_btn.clicked.connect(self.select_video)
        self.video_model_combo = QComboBox()
        self.video_model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        
        self.extract_only_check = QCheckBox("Extract Original Language Only")
        
        video_layout.addWidget(self.video_btn)
        video_layout.addWidget(QLabel("Model:"))
        video_layout.addWidget(self.video_model_combo)
        single_layout.addLayout(video_layout)
        single_layout.addWidget(self.extract_only_check)

        # SRT Translation Section - Argos
        srt_argos_title = QLabel("📝 SRT TRANSLATION - OFFLINE (Argos Translate)")
        srt_argos_title.setFont(QFont("Arial", 11, QFont.Bold))
        single_layout.addWidget(srt_argos_title)

        self.srt_argos_btn = QPushButton("Select SRT File (Argos)")
        self.srt_argos_btn.clicked.connect(self.select_srt_argos)
        single_layout.addWidget(self.srt_argos_btn)

        # SRT Translation Section - ChatGPT
        srt_chatgpt_title = QLabel("📝 SRT TRANSLATION - ONLINE (ChatGPT)")
        srt_chatgpt_title.setFont(QFont("Arial", 11, QFont.Bold))
        single_layout.addWidget(srt_chatgpt_title)

        srt_chatgpt_layout = QHBoxLayout()
        self.srt_chatgpt_btn = QPushButton("Select SRT File (ChatGPT)")
        self.srt_chatgpt_btn.clicked.connect(self.select_srt_chatgpt)
        self.chatgpt_model_combo = QComboBox()
        self.chatgpt_model_combo.addItems(["gpt-4-turbo", "gpt-4", "gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini"])
        srt_chatgpt_layout.addWidget(self.srt_chatgpt_btn)
        srt_chatgpt_layout.addWidget(QLabel("Model:"))
        srt_chatgpt_layout.addWidget(self.chatgpt_model_combo)
        single_layout.addLayout(srt_chatgpt_layout)

        # API Key input
        self.api_key_label = QLabel("OpenAI API Key:")
        single_layout.addWidget(self.api_key_label)
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("sk-...")
        single_layout.addWidget(self.api_key_input)

        single_layout.addStretch()
        single_widget.setLayout(single_layout)
        self.tabs.addTab(single_widget, "Single File")

        # ===== BATCH MODE TAB =====
        batch_widget = QWidget()
        batch_layout = QVBoxLayout()

        # Batch controls
        batch_title = QLabel("📦 BATCH TRANSLATION MODE")
        batch_title.setFont(QFont("Arial", 11, QFont.Bold))
        batch_layout.addWidget(batch_title)

        # Engine selection
        engine_layout = QHBoxLayout()
        engine_layout.addWidget(QLabel("Select Engine:"))
        self.batch_engine_combo = QComboBox()
        self.batch_engine_combo.addItems(["Whisper (Offline)", "Argos (Offline)", "ChatGPT (Online)"])
        engine_layout.addWidget(self.batch_engine_combo)
        engine_layout.addStretch()
        batch_layout.addLayout(engine_layout)

        # Whisper model selection (shown when Whisper selected)
        self.batch_whisper_widget = QWidget()
        batch_whisper_layout = QVBoxLayout()
        
        whisper_model_layout = QHBoxLayout()
        whisper_model_layout.addWidget(QLabel("Whisper Model:"))
        self.batch_whisper_model_combo = QComboBox()
        self.batch_whisper_model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.batch_whisper_model_combo.setCurrentText("base")
        whisper_model_layout.addWidget(self.batch_whisper_model_combo)
        whisper_model_layout.addStretch()
        batch_whisper_layout.addLayout(whisper_model_layout)
        
        self.batch_extract_only_check = QCheckBox("Extract Original Language Only (No Translation)")
        batch_whisper_layout.addWidget(self.batch_extract_only_check)
        
        self.batch_whisper_widget.setLayout(batch_whisper_layout)
        batch_layout.addWidget(self.batch_whisper_widget)

        # ChatGPT model selection (shown when ChatGPT selected)
        self.batch_chatgpt_model_widget = QWidget()
        self.batch_chatgpt_model_layout = QHBoxLayout()
        self.batch_chatgpt_model_layout.addWidget(QLabel("ChatGPT Model:"))
        self.batch_chatgpt_model_combo = QComboBox()
        self.batch_chatgpt_model_combo.addItems(["gpt-4-turbo", "gpt-4", "gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini"])
        self.batch_chatgpt_model_layout.addWidget(self.batch_chatgpt_model_combo)
        self.batch_chatgpt_model_layout.addStretch()
        self.batch_chatgpt_model_widget.setLayout(self.batch_chatgpt_model_layout)
        batch_layout.addWidget(self.batch_chatgpt_model_widget)
        self.batch_chatgpt_model_widget.setVisible(False)

        # API key for batch ChatGPT
        self.batch_api_key_label = QLabel("OpenAI API Key:")
        batch_layout.addWidget(self.batch_api_key_label)
        self.batch_api_key_input = QLineEdit()
        self.batch_api_key_input.setEchoMode(QLineEdit.Password)
        self.batch_api_key_input.setPlaceholderText("sk-...")
        batch_layout.addWidget(self.batch_api_key_input)
        self.batch_api_key_label.setVisible(False)
        self.batch_api_key_input.setVisible(False)

        # Parallel jobs control
        parallel_layout = QHBoxLayout()
        parallel_layout.addWidget(QLabel("Parallel Jobs:"))
        self.parallel_jobs_spin = QSpinBox()
        self.parallel_jobs_spin.setMinimum(1)
        self.parallel_jobs_spin.setMaximum(20)
        self.parallel_jobs_spin.setValue(2)
        parallel_layout.addWidget(self.parallel_jobs_spin)
        parallel_layout.addStretch()
        batch_layout.addLayout(parallel_layout)

        # File selection buttons
        file_button_layout = QHBoxLayout()
        self.batch_select_files_btn = QPushButton("📂 Select Files")
        self.batch_select_files_btn.clicked.connect(self.batch_select_files)
        file_button_layout.addWidget(self.batch_select_files_btn)

        self.batch_clear_btn = QPushButton("🗑️  Clear Queue")
        self.batch_clear_btn.clicked.connect(self.batch_clear_queue)
        file_button_layout.addWidget(self.batch_clear_btn)
        batch_layout.addLayout(file_button_layout)

        # Queue display
        self.batch_queue_list = QListWidget()
        self.batch_queue_list.setMaximumHeight(200)
        batch_layout.addWidget(QLabel("📋 Translation Queue:"))
        batch_layout.addWidget(self.batch_queue_list)

        # Batch controls
        control_layout = QHBoxLayout()
        self.batch_start_btn = QPushButton("▶️  Start Processing")
        self.batch_start_btn.clicked.connect(self.batch_start_processing)
        control_layout.addWidget(self.batch_start_btn)

        self.batch_stop_btn = QPushButton("⏹️  Stop Processing")
        self.batch_stop_btn.setEnabled(False)
        self.batch_stop_btn.clicked.connect(self.batch_stop_processing)
        control_layout.addWidget(self.batch_stop_btn)
        batch_layout.addLayout(control_layout)

        batch_layout.addStretch()
        batch_widget.setLayout(batch_layout)
        self.tabs.addTab(batch_widget, "Batch Mode")

        # Connect batch engine combo
        self.batch_engine_combo.currentTextChanged.connect(self.update_batch_ui)

        main_layout.addWidget(self.tabs)

        # ===== Progress and Status (Common) =====
        separator = QLabel("─" * 100)
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

    def update_batch_ui(self):
        """Update batch UI based on selected engine."""
        engine = self.batch_engine_combo.currentText()
        is_chatgpt = "ChatGPT" in engine
        is_whisper = "Whisper" in engine
        
        self.batch_chatgpt_model_widget.setVisible(is_chatgpt)
        self.batch_api_key_label.setVisible(is_chatgpt)
        self.batch_api_key_input.setVisible(is_chatgpt)
        self.batch_whisper_widget.setVisible(is_whisper)
        
        if is_whisper:
            self.batch_select_files_btn.setText("📂 Select Video Files")
        else:
            self.batch_select_files_btn.setText("📂 Select SRT Files")

    def batch_select_files(self):
        """Select multiple files for batch processing."""
        is_whisper = "Whisper" in self.batch_engine_combo.currentText()
        
        if is_whisper:
            caption = "Select Video Files for Processing"
            filter_str = "Video Files (*.mp4 *.mkv *.avi *.mov *.webm);;All Files (*)"
        else:
            caption = "Select SRT Files for Batch Processing"
            filter_str = "SRT Files (*.srt);;All Files (*)"

        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            caption,
            "",
            filter_str
        )

        if file_paths:
            selection = self.batch_engine_combo.currentText()
            if "ChatGPT" in selection:
                engine = "chatgpt"
            elif "Whisper" in selection:
                engine = "whisper"
            else:
                engine = "argos"
            
            config = {}
            if engine == "chatgpt":
                api_key = self.batch_api_key_input.text().strip()
                if not api_key:
                    self.log_area.append("[Batch] ✗ Error: API key required for ChatGPT")
                    return
                config["api_key"] = api_key
                config["model"] = self.batch_chatgpt_model_combo.currentText()
            elif engine == "whisper":
                config["model"] = self.batch_whisper_model_combo.currentText()
                config["extract_only"] = self.batch_extract_only_check.isChecked()

            # Create translation jobs
            from batch_processor import TranslationEngineType as EngineType
            
            self.batch_jobs = []
            if engine == "chatgpt":
                engine_type = EngineType.CHATGPT
            elif engine == "whisper":
                engine_type = EngineType.WHISPER
            else:
                engine_type = EngineType.ARGOS
            
            for file_path in file_paths:
                if os.path.exists(file_path):
                    job = TranslationJob(
                        file_path=file_path,
                        engine=engine_type,
                        config=config
                    )
                    self.batch_jobs.append(job)
                    self.log_area.append(f"[Batch] Added: {os.path.basename(file_path)}")
            
            self.log_area.append(f"[Batch] ✓ Ready to translate {len(self.batch_jobs)} file(s)")
            self.refresh_batch_queue_display()

    def batch_clear_queue(self):
        """Clear the batch processing queue."""
        self.batch_jobs.clear()
        self.batch_queue_list.clear()
        self.log_area.append("[Batch] Queue cleared")

    def refresh_batch_queue_display(self):
        """Update batch queue list display."""
        self.batch_queue_list.clear()
        
        for job in self.batch_jobs:
            filename = os.path.basename(job.file_path)
            status_icon = {
                TranslationStatus.PENDING: "⏳",
                TranslationStatus.RUNNING: "⚙️",
                TranslationStatus.COMPLETED: "✓",
                TranslationStatus.FAILED: "✗",
                TranslationStatus.SKIPPED: "⊘"
            }.get(job.status, "❓")

            item_text = f"{status_icon} {filename} | {job.engine.value.upper()} | {job.progress}%"
            
            item = QListWidgetItem(item_text)
            
            # Color code by status
            if job.status == TranslationStatus.COMPLETED:
                item.setForeground(QColor("green"))
            elif job.status == TranslationStatus.RUNNING:
                item.setForeground(QColor("blue"))
            elif job.status == TranslationStatus.FAILED:
                item.setForeground(QColor("red"))
            elif job.status == TranslationStatus.PENDING:
                item.setForeground(QColor("gray"))

            self.batch_queue_list.addItem(item)

    def batch_start_processing(self):
        """Start batch translation processing."""
        if not self.batch_jobs:
            self.log_area.append("[Batch] ✗ Error: No files in queue")
            return

        self.batch_select_files_btn.setEnabled(False)
        self.batch_clear_btn.setEnabled(False)
        self.batch_start_btn.setEnabled(False)
        self.batch_stop_btn.setEnabled(True)
        self.batch_engine_combo.setEnabled(False)
        self.parallel_jobs_spin.setEnabled(False)

        self.log_area.append(f"[Batch] ▶️ Starting translation of {len(self.batch_jobs)} file(s)...")

        # Determine which executor to use
        # Determine which executor to use
        engine_text = self.batch_engine_combo.currentText()
        if "ChatGPT" in engine_text:
            executor = self.execute_chatgpt_batch_job
        elif "Whisper" in engine_text:
            executor = self.execute_whisper_batch_job
        else:
            executor = self.execute_argos_batch_job

        # Create and start the batch processor
        self.batch_manager = SimpleBatchProcessor(self.batch_jobs, executor)
        
        # Connect signals
        self.batch_manager.job_started.connect(self.on_batch_job_started)
        self.batch_manager.job_progress.connect(self.on_batch_job_progress)
        self.batch_manager.job_completed.connect(self.on_batch_job_completed)
        self.batch_manager.job_failed.connect(self.on_batch_job_failed)
        self.batch_manager.batch_progress.connect(self.on_batch_progress)
        self.batch_manager.batch_finished.connect(self.on_batch_finished)
        self.batch_manager.start()

    def batch_stop_processing(self):
        """Stop batch translation."""
        if self.batch_manager and self.batch_manager.isRunning():
            self.batch_manager.stop()
            self.batch_manager.wait(timeout=5000)  # Wait up to 5 seconds for thread to finish
        self.batch_reset_ui()
        self.log_area.append("[Batch] ⏹️ Processing stopped")

    def batch_reset_ui(self):
        """Reset batch UI after processing."""
        self.batch_select_files_btn.setEnabled(True)
        self.batch_clear_btn.setEnabled(True)
        self.batch_start_btn.setEnabled(True)
        self.batch_stop_btn.setEnabled(False)
        self.batch_engine_combo.setEnabled(True)
        self.parallel_jobs_spin.setEnabled(True)

    def on_batch_job_started(self, job_id: str):
        """Handle batch job start."""
        # Find the job with this ID in our batch_jobs list
        job = None
        for j in self.batch_jobs:
            if j.job_id == job_id:
                job = j
                break
        
        if job:
            filename = os.path.basename(job.file_path)
            self.log_area.append(f"[{job.engine.value.upper()}] Starting: {filename}")

    def on_batch_job_progress(self, job_id: str, progress: int, message: str):
        """Handle batch job progress."""
        if message:
            self.log_area.append(f"  {message}")
        self.refresh_batch_queue_display()

    def on_batch_job_completed(self, job_id: str, output_path: str):
        """Handle batch job completion."""
        # Find the job with this ID in our batch_jobs list
        job = None
        for j in self.batch_jobs:
            if j.job_id == job_id:
                job = j
                break
        
        if job:
            filename = os.path.basename(job.file_path)
            output_name = os.path.basename(output_path) if output_path else "unknown"
            self.log_area.append(f"[{job.engine.value.upper()}] Completed: {filename} -> {output_name}")
        self.refresh_batch_queue_display()

    def on_batch_job_failed(self, job_id: str, error_message: str):
        """Handle batch job failure."""
        # Find the job with this ID in our batch_jobs list
        job = None
        for j in self.batch_jobs:
            if j.job_id == job_id:
                job = j
                break
        
        if job:
            filename = os.path.basename(job.file_path)
            self.log_area.append(f"[{job.engine.value.upper()}] Failed: {filename} - {error_message}")
        self.refresh_batch_queue_display()

    def on_batch_queue_updated(self, stats: dict):
        """Handle queue statistics update."""
        progress = self.batch_processor.queue.get_progress_summary()
        percentage = progress.get("percentage", 0)
        self.progress.setValue(percentage)
        
        completed = stats.get("completed", 0)
        total = stats.get("total_jobs", 0)
        active = stats.get("active", 0)
        self.status_label.setText(f"Status: Batch Processing | Completed: {completed}/{total} | Active: {active}")

    def on_batch_progress(self, stats: dict):
        """Handle batch progress update."""
        total = stats.get("total", 0)
        completed = stats.get("completed", 0)
        failed = stats.get("failed", 0)
        current = stats.get("current", 0)
        
        if total > 0:
            percentage = int((completed * 100) / total) if total > 0 else 0
            self.progress.setValue(percentage)
        
        self.status_label.setText(f"Status: Batch Processing | {completed}/{total} completed | {failed} failed")

    def on_batch_finished(self, final_stats: dict):
        """Handle batch completion."""
        total = final_stats.get("total", 0)
        completed = final_stats.get("completed", 0)
        failed = final_stats.get("failed", 0)
        
        self.log_area.append("\n" + "="*70)
        self.log_area.append(f"[Batch] 🎉 All jobs completed!")
        self.log_area.append(f"[Batch] Total: {total} | Completed: {completed} | Failed: {failed}")
        self.log_area.append("="*70 + "\n")
        
        self.progress.setValue(100)
        self.batch_reset_ui()

    def on_batch_all_completed(self, final_stats: dict):
        """Handle batch completion (legacy method)."""
        # Redirect to new handler for backward compatibility
        self.on_batch_finished(final_stats)

    def execute_whisper_batch_job(self, job) -> bool:
        """Execute single Whisper translation job."""
        try:
            if not WHISPER_AVAILABLE:
                on_failed = job.config.get('_on_failed')
                if on_failed:
                    on_failed("Whisper not installed")
                return False

            on_progress = job.config.get('_on_progress', lambda *args: None)
            on_completed = job.config.get('_on_completed', lambda *args: None)
            on_failed = job.config.get('_on_failed', lambda *args: None)

            model_name = job.config.get('model', 'medium')
            extract_only = job.config.get('extract_only', False)

            on_progress(10, f"Loading Whisper model ({model_name})...")
            model = whisper.load_model(model_name)

            # Extract audio
            on_progress(20, "Extracting audio...")
            audio_path = os.path.splitext(job.file_path)[0] + "_temp_audio.wav"
            
            try:
                FFmpegHandler.extract_audio(job.file_path, audio_path)
            except Exception as e:
                on_failed(f"Audio extraction failed: {str(e)}")
                return False

            try:
                # Transcribe
                # Transcribe
                if extract_only:
                    on_progress(40, "Transcribing (Original Language)...")
                    transcribe_options = {"task": "transcribe"}
                else:
                    on_progress(40, "Transcribing & Translating to English...")
                    transcribe_options = {"task": "translate"}

                result = model.transcribe(
                    audio_path,
                    **transcribe_options
                )

                on_progress(50, "Converting output...")
                srt_content = WhisperTranslateThread._format_whisper_output(result)
                subtitles = SRTParser.parse(srt_content)
                total = len(subtitles)

                if total > 0:
                    if extract_only:
                        on_progress(80, f"Extracted {total} segments")
                    else:
                        on_progress(60, f"Translating {total} segments to Arabic...")
                        
                        if ARGOS_AVAILABLE:
                            try:
                                try:
                                    package.update_package_index()
                                except Exception:
                                    pass
                                
                                translated_count = 0
                                for i, subtitle in enumerate(subtitles):
                                    if not CodeDetector.is_code_or_technical(subtitle['text']):
                                        try:
                                            translated = translate.translate(subtitle['text'], "en", "ar")
                                            if translated and len(translated.strip()) > 0:
                                                subtitle['text'] = translated
                                                translated_count += 1
                                        except Exception:
                                            pass
                                    
                                    progress = 60 + int((i + 1) / total * 20)
                                    on_progress(progress, f"Translated {i+1}/{total}")
                            except Exception as e:
                                on_progress(60, f"Translation unavailable: {str(e)}")
                        
                        srt_content = SRTParser.format(subtitles)

                on_progress(90, "Saving file...")
                
                # Get detected language if available
                detected_lang = result.get('language', 'original')
                
                # Output filename logic:
                # If extract_only: use detected language (e.g. "video en.srt")
                # If translation: forced to "ar" as that's the pipeline
                suffix = detected_lang if extract_only else "ar"

                # Output filename as requested
                # Create 'subs' folder if it doesn't exist
                source_dir = os.path.dirname(job.file_path)
                output_dir = os.path.join(source_dir, "subs")
                os.makedirs(output_dir, exist_ok=True)
                
                base_name = os.path.splitext(os.path.basename(job.file_path))[0]
                output_path = os.path.join(output_dir, f"{base_name} {suffix}.srt")

                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(srt_content)

                on_completed(output_path)
                return True

            finally:
                if os.path.exists(audio_path):
                    try:
                        os.remove(audio_path)
                    except:
                        pass

        except Exception as e:
            on_failed = job.config.get('_on_failed', lambda *args: None)
            on_failed(str(e))
            return False

    def execute_argos_batch_job(self, job) -> bool:
        """Execute single Argos translation job."""
        try:
            if not ARGOS_AVAILABLE:
                on_failed = job.config.get('_on_failed')
                if on_failed:
                    on_failed("Argos Translate not installed")
                return False

            on_progress = job.config.get('_on_progress', lambda *args: None)
            on_completed = job.config.get('_on_completed', lambda *args: None)
            on_failed = job.config.get('_on_failed', lambda *args: None)

            on_progress(20, "Preparing language packages...")

            try:
                package.update_package_index()
            except Exception:
                pass

            on_progress(30, "Reading SRT file...")

            with open(job.file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            subtitles = SRTParser.parse(content)
            total = len(subtitles)

            if total == 0:
                on_failed("No subtitles found in file")
                return False

            on_progress(40, f"Translating {total} subtitles...")

            for i, subtitle in enumerate(subtitles):
                if not CodeDetector.is_code_or_technical(subtitle['text']):
                    try:
                        translated = translate.translate(subtitle['text'], "en", "ar")
                        subtitle['text'] = translated
                    except Exception:
                        pass

                progress = 40 + int((i + 1) / total * 55)
                on_progress(progress, f"Translated {i+1}/{total}")

            on_progress(95, "Saving file...")

            # Output filename as requested: [original] trans.srt
            # Create 'subs' folder
            source_dir = os.path.dirname(job.file_path)
            output_dir = os.path.join(source_dir, "subs")
            os.makedirs(output_dir, exist_ok=True)
            
            base_name = os.path.splitext(os.path.basename(job.file_path))[0]
            output_path = os.path.join(output_dir, f"{base_name} en.srt")
            output_content = SRTParser.format(subtitles)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_content)

            on_completed(output_path)
            return True

        except Exception as e:
            on_failed = job.config.get('_on_failed', lambda *args: None)
            on_failed(str(e))
            return False

    def execute_chatgpt_batch_job(self, job) -> bool:
        """Execute single ChatGPT translation job."""
        try:
            if not OPENAI_AVAILABLE:
                on_failed = job.config.get('_on_failed')
                if on_failed:
                    on_failed("OpenAI library not installed")
                return False

            on_progress = job.config.get('_on_progress', lambda *args: None)
            on_completed = job.config.get('_on_completed', lambda *args: None)
            on_failed = job.config.get('_on_failed', lambda *args: None)

            api_key = job.config.get('api_key', '')
            model = job.config.get('model', 'gpt-4-turbo')

            if not api_key:
                on_failed("API key not provided")
                return False

            client = OpenAI(api_key=api_key)

            on_progress(20, "Reading SRT file...")

            with open(job.file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            subtitles = SRTParser.parse(content)
            total = len(subtitles)

            if total == 0:
                on_failed("No subtitles found in file")
                return False

            on_progress(30, f"Translating {total} subtitles with ChatGPT...")

            translated_count = 0
            skipped_count = 0

            for i, subtitle in enumerate(subtitles):
                text_to_translate = subtitle['text'].strip()
                
                if not text_to_translate:
                    skipped_count += 1
                elif CodeDetector.is_code_or_technical(text_to_translate):
                    skipped_count += 1
                else:
                    try:
                        response = client.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": ChatGPTTranslateThread.SYSTEM_PROMPT},
                                {"role": "user", "content": text_to_translate}
                            ],
                            temperature=0.3,
                            max_tokens=500
                        )
                        
                        if response.choices and len(response.choices) > 0:
                            translated = response.choices[0].message.content.strip()
                            if translated:
                                subtitle['text'] = translated
                                translated_count += 1
                            else:
                                skipped_count += 1
                        else:
                            skipped_count += 1
                            
                    except Exception as e:
                        on_progress(0, f"⚠ API Error: {str(e)[:80]}")
                        skipped_count += 1

                progress = 30 + int((i + 1) / total * 65)
                on_progress(progress, f"Translated {translated_count}, Skipped {skipped_count}")

            on_progress(95, "Saving file...")

            # Output filename as requested: [original] trans.srt
            # Create 'subs' folder
            source_dir = os.path.dirname(job.file_path)
            output_dir = os.path.join(source_dir, "subs")
            os.makedirs(output_dir, exist_ok=True)
            
            base_name = os.path.splitext(os.path.basename(job.file_path))[0]
            output_path = os.path.join(output_dir, f"{base_name} trans.srt")
            output_content = SRTParser.format(subtitles)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_content)

            on_completed(output_path)
            return True

        except Exception as e:
            on_failed = job.config.get('_on_failed', lambda *args: None)
            on_failed(str(e))
            return False

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
            extract_only = self.extract_only_check.isChecked()
            
            self.log_area.append(f"[Video] Selected: {os.path.basename(file_path)}")
            self.log_area.append(f"[Video] Model: {model} | Extract Only: {extract_only}")
            self.disable_ui()
            self.thread = WhisperTranslateThread(file_path, model, extract_only)
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
        self.extract_only_check.setEnabled(False)
        self.srt_argos_btn.setEnabled(False)
        self.srt_chatgpt_btn.setEnabled(False)
        self.api_key_input.setEnabled(False)
        self.progress.setValue(0)

    def enable_ui(self):
        """Enable UI after translation."""
        self.video_btn.setEnabled(True)
        self.video_model_combo.setEnabled(True)
        self.extract_only_check.setEnabled(True)
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