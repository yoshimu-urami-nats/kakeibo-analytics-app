# ホゲの中核

# account/utils/guest_utils.py

from __future__ import annotations


def is_guest(user) -> bool:
    return bool(getattr(user, "is_authenticated", False) and getattr(user, "username", "") == "guest")


def mask_shop_name(shop: str) -> str:
    if not shop:
        return ""
    # 例：先頭1文字だけ残して伏せる（必要ならルール変更OK）
    head = shop[:1]
    return f"HOGE-{head}****"