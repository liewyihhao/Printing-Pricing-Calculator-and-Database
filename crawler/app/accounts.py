"""Excard account definitions for parallel crawling.

Each account = its own login + its own Playwright storage_state file, giving a
SEPARATE server-side session. Two crawls on two accounts run independently with
no cross-corruption (unlike two tabs on one login). Account 1 keeps the original
session_state.json so existing/running crawls are unaffected.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import config


@dataclass(frozen=True)
class Account:
    id: int
    username: str
    password: str
    state_file: str


def _creds(account_id: int):
    return {
        1: (config.USERNAME, config.PASSWORD),
        2: (config.USERNAME_2, config.PASSWORD_2),
        3: (config.USERNAME_3, config.PASSWORD_3),
    }.get(account_id)


def get(account_id: int = 1) -> Account:
    creds = _creds(account_id)
    if creds is None:
        raise KeyError(f"Unknown account_id {account_id} (supported: 1, 2, 3)")
    username, password = creds
    if not (username and password):
        raise RuntimeError(f"Account {account_id} not configured — set "
                           f"EXCARD_USERNAME_{account_id} and "
                           f"EXCARD_PASSWORD_{account_id} in crawler/.env")
    # Account 1 keeps the original session file so existing crawls are unaffected.
    sf = "session_state.json" if account_id == 1 else f"session_state{account_id}.json"
    return Account(account_id, username, password, str(config.OUTPUT_DIR / sf))
