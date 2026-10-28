"""Icons and screenshots the way the catalog serves them: a 10x10 icon and
128x64 screenshots, black on transparent. The server takes them as they
are, so this is the one place they are prepared."""

from pathlib import Path

from PIL import Image

from . import BundlerException

SCREEN = (128, 64)
SCREEN_SCALES = (1, 4, 8)
ICON = (10, 10)
BLACK_THRESHOLD = (15, 15, 15)
PIXEL_BLACK = (0, 0, 0, 255)
PIXEL_TRANSPARENT = (255, 255, 255, 0)


def _black_on_transparent(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    img.putdata([PIXEL_BLACK if p[:3] <= BLACK_THRESHOLD else PIXEL_TRANSPARENT for p in img.getdata()])
    return img


def icon(src: Path, dest: Path) -> None:
    img = Image.open(src).convert("RGBA")
    if img.size != ICON:
        raise BundlerException(f"icon {src.name} is {img.width}x{img.height}, expected 10x10")
    if any(p[:3] not in (PIXEL_BLACK[:3], PIXEL_TRANSPARENT[:3]) for p in img.getdata()):
        raise BundlerException(f"icon {src.name} is not black and white")
    dest.parent.mkdir(parents=True, exist_ok=True)
    _black_on_transparent(img).save(dest, "PNG")


def screenshot(src: Path, dest: Path) -> None:
    """A qFlipper screenshot (4x or 8x of the screen) down to the screen."""
    img = Image.open(src).convert("RGBA")
    if img.width < img.height:
        raise BundlerException(f"screenshot {src.name} is portrait")
    fx, fy = img.width // SCREEN[0], img.height // SCREEN[1]
    if fx != fy or fx not in SCREEN_SCALES or (img.width // fx, img.height // fy) != SCREEN:
        raise BundlerException(f"screenshot {src.name} is {img.width}x{img.height}, expected a 4x or 8x 128x64")
    if fx > 1:
        img = img.resize(SCREEN, resample=Image.Resampling.NEAREST)
    dest.parent.mkdir(parents=True, exist_ok=True)
    _black_on_transparent(img).save(dest, "PNG")
