# Quick Start Guide - Telegram Knowledge Base Extractor

Get up and running in **5 minutes** with this streamlined setup guide.

## ⚡ Prerequisites Checklist

Before starting, make sure you have:

- [ ] Python 3.9 or higher installed
- [ ] Git installed
- [ ] A Telegram account
- [ ] 10 minutes of free time

## 🚀 Installation (2 minutes)

### Step 1: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/telegram-knowledge-extractor.git
cd telegram-knowledge-extractor

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Get Telegram API Credentials (1 minute)

1. Visit https://my.telegram.org/auth
2. Log in with your phone number
3. Go to "API development tools"
4. Create a new application (any name/description)
5. Copy your `api_id` and `api_hash`

### Step 3: Configure Environment (1 minute)

```bash
# Copy environment template
cp .env.template .env

# Edit .env with your favorite editor
nano .env
```

**Minimal required configuration:**

```env
# Telegram Configuration
TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_PHONE=+1234567890
TELEGRAM_CHANNELS=@techcrunch,@hackernews

# AI Configuration (optional for testing)
ANTHROPIC_API_KEY=your_key_or_leave_empty
USE_LOCAL_AI=false
```

## 🎯 First Run (1 minute)

### Test the Installation

```bash
# Test configuration loading
python -c "from src.config import get_config; config = get_config(); print('✅ Configuration loaded!')"

# Test database manager
python src/utils/db_manager.py

# Run the application
python main.py
```

## 📊 What Happens on First Run

1. **Authentication** - On first run, Telegram will send you a code
2. **Message Extraction** - Extracts messages from configured channels
3. **Duplicate Prevention** - Automatically filters out duplicates
4. **Data Storage** - Saves to `data/` directory
5. **Statistics** - Shows processing summary

## 🎨 Expected Output

```
============================================================
          Telegram Knowledge Base Extractor
============================================================
Telegram Channels: 2
AI Provider: Claude
Batch Size: 50
Duplicate Prevention: Enabled
JSON Storage: Enabled
CSV Export: Enabled
Debug Mode: Disabled
============================================================

🚀 Starting application...
✅ Configuration loaded
✅ Directories created
✅ Database connections configured
✅ Duplicate tracker initialized
✅ All components initialized

============================================================
                  Processing Channels
============================================================

📡 Processing channel: @techcrunch
📊 Total: 100 | New: 85 | Duplicates: 15 (15.0%)

📡 Processing channel: @hackernews
📊 Total: 100 | New: 92 | Duplicates: 8 (8.0%)

============================================================
                  Extraction Complete
============================================================

Final Results:
   Channels Processed: 2
   Total Messages Extracted: 200
   New Messages: 177
   Duplicates Filtered: 23
   Duplicate Rate: 11.5%
   Processing Time: 5.23s
   Throughput: 33.84 msg/s

🎉 Extraction workflow completed successfully!
💾 Data saved to: ./data
```

## 📁 Check Your Results

```bash
# View database
sqlite3 data/processed_messages.db "SELECT COUNT(*) FROM processed_messages;"

# Check data directory
ls -lh data/

# View state file
cat data/duplicate_tracker_state.json | python -m json.tool | head -20
```

## 🐛 Common Issues

### Issue: "No module named 'telethon'"

**Solution:**
```bash
pip install telethon
```

### Issue: "Configuration error: Invalid Telegram configuration"

**Solution:** Make sure you've:
- Created `.env` from `.env.template`
- Added your real `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`
- Added your phone number with country code

### Issue: "Database is locked"

**Solution:** This shouldn't happen with the centralized db_manager, but if it does:
```bash
# Close all connections
rm data/*.db
python main.py
```

### Issue: Telegram sends authentication code but script doesn't prompt

**Solution:**
```bash
# Run in interactive mode
python -i main.py
```

## 🎓 Next Steps

### 1. Configure AI Processing (Optional)

Add Claude API key to `.env`:
```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Or enable local AI:
```env
USE_LOCAL_AI=true
OLLAMA_BASE_URL=http://localhost:11434
```

### 2. Add More Channels

Edit `.env`:
```env
TELEGRAM_CHANNELS=@channel1,@channel2,@channel3
```

### 3. Customize Processing

Adjust settings in `.env`:
```env
BATCH_SIZE=100
MESSAGE_LIMIT_PER_CHANNEL=1000
MAX_MESSAGE_AGE_DAYS=30
```

### 4. Run Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python tests/unit/test_duplicate_prevention.py

# Run with coverage
pytest --cov=src tests/
```

### 5. Export Data

```bash
# Enable CSV export in .env
ENABLE_CSV_EXPORT=true

# Check exports directory
ls data/exports/
```

## 📈 Performance Tips

1. **Increase Batch Size** for faster processing:
   ```env
   BATCH_SIZE=100
   ```

2. **Use Local AI** to avoid rate limits:
   ```env
   USE_LOCAL_AI=true
   LOCAL_AI_PRIMARY=true
   ```

3. **Limit Message Age** to reduce duplicates:
   ```env
   MAX_MESSAGE_AGE_DAYS=7
   ```

## 🎯 Production Deployment

### Docker (Recommended)

```bash
# Build image
docker build -t telegram-extractor .

# Run container
docker run -d \
  --name telegram-extractor \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  telegram-extractor
```

### Systemd Service (Linux)

```bash
# Copy service file
sudo cp scripts/telegram-extractor.service /etc/systemd/system/

# Enable and start
sudo systemctl enable telegram-extractor
sudo systemctl start telegram-extractor

# Check status
sudo systemctl status telegram-extractor
```

### Scheduled Runs (Cron)

```bash
# Edit crontab
crontab -e

# Add daily run at 2 AM
0 2 * * * cd /path/to/telegram-extractor && /path/to/venv/bin/python main.py >> logs/cron.log 2>&1
```

## 💡 Pro Tips

1. **Test with one channel first** before adding many channels
2. **Check duplicate statistics** after first run to verify it's working
3. **Start with small message limits** (100-500) for testing
4. **Use screen or tmux** for long-running sessions
5. **Monitor logs** in `logs/extractor.log`

## 🆘 Get Help

- **GitHub Issues**: Report bugs or ask questions
- **Documentation**: Read the full README.md
- **Examples**: Check `examples/` directory
- **Tests**: Run tests to verify functionality

## ✅ Verification Checklist

After setup, verify everything works:

- [ ] Configuration loads without errors
- [ ] Database connects successfully
- [ ] Telegram authentication works
- [ ] Messages are extracted
- [ ] Duplicates are detected
- [ ] Data is saved to `data/`
- [ ] Statistics are displayed

## 🎉 You're Ready!

Congratulations! Your Telegram Knowledge Base Extractor is now running.

**What's next?**
- Customize your configuration
- Add more channels
- Enable AI processing
- Set up automated runs
- Export to Google Docs

---

**Need more help?** Check out:
- [Full README](README.md)
- [Implementation Guide](IMPLEMENTATION_GUIDE.md)
- [Project Structure](PROJECT_STRUCTURE.md)
- [API Documentation](docs/API.md)

Happy extracting! 🚀