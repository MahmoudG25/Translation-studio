# Batch Processing Guide

## Overview

The Translation Studio now supports **batch processing** to translate multiple files simultaneously. This allows you to queue multiple SRT files and process them in parallel, significantly speeding up large translation projects.

## Features

### Single File Mode
- Translate one file at a time (original functionality)
- **Video/Audio Translation** using Whisper (offline)
- **SRT Translation** using Argos (offline)
- **SRT Translation** using ChatGPT API (online)

### Batch Processing Mode (NEW)
- ✅ **Multiple File Processing** - Add 1-10+ files to queue
- ✅ **Parallel Execution** - Process 1-4 files simultaneously (configurable)
- ✅ **Queue Management** - View queue status, add/remove files before processing
- ✅ **Progress Tracking** - Real-time status for each file
- ✅ **Automatic Retry** - Continues processing if one file fails
- ✅ **Two Engines** - Argos (offline) or ChatGPT (online)

## Usage

### Starting Batch Translation

1. **Launch the Application**
   ```bash
   python main.py
   ```

2. **Switch to "Batch Mode" Tab**
   - Click the "Batch Mode" tab at the top of the window

3. **Configure Settings**
   - **Select Engine**: Choose "Argos (Offline)" or "ChatGPT (Online)"
   - **Parallel Jobs**: Set number of simultaneous translations (1-4, default: 2)
   - **API Key** (ChatGPT only): Enter your OpenAI API key

4. **Add Files**
   - Click "📂 Select SRT Files"
   - Select multiple `.srt` files from your file browser
   - Files appear in the queue list below

5. **Process Queue**
   - Click "▶️ Start Processing"
   - Watch progress in the log area and queue list
   - Each file shows status with percentage complete

6. **Monitor Progress**
   - **⏳ Pending** (gray) - Waiting to process
   - **⚙️ Running** (blue) - Currently processing
   - **✓ Completed** (green) - Successfully translated
   - **✗ Failed** (red) - Error during translation

## Parallel Processing

### Configuration

Control concurrent translations via "Parallel Jobs" spinner:

| Value | Behavior | Best For |
|-------|----------|----------|
| 1 | Sequential processing | Limited RAM, testing |
| 2 | Default, 2 at a time | Most systems (recommended) |
| 3 | 3 simultaneous | High-end systems |
| 4 | Maximum parallel | Powerful machines |

### Performance Tips

- **Offline (Argos)**: Can run 3-4 parallel safely
- **Online (ChatGPT)**: Use 1-2 to avoid API rate limits
- **Memory**: Monitor system RAM; each thread uses ~500MB
- **Network**: ChatGPT requires stable internet connection

## Output Files

Translated files are saved in the **same directory** as input files:

```
Input:  interview.srt
Output: interview.ar.srt
```

Naming convention:
- Original extension `.srt` → `.ar.srt` (Arabic)
- All files in same folder as source

## Queue Management

### Clear Queue
- Click "🗑️ Clear Queue" to remove all pending jobs
- Already-processing jobs will complete

### Remove Individual Files
- Not supported in current version
- Workaround: Clear queue and re-add desired files

### View Detailed Status
- Log area shows real-time updates
- Each job logs: engine, filename, progress, errors
- Final summary shows total completed/failed

## Engine Selection

### Argos Translate (Offline)
```
✓ Pros:
  - No internet required
  - No API costs
  - Can process 3-4 files in parallel
  - Faster for short subtitles
  
✗ Cons:
  - Lower translation quality
  - First run downloads language packs (~500MB)
  - Slower for long subtitles
```

### ChatGPT (Online)
```
✓ Pros:
  - Higher translation quality
  - Better context understanding
  - Supports all models (GPT-4, etc.)
  
✗ Cons:
  - Requires API key (paid)
  - Slower due to network latency
  - API rate limits (recommended: 1-2 parallel)
  - Requires internet connection
```

## Error Handling

### Common Issues

**"API key not provided"**
- Solution: Enter API key in ChatGPT API Key field

**"Argos Translate not installed"**
- Solution: `pip install argostranslate`

**"Model not available"**
- ChatGPT model issue
- Solution: Check API key, try different model

**"File not found"**
- File deleted or moved before processing
- Solution: Re-add files to queue

**Single file fails**
- Other files continue processing
- Solution: Check logs, retry after fixing issue

## API Rate Limiting (ChatGPT)

OpenAI has rate limits per minute/day. To avoid errors:

1. **Use lower parallel jobs** (1-2 instead of 3-4)
2. **Add delays** between large batches
3. **Monitor API usage** at platform.openai.com/account/usage

Example rate limits:
- GPT-4: 200 requests/minute
- GPT-4 Turbo: 500 requests/minute
- GPT-4o: 1000 requests/minute

## Performance Example

| Files | Engine | Parallel | Time |
|-------|--------|----------|------|
| 5 SRT | Argos | 2 | ~2 mins |
| 5 SRT | ChatGPT | 2 | ~5 mins |
| 10 SRT | Argos | 3 | ~3 mins |
| 10 SRT | ChatGPT | 1 | ~10 mins |

*Times vary based on subtitle length and system specs*

## Advanced: Custom Configuration

### Max Parallel Jobs (Code Level)

Edit `main.py` line where `TranslatorApp()` is created:

```python
self.batch_processor = MultiFileBatchProcessor(max_parallel=4)  # Change here
```

### System Resource Monitoring

Monitor CPU/RAM during batch processing:
- Windows: Task Manager
- Linux: `htop` or `watch free -h`
- macOS: Activity Monitor

## Troubleshooting

### Queue Stuck Processing
```bash
# Restart application
python main.py
```

### ChatGPT Quota Exceeded
- Wait 1 minute for rate limit reset
- Switch to Argos (offline)
- Upgrade API tier

### Memory Issues (Many Files)
- Reduce parallel jobs to 1
- Process in smaller batches
- Upgrade system RAM

### Slow Processing
**Argos slow**: First run downloads models, subsequent runs faster
**ChatGPT slow**: Network latency, check internet speed

## Technical Details

### Architecture

```
TranslatorApp (GUI)
    ↓
BatchTranslationManager (Coordinator)
    ↓
SingleJobWorker × N (Parallel Threads)
    ↓
[WhisperTranslateThread | ArgosTranslateThread | ChatGPTTranslateThread]
```

### Queue System

- `BatchTranslationQueue` - Manages job queue with thread-safe operations
- `BatchTranslationManager` - Controls parallel execution
- `SingleJobWorker` - Processes individual files
- Signals emit progress/completion to UI

### Thread Safety

- All queue operations use `threading.RLock()`
- No data races between parallel workers
- Safe to add jobs while processing

## Future Enhancements

Potential features for future versions:
- Remove individual files from queue
- Pause/resume processing
- Custom output folder selection
- Filter by extension (auto-detect .srt, .vtt)
- Batch import from directories
- Save/load queue configurations
- Video batch processing (Whisper)

## Support

For issues or feature requests:
1. Check logs in the application
2. Verify file paths and permissions
3. Test with single file mode first
4. Check API key (ChatGPT mode)
5. Review system resources

---

**Made by Mahmoud Gado**
