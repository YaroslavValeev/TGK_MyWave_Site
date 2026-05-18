"""
Сборка карточек услуг для шаблонов: изображения + опциональные ролики из папки / YAML.
"""
from __future__ import annotations

from typing import Any, Callable, List

from app.services.images_resolver import (
    FALLBACK,
    resolve_card_images,
    rotate_images_to_cover_index,
    scan_folder_videos,
)

_SVC_SKIP = frozenset({"image_folder", "cover_index", "video_files"})


def build_services_list(
    services_config: List[dict],
    url_for_static: Callable[..., str],
) -> List[dict[str, Any]]:
    """
    Как на главной и на /services: cover, images, image_urls, videos, video_urls.
    """
    out: list[dict[str, Any]] = []
    for s in services_config:
        folder = s.get("image_folder", "")
        resolved = resolve_card_images(folder, fallback=FALLBACK)
        imgs = resolved.get("images") or [resolved["cover"]]
        try:
            ci = int(s.get("cover_index") or 0)
        except (TypeError, ValueError):
            ci = 0
        imgs = rotate_images_to_cover_index(imgs, ci)
        vids: list[str] = []
        for vf in s.get("video_files") or []:
            p = (vf or "").replace("\\", "/").strip()
            if p and p not in vids:
                vids.append(p)
        if not vids:
            vids = scan_folder_videos(folder)
        item = {
            **{k: v for k, v in s.items() if k not in _SVC_SKIP},
            "cover": imgs[0],
            "fallback": resolved["fallback"],
            "images": imgs,
            "image_urls": [url_for_static("static", filename=p) for p in imgs],
            "videos": vids,
            "video_urls": [url_for_static("static", filename=p) for p in vids],
        }
        out.append(item)
    return out
