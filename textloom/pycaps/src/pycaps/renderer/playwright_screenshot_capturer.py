import io
import math
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from playwright.sync_api import Page
    from PIL import Image

class PlaywrightScreenshotCapturer:
    @staticmethod
    def capture(page: 'Page', bounding_box: Dict) -> 'Image.Image':
        '''
        Captures a screenshot of the locator.
        It doesn't use locator.screenshot() because it adds some extra transparent pixels on the edges.
        This method is a workaround to avoid that.
        '''
        from PIL import Image

        x = bounding_box["x"]
        y = bounding_box["y"]
        width = bounding_box["width"]
        height = bounding_box["height"]

        # math.floor + 0.5 is used to round half up (round function in python uses some special rounding rules)
        left = math.floor(x + 0.5)
        top = math.floor(y + 0.5)
        right = math.floor(x + width + 0.5)
        bottom = math.floor(y + height + 0.5)

        clip = {
            'x': left,
            'y': top,
            'width': right - left,
            'height': bottom - top
        }
        png_bytes = page.screenshot(omit_background=True, type="png", animations="disabled", scale="device", clip=clip)
        image = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        return image
