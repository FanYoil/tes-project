import json
import os
from config import ADMIN_USER_IDS, DEFAULT_GITHUB_TOKEN

DATA_FILE = "data/user_tokens.json"


def _load_data() -> dict:
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        try:
            return json.load(f)
        except Exception:
            return {}


def _save_data(data: dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS


def get_github_token(user_id: int) -> str:
    data = _load_data()
    return data.get(str(user_id), {}).get("github_token", DEFAULT_GITHUB_TOKEN)


def set_github_token(user_id: int, token: str):
    data = _load_data()
    if str(user_id) not in data:
        data[str(user_id)] = {}
    data[str(user_id)]["github_token"] = token
    _save_data(data)


def remove_github_token(user_id: int):
    data = _load_data()
    if str(user_id) in data:
        data[str(user_id)].pop("github_token", None)
        _save_data(data)


def get_linked_repo(user_id: int) -> str | None:
    data = _load_data()
    return data.get(str(user_id), {}).get("linked_repo")


def set_linked_repo(user_id: int, repo_full_name: str):
    if not repo_full_name or "/" not in repo_full_name:
        raise ValueError(f"Format repo tidak valid: '{repo_full_name}'. Gunakan format owner/repo (contoh: username/my-repo)")
    data = _load_data()
    if str(user_id) not in data:
        data[str(user_id)] = {}
    data[str(user_id)]["linked_repo"] = repo_full_name
    _save_data(data)


def get_terminal_cwd(user_id: int) -> str:
    data = _load_data()
    return data.get(str(user_id), {}).get("terminal_cwd", "/tmp/telegram-shell")


def set_terminal_cwd(user_id: int, cwd: str):
    data = _load_data()
    if str(user_id) not in data:
        data[str(user_id)] = {}
    data[str(user_id)]["terminal_cwd"] = cwd
    _save_data(data)
