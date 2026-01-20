# Quick Start: Batch Translation Mode

## 30-Second Setup

1. **Launch Application**
   ```bash
   python main.py
   ```

2. **Switch to "Batch Mode" Tab**
   - Click the blue "Batch Mode" tab at the top

3. **Select Engine**
   - Choose **"Argos (Offline)"** for free, fast translation
   - Or **"ChatGPT (Online)"** for better quality (requires API key)

4. **Add Files**
   - Click **"📂 Select SRT Files"**
   - Select multiple `.srt` files
   - They appear in the queue list

5. **Start Processing**
   - Click **"▶️ Start Processing"**
   - Files translate automatically in parallel
   - Watch the live progress display

## Common Workflows

### Workflow 1: Translate 5 SRT Files (Free, Offline)

```
Settings:
  Engine: Argos (Offline)
  Parallel Jobs: 3 (safe for offline)
  Files: 5 English SRT files

Time: ~2-3 minutes
Cost: FREE
Output: 5 × .ar.srt files
```

**Steps:**
1. Tab → Batch Mode
2. Select Engine: Argos
3. Set Parallel Jobs: 3
4. Click 📂, select 5 files
5. Click ▶️ Start
6. Done! Check `.ar.srt` files in same folder

### Workflow 2: Translate 10 Files (ChatGPT, High Quality)

```
Settings:
  Engine: ChatGPT
  Model: gpt-4-turbo
  Parallel Jobs: 2 (API rate limit safe)
  API Key: sk-...

Time: ~8-10 minutes
Cost: ~$0.50-1.00 (depends on file length)
Output: 10 × .ar.srt files with better quality
```

**Steps:**
1. Tab → Batch Mode
2. Select Engine: ChatGPT
3. Enter API Key in field
4. Set Model: gpt-4-turbo
5. Set Parallel Jobs: 2
6. Click 📂, select 10 files
7. Click ▶️ Start
8. Monitor progress in log

### Workflow 3: Mix & Match (Offline First, Then ChatGPT)

```
Batch 1 (Offline):
  - 20 files with Argos
  - Free, quick preview
  - Time: ~5 minutes

Batch 2 (Online):
  - Best 5 files with ChatGPT
  - High quality for important files
  - Time: ~3 minutes
```

## What Each Icon Means

| Icon | Status | What It Means |
|------|--------|--------------|
| ⏳ | Pending | Waiting to start (in queue) |
| ⚙️ | Running | Currently being translated |
| ✓ | Completed | Successfully translated ✓ |
| ✗ | Failed | Error during translation ✗ |
| ⊘ | Skipped | Skipped (not needed) |

## Parallel Jobs Explained

| Setting | Uses | Best For |
|---------|------|----------|
| **1 job** | 1 file at a time | Limited RAM, testing |
| **2 jobs** | 2 files together | Most computers (RECOMMENDED) |
| **3 jobs** | 3 files together | Good computer, Argos only |
| **4 jobs** | 4 files together | High-end system |

**Simple Rule:**
- 8GB RAM → Parallel = 2
- 16GB RAM → Parallel = 3
- 32GB+ RAM → Parallel = 4
- Low RAM → Parallel = 1

## Troubleshooting Quick Reference

| Problem | Solution |
|---------|----------|
| "API key not provided" | Enter API key in ChatGPT field |
| Slow processing | Reduce Parallel Jobs to 1 |
| Processing stopped | Check internet (ChatGPT) |
| One file failed | Check logs, others still process |
| No .ar.srt files created | Check input folder, verify file paths |

## Output Files

**Input:**
```
Interview_English.srt
podcast_episode_1.srt
tutorial_part2.srt
```

**Output (automatically created):**
```
Interview_English.ar.srt        ← Added to same folder
podcast_episode_1.ar.srt         ← Added to same folder
tutorial_part2.ar.srt            ← Added to same folder
```

All `.ar.srt` files are **in the same folder** as originals.

## Tips & Tricks

### ✓ Good Practices
- Test with 1-2 files first
- Use Argos for quick preview
- Use ChatGPT for important files
- Check API key before starting
- Monitor first run to learn speed

### ✗ Avoid
- Too many parallel jobs (crashes)
- ChatGPT with 4 parallel jobs (hits rate limit)
- Large files without enough RAM
- Forgetting to enter API key
- Closing app during processing

## Example: Translating 10 Files

**Step-by-step:**

```
1. python main.py                          [Launch app]
2. Click "Batch Mode" tab                 [Switch to batch]
3. Select "Argos (Offline)"               [Choose engine]
4. Set Parallel to 2                      [Balanced speed]
5. Click 📂 Select SRT Files               [Open file picker]
6. Select: file1.srt → file10.srt         [Choose 10 files]
7. See "✓ Added 10 file(s) to queue"      [Confirmation]
8. Click ▶️ Start Processing               [Begin!]
9. Watch progress:
   ⚙️ file1.srt 45%
   ⚙️ file2.srt 32%
   ✓ file3.srt 100%
   ⏳ file4.srt 0%
   ...                                     [Real-time updates]
10. See "🎉 All jobs completed!"          [Done!]
11. Find file1.ar.srt, file2.ar.srt...    [Check output folder]
```

**Total Time:** ~4-5 minutes with Argos  
**Total Cost:** FREE

## Before You Start

- ✅ Python 3.10+ installed
- ✅ Requirements installed: `pip install -r requirements.txt`
- ✅ FFmpeg on PATH (for video mode only)
- ✅ Internet (for ChatGPT mode only)
- ✅ OpenAI API key (for ChatGPT mode)
- ✅ At least 2GB free RAM

## Need Help?

1. **See full documentation**: [BATCH_PROCESSING.md](BATCH_PROCESSING.md)
2. **Check implementation details**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
3. **View logs**: Check the log area in the app
4. **Restart if stuck**: Close app and run again

---

**That's it!** You're ready to batch translate multiple files. 🚀

**Made by Mahmoud Gado**
