#!/usr/bin/env python3
import time, os, sys, platform
from datetime import datetime, timezone
import psutil
from aw_core.models import Event
from aw_client import ActivityWatchClient

OS = platform.system()

if OS == "Windows":
    import win32gui, win32process

    def get_active_window_info():
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None
        title = win32gui.GetWindowText(hwnd) or ""
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            p = psutil.Process(pid)
            exe = p.exe()  # full path
        except Exception:
            return None
        return {"pid": pid, "title": title, "exe_path": exe}

else:
    #TODO: Implement for Linux as well!
    def get_active_window_info():
        return None

def main(pulsetime=5.0, interval=0.5):
    # Use the canonical window event type so AW tools recognize it
    client = ActivityWatchClient("aw-watcher-window", testing=False)
    bucket_id = f"aw-watcher-window_{client.client_hostname}"
    client.create_bucket(bucket_id, event_type="window")

    last_payload = None

    with client:
        while True:
            info = get_active_window_info()
            if info:
                title = info["title"]
                exe_path = info["exe_path"]

                app_name = os.path.basename(exe_path) if exe_path else ""

                # Put the *full path* into data.app so AW's Categorizer can regex on it.
                data = {"app": exe_path or app_name, "title": title or ""}
                event = Event(timestamp=datetime.now(timezone.utc), data=data)

                # Only heartbeat when payload actually changes (window/app switch)
                # Otherwise, heartbeats will merge automatically (pulsetime) on identical data
                if data != last_payload:
                    last_payload = data
                print(data)
                client.heartbeat(bucket_id, event, pulsetime=pulsetime, queued=True, commit_interval=60.0)

            time.sleep(interval)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
