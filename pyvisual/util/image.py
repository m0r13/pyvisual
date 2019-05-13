import os
import time
from PIL import Image

from pyvisual import assets

def generate_screenshot_path(suffix=".png"):
    name = time.strftime("%Y-%m-%d_%H-%M-%S") + suffix
    return os.path.join(assets.SCREENSHOT_PATH, name)

def save_screenshot(texture, path=None):
    if path is None:
        path = generate_screenshot_path()
    image = Image.fromarray(texture)
    image.save(path)
    print("Saved screenshot %s" % path)

