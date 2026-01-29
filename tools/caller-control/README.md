# Claude Code Remote (Caller Control)

Control Claude Code from your phone via a web-based terminal.

## Features

- PTY wrapper spawns real Claude Code CLI
- WebSocket streams terminal I/O in real-time
- Mobile-optimized UI with touch controls
- Works over any network with tunnel

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start server
python3 main.py

# In another terminal, create tunnel for remote access
cloudflared tunnel --url http://localhost:8080
```

Open the tunnel URL on your phone.

## Architecture

```
Phone Browser → Cloudflare Tunnel → FastAPI Server → PTY → Claude Code
     ↑                                    ↓
     └──────────── WebSocket ←───────────┘
```

## Files

- `main.py` - FastAPI backend with PTY management
- `static/index.html` - xterm.js terminal UI
- `requirements.txt` - Python dependencies

## Mobile Controls

| Button | Action |
|--------|--------|
| Ctrl+C | Interrupt (SIGINT) |
| Ctrl+D | EOF |
| ESC | Escape key |
| TAB | Autocomplete |
| ↑/↓ | History navigation |
| y/n | Quick yes/no |
| Enter | Submit |

## Requirements

- Python 3.10+
- Claude Code CLI installed
- cloudflared (for remote access)

## Local Only

For local network access (no tunnel):

```bash
python3 main.py
# Access at http://<your-ip>:8080
```

## Notes

- Each WebSocket connection spawns a new Claude Code session
- Sessions are cleaned up on disconnect
- Server runs on port 8080 by default
