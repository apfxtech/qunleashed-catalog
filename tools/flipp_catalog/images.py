"""Icons and screenshots the way the catalog serves them: a 10x10 icon and
128x64 screenshots, black on transparent, written as 1-bit PNGs: the app
colours them itself. The server takes them as they are, so this is the one
place they are prepared."""

from pathlib import Path

from PIL import Image

from . import BundlerException

SCREEN = (128, 64)
SCREEN_SCALES = (1, 4, 8)
ICON = (10, 10)
BLACK_THRESHOLD = (15, 15, 15)
PIXEL_BLACK = (0, 0, 0, 255)
PIXEL_TRANSPARENT = (255, 255, 255, 0)
INDEX_BLACK, INDEX_TRANSPARENT = 0, 1


def _black_on_transparent(img: Image.Image) -> Image.Image:
    """Two palette entries, black and a transparent one: saved as a 1-bit PNG."""
    out = Image.new("P", img.size)
    out.putpalette([*PIXEL_BLACK[:3], *PIXEL_TRANSPARENT[:3]])
    out.putdata([INDEX_BLACK if p[:3] <= BLACK_THRESHOLD else INDEX_TRANSPARENT for p in img.convert("RGBA").getdata()])
    return out


def _save(img: Image.Image, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    _black_on_transparent(img).save(dest, "PNG", bits=1, transparency=INDEX_TRANSPARENT)


def icon(src: Path, dest: Path) -> None:
    img = Image.open(src).convert("RGBA")
    if img.size != ICON:
        raise BundlerException(f"icon {src.name} is {img.width}x{img.height}, expected 10x10")
    if any(p[:3] not in (PIXEL_BLACK[:3], PIXEL_TRANSPARENT[:3]) for p in img.getdata()):
        raise BundlerException(f"icon {src.name} is not black and white")
    _save(img, dest)


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
    _save(img, dest)
