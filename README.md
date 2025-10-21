# Instagram + Telegram + VK Auto-Poster Bot

A Telegram bot that automatically posts photos to Instagram, Telegram groups, and VK. The bot receives photos and captions from an admin via Telegram DMs and publishes them to selected platforms simultaneously.

## Features

- 📸 **Photo Support**: Single photos or carousels/albums (2-10 photos)
- 🔄 **Multi-Platform**: Posts to Instagram, Telegram, and/or VK ✨ **NEW!**
- 🎯 **Platform Selection**: Choose specific platforms or post to all at once
- 🖼️ **Auto Processing**: Resizes images to optimal formats (1080x1080 or 1080x1350)
- 🔍 **Article Detection**: Automatically finds product article numbers in photos
- 🔐 **Secure**: Only admin can use the bot
- 💾 **Session Management**: Saves Instagram login sessions
- 🧹 **Auto Cleanup**: Automatically cleans temporary files
- ⏰ **Scheduling**: Post now or schedule for later
- 🤖 **AI Assistant**: Get help with captions using Google AI

## Requirements

- Python 3.10+
- Telegram Bot Token
- Instagram Account (optional)
- Telegram Group ID (optional)
- VK Group and Access Token (optional) ✨ **NEW!**
- Google AI API Key (optional, for AI features)

## Installation

1. **Clone or download the project**
   ```bash
   git clone <repository-url>
   cd auto-poster-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   - Copy `env.example` to `.env`
   - Fill in your credentials:
   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ADMIN_USER_ID=123456789
   TELEGRAM_GROUP_ID=@your_group_or_-1001234567890
   INSTAGRAM_USERNAME=your_instagram_username
   INSTAGRAM_PASSWORD=your_instagram_password
   VK_ACCESS_TOKEN=your_vk_access_token          # ✨ NEW!
   VK_GROUP_ID=your_vk_group_id                  # ✨ NEW!
   GOOGLE_API_KEY=your_google_ai_api_key         # Optional
   ```
   
   📖 **For VK setup**, see [INSTALL_VK.md](INSTALL_VK.md) and [VK_SETUP.md](VK_SETUP.md)

4. **Create necessary directories**
   ```bash
   mkdir sessions uploads
   ```

## Configuration

### Getting Telegram Bot Token

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Use `/newbot` command
3. Follow instructions to create your bot
4. Copy the token to your `.env` file

### Getting Admin User ID

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. Send any message to get your user ID
3. Copy the ID to your `.env` file

### Getting Telegram Group ID

1. Add your bot to the group
2. Make the bot an admin (optional but recommended)
3. Send a message in the group
4. Visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
5. Find the chat ID in the response (starts with -100 for groups)

### Instagram Account

- Use your existing Instagram username and password
- The bot will handle login and session management
- Sessions are saved in the `sessions/` directory

### VK Setup ✨ **NEW!**

See detailed instructions in [VK_SETUP.md](VK_SETUP.md)

**Quick steps:**
1. Create a VK app at https://vk.com/apps?act=manage
2. Get your group ID from https://vk.com/psyqk (use https://regvk.com/id/)
3. Generate access token with `wall`, `photos`, `groups` permissions
4. Add to `.env` file

For complete setup guide: [INSTALL_VK.md](INSTALL_VK.md)

## Usage

1. **Start the bot**
   ```bash
   python main.py
   ```

2. **Create a post**
   - Send `/start` to the bot
   - Press **"🚀 Начать публикацию"**
   - Choose post type:
     - **📷 Одиночный пост** - single photo
     - **📸 Массовый пост** - multiple photos (album/carousel)
   
3. **Select platform(s)**
   - **📷 Instagram** - post only to Instagram
   - **💬 Telegram** - post only to Telegram
   - **🔵 VK** - post only to VK ✨ **NEW!**
   - **🔀 Все платформы** - post to all platforms at once ✨ **NEW!**

4. **Article detection** (optional)
   - Choose if bot should find product article numbers in photos
   - Bot will automatically detect and add them to caption

5. **Upload photos**
   - Send 1-10 photos
   - Bot will confirm each photo received

6. **Send caption**
   - Send the text for your post
   - Bot will show preview

7. **Publish**
   - **⚡ Опубликовать сейчас** - publish immediately
   - **⏰ Запланировать** - schedule for later
   - **🤖 Помощь ИИ** - get AI assistance with caption

8. **Check status**
   - Use `/status` to check bot status
   - Use `/help` for available commands

## Commands

- `/start` - Start the bot and show main menu
- `/help` - Show help message with all features
- `/status` - Check bot and service status (Instagram, Telegram, VK)
- `/cancel` - Cancel current operation and clear state

## Workflow

1. **Admin selects post type** → Single or multiple photos
2. **Admin selects platform(s)** → Instagram, Telegram, VK, or all
3. **Admin chooses article detection** → Optional product number recognition
4. **Admin sends photos** → Bot saves them temporarily
5. **Admin sends caption** → Bot processes photos (resize, format)
6. **Bot shows preview** → Admin confirms or edits
7. **Bot posts to selected platforms:**
   - **Instagram** → Single photo or carousel
   - **Telegram** → Photo or media group
   - **VK** → Photo or album ✨ **NEW!**
