from cores.platforms.base import BugBountyPlatform, PlatformAction, SubmissionResult
from cores.platforms.bugcrowd import Bugcrowd
from cores.platforms.hackerone import HackerOne
from cores.platforms.intigriti import Intigriti
from cores.platforms.synack import Synack
from cores.platforms.yeswehack import YesWeHack

PLATFORM_REGISTRY: dict[str, type[BugBountyPlatform]] = {
    "hackerone": HackerOne,
    "bugcrowd": Bugcrowd,
    "intigriti": Intigriti,
    "yeswehack": YesWeHack,
    "synack": Synack,
}


def get_platform(platform_id: str) -> BugBountyPlatform | None:
    cls = PLATFORM_REGISTRY.get(platform_id)
    if cls is None:
        return None
    return cls()


def get_platform_for_action(platform_id: str, action: str) -> BugBountyPlatform | None:
    platform = get_platform(platform_id)
    if platform is None:
        return None
    if not platform.supports_action(action):
        return None
    return platform
