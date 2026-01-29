#!/usr/bin/env python3
"""
Claude Code Remote - Control Claude Code from your phone.

FastAPI backend with PTY wrapper for Claude Code CLI.
Streams I/O over WebSocket to xterm.js frontend.

Usage:
    python3 main.py
    # Then expose with tunnel: cloudflared tunnel --url http://localhost:8080
"""
import asyncio
import fcntl
import json
import os
import pty
import select
import signal
import struct
import termios
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="Claude Code Remote")

# Active PTY sessions
sessions: dict[str, dict] = {}


def set_pty_size(fd: int, rows: int, cols: int) -> None:
    """Set PTY window size."""
    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)


async def read_pty_output(master_fd: int, websocket: WebSocket) -> None:
    """Read PTY output and stream to WebSocket."""
    loop = asyncio.get_event_loop()

    # Set non-blocking mode
    flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    while True:
        try:
            # Wait for data with select (non-blocking check)
            readable = await loop.run_in_executor(
                None, lambda: select.select([master_fd], [], [], 0.1)[0]
            )
            if not readable:
                await asyncio.sleep(0.01)  # Yield to event loop
                continue

            # Read available data
            data = os.read(master_fd, 4096)
            if not data:
                break
            # Send as text (UTF-8)
            await websocket.send_text(data.decode("utf-8", errors="replace"))
        except BlockingIOError:
            await asyncio.sleep(0.01)
            continue
        except OSError:
            break
        except WebSocketDisconnect:
            break


@app.websocket("/ws/terminal")
async def terminal_websocket(websocket: WebSocket):
    """WebSocket endpoint for terminal session."""
    await websocket.accept()

    # Create PTY pair
    master_fd, slave_fd = pty.openpty()

    # Set initial size
    set_pty_size(master_fd, 24, 80)

    # Fork and exec claude
    pid = os.fork()
    if pid == 0:
        # Child process
        os.close(master_fd)
        os.setsid()
        os.dup2(slave_fd, 0)  # stdin
        os.dup2(slave_fd, 1)  # stdout
        os.dup2(slave_fd, 2)  # stderr
        os.close(slave_fd)

        # Execute claude CLI
        os.execlp("claude", "claude")

    # Parent process
    os.close(slave_fd)

    session_id = str(pid)
    sessions[session_id] = {"pid": pid, "master_fd": master_fd}

    # Start reading PTY output
    read_task = asyncio.create_task(read_pty_output(master_fd, websocket))

    try:
        while True:
            message = await websocket.receive_text()

            # Check for control messages (JSON)
            try:
                data = json.loads(message)
                msg_type = data.get("type")

                if msg_type == "resize":
                    rows = data.get("rows", 24)
                    cols = data.get("cols", 80)
                    set_pty_size(master_fd, rows, cols)
                    continue
                elif msg_type == "interrupt":
                    # Send SIGINT to Claude
                    os.kill(pid, signal.SIGINT)
                    continue
            except json.JSONDecodeError:
                pass

            # Regular input - write to PTY
            os.write(master_fd, message.encode("utf-8"))

    except WebSocketDisconnect:
        pass
    finally:
        # Cleanup
        read_task.cancel()
        os.close(master_fd)
        try:
            os.kill(pid, signal.SIGTERM)
            os.waitpid(pid, 0)
        except OSError:
            pass
        sessions.pop(session_id, None)


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "sessions": len(sessions)}


# Serve static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """Serve main page."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Claude Code Remote - static files not found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