8. **Bot sends notification** → Success/error message to admin
9. **Bot cleans up** → Removes temporary files

## Image Processing

- **Single photos**: Resized to 1080x1080 (square) or 1080x1350 (story format)
- **Multiple photos**: All resized to 1080x1080 for carousel
- **Format**: Converted to JPEG with 95% quality
- **Size limit**: Maximum 8MB per image
- **Supported formats**: JPEG, PNG, WEBP

## File Structure

```
auto-poster-bot/
├── main.py                  # Bot entry point
├── config.py                # Configuration and constants
├── handlers/
│   └── admin_handler.py     # Admin message handling
├── services/
│   ├── instagram_service.py # Instagram API integration
│   ├── telegram_service.py  # Telegram group posting
│   ├── vk_service.py        # VK group posting ✨ NEW!
│   └── ai_service.py        # Google AI integration
├── utils/
│   ├── image_processor.py   # Image processing utilities
│   └── article_extractor.py # Article number detection
├── sessions/                # Instagram session files
├── uploads/                 # Temporary photo storage
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (create from env.example)
├── env.example             # Example environment file
├── README.md               # This file
├── VK_SETUP.md             # VK setup guide ✨ NEW!
├── INSTALL_VK.md           # VK installation guide ✨ NEW!
└── .gitignore              # Git ignore rules
```

## Security Notes

- Never commit your `.env` file
- Keep your Instagram credentials secure
- Only the admin user ID can use the bot
- Sessions are stored locally and encrypted by instagrapi

## Troubleshooting

### Common Issues

1. **Instagram login fails**
   - Check username/password
   - Try logging in manually first
   - Clear sessions directory and retry

2. **Telegram posting fails**
   - Check bot token
   - Ensure bot is added to the group
   - Verify group ID format

3. **VK posting fails** ✨ **NEW!**
   - Check VK access token
   - Verify group ID is correct
   - Ensure you're admin of the group
   - Check token permissions (wall, photos, groups)
   - See [VK_SETUP.md](VK_SETUP.md) for troubleshooting

4. **Image processing errors**
   - Check image format and size
   - Ensure uploads directory exists
   - Check file permissions

5. **Article detection not working**
   - Make sure pytesseract is installed
   - Install Tesseract OCR on your system
   - Check photo quality and text visibility

### Logs

The bot logs all activities. Check the console output for detailed error messages.

## Deployment

### Local Development
```bash
python main.py
```

### Production (VPS/Cloud)
1. Install dependencies
2. Set up environment variables
3. Run with process manager (systemd, PM2, etc.)
4. Consider using a virtual environment

### Docker (Optional)
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

## License

This project is for educational and personal use. Please respect Instagram's and Telegram's terms of service.

## Documentation

- [README.md](README.md) - This file (overview and basic setup)
- [START_HERE.md](START_HERE.md) - Quick orientation guide ✨ **NEW!**
- [QUICK_START_VK.md](QUICK_START_VK.md) - 5-minute VK setup ✨ **NEW!**
- [INSTALL_VK.md](INSTALL_VK.md) - Complete VK installation guide ✨ **NEW!**
- [VK_SETUP.md](VK_SETUP.md) - Detailed VK configuration ✨ **NEW!**
- [FAQ_VK.md](FAQ_VK.md) - Frequently Asked Questions about VK ✨ **NEW!**
- [TROUBLESHOOTING_VK.md](TROUBLESHOOTING_VK.md) - Fix VK errors ✨ **NEW!**
- [EXAMPLES.md](EXAMPLES.md) - Usage examples ✨ **NEW!**
- [CHANGELOG_VK.md](CHANGELOG_VK.md) - Version history ✨ **NEW!**
- [ARTICLE_DETECTION_IMPROVEMENTS.md](ARTICLE_DETECTION_IMPROVEMENTS.md) - Article detection features
- [BUSINESS_PROCESS.md](BUSINESS_PROCESS.md) - Bot workflow and business logic
- [AI_SETUP.md](AI_SETUP.md) - Google AI assistant setup

## What's New in VK Integration

### Version with VK Support ✨

**New Features:**
- ✅ Post to VK groups
- ✅ Single photo and album support (up to 10 photos)
- ✅ Platform selection: Instagram, Telegram, VK, or all at once
- ✅ Automatic article number detection and inclusion
- ✅ VK connection testing on bot startup
- ✅ Comprehensive error handling for VK

**New Files:**
- `services/vk_service.py` - VK API integration
- `VK_SETUP.md` - Detailed VK setup instructions
- `INSTALL_VK.md` - Quick installation guide

**Updated Files:**
- `requirements.txt` - Added `vk-api` library
- `config.py` - Added VK configuration
- `handlers/admin_handler.py` - Added VK platform support
- `main.py` - Added VK initialization

## Support

For issues and questions:
1. Check the logs for error messages
2. Verify your configuration in `.env`
3. Test with a simple photo first
4. Check Instagram, Telegram, and VK service status
5. For VK issues, see [VK_SETUP.md](VK_SETUP.md) troubleshooting section


