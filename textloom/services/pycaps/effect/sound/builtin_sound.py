from .sound import Sound
import os

_BUILTIN_SOUNDS_PATH = os.path.join(os.path.dirname(__file__), "presets")

def _build_builtin_sound(name: str) -> Sound:
    return Sound(name, os.path.join(_BUILTIN_SOUNDS_PATH, name + ".mp3"))

class BuiltinSound:
    CLICK = _build_builtin_sound("click")
    CLICK_LIGHT = _build_builtin_sound("click-light")

    DING = _build_builtin_sound("ding")
    DING_LONG = _build_builtin_sound("ding-long")
    DING_SHORT = _build_builtin_sound("ding-short")

    GLITCH = _build_builtin_sound("glitch")
    GLITCH_STATIC = _build_builtin_sound("glitch-static")

    HEART_BEAT = _build_builtin_sound("heart-beat")

    HIT_INTENSE = _build_builtin_sound("hit-intense")
    HIT_STRONG = _build_builtin_sound("hit-strong")

    POP = _build_builtin_sound("pop")
    POP_2 = _build_builtin_sound("pop-2")

    SLIDE_PAPER = _build_builtin_sound("slide-paper")

    SWOOSH = _build_builtin_sound("swoosh")

    WHOOSH = _build_builtin_sound("whoosh")
    WHOOSH_2 = _build_builtin_sound("whoosh-2")
    WHOOSH_DEEP = _build_builtin_sound("whoosh-deep")

    @staticmethod
    def get_by_name(name: str) -> Sound | None:
        name = name.upper().replace("-", "_").replace(" ", "_")
        try:
            return getattr(BuiltinSound, name)
        except AttributeError:
            return None
