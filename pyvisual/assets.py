
import os
import glob
import time

ASSET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
SHADER_PATH = os.path.join(ASSET_PATH, "shader")
SAVE_PATH = os.path.join(ASSET_PATH, "saves")
SCREENSHOT_PATH = os.path.join(ASSET_PATH, "screenshots")

os.makedirs(SAVE_PATH, exist_ok=True)
os.makedirs(SCREENSHOT_PATH, exist_ok=True)

def get_shader_path(name):
    return os.path.join(SHADER_PATH, name)

def glob_paths(wildcard):
    paths = []
    for path in glob.glob(os.path.join(ASSET_PATH, wildcard)):
        paths.append(os.path.relpath(path, ASSET_PATH))
    return paths

class FileWatcher:
    CHECK_INTERVAL = 1.0

    def __init__(self, path):
        self.path = path
        self.last_check = 0

    def has_changed(self):
        t = time.time()
        if t - self.CHECK_INTERVAL > self.last_check:
            last_change = os.path.getmtime(self.path)
            changed = last_change > self.last_check
            self.last_check = t
            if changed:
                return True
        return False

