import os
import time
from PIL import Image

from pyvisual import assets

def save_screenshot(texture):
    image = Image.fromarray(texture)
    name = "%s.png" % (time.strftime("%Y-%m-%d_%H-%M-%S"))
    path = os.path.join(assets.SCREENSHOT_PATH, name)
    image.save(path)
    print("Saved screenshot %s" % path)

