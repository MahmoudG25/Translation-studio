# Translation Studio | استوديو الترجمة 🎬

**[English version below]**

تطبيق مكتبي احترافي لترجمة الفيديوهات والملفات الصوتية وملفات الترجمة (SRT) إلى اللغة العربية. يدعم محركات ترجمة متعددة بما في ذلك خيارات العمل بدون إنترنت.

**من تطوير: محمود جادو**

## المميزات ✨

*   **أنماط ترجمة متعددة:**
    *   **فيديو/صوت ← ترجمة عربية (SRT):** باستخدام OpenAI Whisper (استخراج النص + الترجمة).
    *   **SRT ← عربي:** باستخدام Argos Translate (يعمل بالكامل بدون إنترنت).
    *   **SRT ← عربي:** باستخدام OpenAI ChatGPT API (عبر الإنترنت، جودة احترافية).
*   **المعالجة الجماعية (Batch Processing):** (جديد!)
    *   ترجمة عدة ملفات في وقت واحد.
    *   إدارة قائمة الانتظار مع تتبع مباشر للتقدم.
    *   دعم محركات متعددة (Argos أو ChatGPT).
*   **استخراج SRT معزز:**
    *   استخراج النص من الفيديو عبر الإنترنت (OpenAI) أو بدون إنترنت (Whisper).
    *   دعم تنسيقات فيديو واسعة (MP4, MKV, AVI, MOV, WebM, FLV, M4V).
*   **حماية الأكواد والمصطلحات التقنية:**
    *   يحافظ على أسماء الدوال والمتغيرات والأكواد البرمجية كما هي.
    *   يكتشف ويتجاوز المصطلحات التقنية لضمان دقة الشرح.

## المتطلبات 🔧

### متطلبات النظام
*   Python 3.10
*   FFmpeg (لمعالجة الفيديو والصوت)
*   ذاكرة عشوائية (RAM) 8 جيجابايت (موصى به)
*   بطاقة رسوميات متوافقة مع CUDA (اختياري، لتسريع المعالجة)

---

Professional desktop application for translating videos, audio files, and SRT subtitles to Arabic. Supports multiple translation engines including offline options.

**Made by Mahmoud Gado**

## Features ✨

*   **Multiple Translation Modes:**
    *   **Video/Audio → Arabic SRT:** using OpenAI Whisper (offline/online transcription + translation).
    *   **SRT → Arabic:** using Argos Translate (completely offline).
    *   **SRT → Arabic:** using ChatGPT API (online, highest quality).
*   **Batch Processing:** (NEW!)
    *   Translate multiple files simultaneously.
    *   Queue management with real-time progress tracking.
    *   Multiple engine support (Argos or ChatGPT).
*   **Enhanced SRT Extraction:**
    *   Extract text from video Online (OpenAI) or Offline (Whisper).
    *   Support for vast video formats (MP4, MKV, AVI, MOV, WebM, FLV, M4V).
*   **Code Protection:**
    *   Intelligently protects code snippets and technical terms.
    *   Preserves function names, variables, and code syntax.

## Requirements 🔧

### System Requirements
*   Python 3.10
*   FFmpeg (for video/audio processing)
*   8GB RAM recommended
*   CUDA-compatible GPU (optional, for faster processing)

## Installation | التثبيت 🔧

1. **Install FFmpeg | تثبيت FFmpeg:**
   - Windows: `choco install ffmpeg`
   - macOS: `brew install ffmpeg`
   - Linux: `sudo apt-get install ffmpeg`

2. **Clone Repository | تحميل المشروع:**
   ```bash
   git clone https://github.com/MahmoudG25/translation-studio.git
   cd translation-studio
   ```

3. **Virtual Environment | إنشاء بيئة افتراضية:**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

4. **Install Everything | تثبيت كل شيء:**
   ```bash
   # Use the automatic installer | استخدم المثبت التلقائي
   install.bat
   ```

5. (Optional) Manual Installation | تثبيت يدوي (اختياري):
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

## Usage | الاستخدام 🚀

- **Run Application | تشغيل التطبيق:**
  ```bash
  python main.py
  # OR use | أو استخدم
  start.bat
  ```

---
**Made with ❤️ by Mahmoud Gado**
