# =============================================================================
# TELEGRAM KNOWLEDGE BASE EXTRACTOR - ENVIRONMENT CONFIGURATION
# =============================================================================
# Copy this file to .env and fill in your actual values
# Never commit .env to version control!

# =============================================================================
# TELEGRAM CONFIGURATION
# =============================================================================
# Get your API credentials from https://my.telegram.org/auth
# After logging in, go to 'API development tools' and create an application

TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_PHONE=+1234567890

# Channels to monitor (comma-separated, can use @ or channel ID)
# Example: @techcrunch,@hackernews,@airesearch
TELEGRAM_CHANNELS=@example_channel1,@example_channel2

# Session configuration
TELEGRAM_SESSION_NAME=extractor_session

# =============================================================================
# AI PROCESSING CONFIGURATION
# =============================================================================

# --- Claude API (Anthropic) ---
# Get your API key from https://console.anthropic.com/
ANTHROPIC_API_KEY=your_claude_api_key_here

# Claude model selection
# Options: claude-3-opus-20240229, claude-3-sonnet-20240229, claude-3-haiku-20240307
CLAUDE_MODEL=claude-3-sonnet-20240229

# Claude API settings
CLAUDE_MAX_TOKENS=300
CLAUDE_TEMPERATURE=0.2
CLAUDE_PROCESSING_DELAY=1

# --- Local AI Configuration (Ollama) ---
# Enable local AI models as primary or fallback
USE_LOCAL_AI=true

# If true, try local models first, use Claude as fallback
# If false, try Claude first, use local models as fallback
LOCAL_AI_PRIMARY=false

# Ollama server URL (default: http://localhost:11434)
OLLAMA_BASE_URL=http://localhost:11434

# Local model names (customize based on your installed models)
# Run 'ollama list' to see available models
LOCAL_MODEL_REASONING=deepseek-r1:32b
LOCAL_MODEL_GENERAL=llama3.1:8b
LOCAL_MODEL_EFFICIENT=phi3:mini
LOCAL_MODEL_CODING=codellama:34b
LOCAL_MODEL_LARGE_CONTEXT=llama3.3:70b

# Smart routing configuration
AUTO_MODEL_SELECTION=true
CLAUDE_FALLBACK_ENABLED=true
MAX_LOCAL_RETRIES=2
FALLBACK_THRESHOLD_TOKENS=2000

# =============================================================================
# PROCESSING CONFIGURATION
# =============================================================================

# Batch processing settings
BATCH_SIZE=50
MAX_WORKERS=4
PROCESSING_DELAY=1

# Message limits
MESSAGE_LIMIT_PER_CHANNEL=1000
MAX_MESSAGE_AGE_DAYS=30

# Duplicate prevention
ENABLE_DUPLICATE_PREVENTION=true
CONTENT_HASH_ENABLED=true
TEMPORAL_CLUSTERING_ENABLED=true

# =============================================================================
# STORAGE CONFIGURATION
# =============================================================================

# Data directory
DATA_DIRECTORY=./data

# JSON storage
ENABLE_JSON_STORAGE=true
JSON_FILE_PATH=./data/messages.json

# CSV export
ENABLE_CSV_EXPORT=true
CSV_FILE_PATH=./data/exports/messages.csv

# Google Docs export (optional)
ENABLE_GOOGLE_DOCS_EXPORT=false
GOOGLE_DOCS_CREDENTIALS_PATH=./credentials/google_credentials.json
GOOGLE_DOCS_FOLDER_ID=your_folder_id_here

# =============================================================================
# NOTIFICATION CONFIGURATION (Optional)
# =============================================================================

# Enable Telegram notifications
ENABLE_NOTIFICATIONS=false
NOTIFICATION_CHANNEL=@your_notification_channel

# Notification settings
NOTIFY_ON_START=true
NOTIFY_ON_COMPLETION=true
NOTIFY_ON_ERROR=true
NOTIFY_BATCH_SUMMARY=true

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Log file path
LOG_FILE=./logs/extractor.log

# Enable colored console output
ENABLE_COLORED_LOGS=true

# Enable emoji in logs
ENABLE_EMOJI_LOGS=true

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# SQLite database settings
DB_PROCESSED_MESSAGES=./data/processed_messages.db
DB_CONNECTION_TIMEOUT=30
DB_MAX_CONNECTIONS_PER_DB=5
DB_CONNECTION_MAX_AGE=3600

# =============================================================================
# PERFORMANCE CONFIGURATION
# =============================================================================

# Memory management
ENABLE_MEMORY_MANAGER=true
MAX_MEMORY_USAGE_MB=1024
CACHE_SIZE_MB=256

# Async settings
ASYNC_SEMAPHORE_LIMIT=10
ASYNC_BATCH_SIZE=20

# Connection pooling
ANTHROPIC_POOL_SIZE=5
OPENAI_POOL_SIZE=5

# =============================================================================
# DEVELOPMENT/DEBUG CONFIGURATION
# =============================================================================

# Debug mode (more verbose logging)
DEBUG_MODE=false

# Dry run (don't actually process, just test)
DRY_RUN=false

# Skip AI processing (for testing extraction only)
SKIP_AI_PROCESSING=false

# =============================================================================
# ADVANCED CONFIGURATION
# =============================================================================

# Event system configuration
ENABLE_EVENT_SYSTEM=true
EVENT_BATCH_SIZE=100

# Autonomous error handling
ENABLE_AUTONOMOUS_DEBUG=false
AUTO_FIX_ERRORS=false

# Performance monitoring
ENABLE_PERFORMANCE_MONITORING=true
MONITOR_INTERVAL_SECONDS=60

# =============================================================================
# NOTES
# =============================================================================
# 1. Never commit the actual .env file to version control
# 2. Add .env to your .gitignore file
# 3. For production, use a secrets management service
# 4. Restart the application after changing environment variables
# 5. Use strong, unique API keys for security
# 6. Regularly rotate your API keys
# 7. Monitor your API usage and costs
# =============================================================================