"""Device compatibility for tweaks.

The constraints themselves live in the tweak registry
(``TweakSpec.min_version`` / ``iphone_only`` / ``ipad_only``); this module
only evaluates them.
"""
from src.devicemanagement.constants import Version
from src.tweaks.registry import SPECS_BY_ID


def is_tweak_compatible(tweak_id, device_version: str, is_iphone: bool) -> bool:
    """Return True if the tweak makes sense on the given device.

    Tweak IDs outside the registry (special tweaks like PosterBoard) carry no
    constraints here and are always compatible.
    """
    spec = SPECS_BY_ID.get(tweak_id)
    if spec is None:
        return True
    if device_version and spec.min_version:
        try:
            if Version(device_version) < Version(spec.min_version):
                return False
        except Exception:
            pass
    if device_version and spec.max_version:
        try:
            if Version(device_version) > Version(spec.max_version):
                return False
        except Exception:
            pass
    if spec.ipad_only and is_iphone:
        return False
    if spec.iphone_only and not is_iphone:
        return False
    return True