# Testing Guide

This directory contains test scripts and example files for testing the Conversational English Copilot system.

## Test Scripts

### 1. Quick Verification Test (No Model Download Required)

```bash
python test_quick_verification.py
```

**What it tests:**
- Configuration loading
- Feature availability verification
- Expected performance metrics
- Pipeline flow explanation
- Usage instructions

**Time:** ~5 seconds  
**Requirements:** None (no models needed)

### 2. Full Performance Test (Requires Model Downloads)

```bash
python test_full_performance.py
```

**What it tests:**
- ASR performance with different audio lengths (2s, 8s, 15s)
- LLM performance with different prompt complexities
- End-to-end pipeline latency
- Document (PDF) loading and retrieval
- Context personalization features

**Time:** ~5-10 minutes (first run downloads models)  
**Requirements:** 
- Models will be downloaded automatically (~566 MB total)
  - Whisper tiny.en: ~75 MB
  - Qwen 2.5 0.5B: ~491 MB
- ~2 GB RAM
- Internet connection (first run only)

**Output:** 
- Console output with detailed metrics
- `performance_test_results.json` file with all results

### Results Interpretation

**ASR (Automatic Speech Recognition)**
- RTF (Real-Time Factor) < 0.3 = Excellent
- RTF < 0.5 = Good
- RTF < 1.0 = Acceptable
- RTF >= 1.0 = Too slow for real-time

**LLM (Language Model)**
- < 300ms = Excellent
- < 500ms = Good
- < 1000ms = Acceptable
- >= 1000ms = Too slow

**End-to-End Pipeline**
- < 1000ms = Excellent
- < 2000ms = Good
- < 3000ms = Acceptable
- >= 3000ms = Too slow

## Example Documents

### `example_english_guide.txt`

An example document containing:
- CEFR English proficiency levels (A1-C2)
- Active listening techniques
- Business English communication tips
- Conversation fillers and transitions
- Technical vocabulary (IT/Cloud/IoT)
- Common grammar patterns
- Handling difficult situations
- Networking and small talk tips

**How to use:**

1. Convert to PDF (optional but recommended):
   ```bash
   # On Linux/Mac with enscript and ps2pdf:
   enscript example_english_guide.txt -o - | ps2pdf - example_english_guide.pdf
   
   # Or use any text-to-PDF converter
   ```

2. Configure in `config.json`:
   ```json
   {
     "enable_document": true,
     "pdf_path": "/full/path/to/example_english_guide.pdf",
     "cite_document": true
   }
   ```

3. Run the application:
   ```bash
   python app/main.py
   ```

**Testing the document feature:**

When enabled, the system will:
1. Load and chunk the document automatically
2. Create semantic embeddings for each chunk
3. Retrieve relevant chunks based on conversation context
4. Include retrieved information in LLM prompts
5. Generate more informed suggestions

**Example scenario:**

- **Interlocutor:** "I'm not sure how to handle disagreements in meetings"
- **System retrieves from document:** "Disagreeing Politely: I see your point, however..."
- **System suggests:** "I see your point, however, I'd like to offer an alternative perspective..."

## Running Tests in Different Environments

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Quick test (no downloads)
python test_quick_verification.py

# Full test (downloads models)
python test_full_performance.py
```

### CI/CD Pipeline

For automated testing in CI/CD:

```bash
# Use quick test only (no model downloads)
python test_quick_verification.py

# Or run full test if models are cached
python test_full_performance.py
```

### Docker

```bash
# Build
docker build -t copilot-test .

# Run quick test
docker run copilot-test python test_quick_verification.py

# Run full test (mounts cache directory)
docker run -v ~/.cache/huggingface:/root/.cache/huggingface copilot-test python test_full_performance.py
```

## Troubleshooting

### Models Not Downloading

**Issue:** "No address associated with hostname" or network errors

**Solution:** 
- Check internet connection
- Verify firewall settings
- Try downloading models manually from HuggingFace

### Out of Memory

**Issue:** System runs out of RAM during testing

**Solution:**
- Close other applications
- Reduce test iterations in test scripts
- Use smaller model (already using smallest)

### Slow Performance

**Issue:** Tests take much longer than expected

**Solution:**
- Verify CPU has at least 4 cores
- Check system load (top/htop)
- Consider using GPU if available

## Performance Baselines

Based on GitHub Actions runner (AMD EPYC 7763, 4 cores):

| Metric | Expected Value | Status |
|--------|---------------|--------|
| ASR RTF | 0.24x | ✅ Excellent |
| LLM Latency | ~294ms | ✅ Excellent |
| Pipeline Total | ~924ms | ✅ Good |

Your results may vary based on hardware.

## Next Steps

After testing:

1. Review results in console output
2. Check `performance_test_results.json` for detailed metrics
3. Read `FEATURES_ES.md` for complete feature documentation
4. Configure `config.json` with your preferences
5. Run the application: `python app/main.py`

## Support

If you encounter issues:
1. Check this README
2. Review test output for specific errors
3. Consult `FEATURES_ES.md` for feature details
4. Open an issue on GitHub

---

*Last updated: 2026-02-03*
