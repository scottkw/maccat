"""BraveCollector — thin subclass of ChromiumBaseCollector for Brave Browser.

All profile-scan logic lives in chromium.py. This module provides Brave-specific
paths, section title, and component denylist.
"""
from __future__ import annotations

from pathlib import Path

from maccat.collectors.chromium import COMPONENT_DENYLIST, ChromiumBaseCollector

__all__ = ["BraveCollector", "BRAVE_COMPONENT_DENYLIST"]

# Source: https://github.com/brave/brave-browser/wiki/Brave-Components
# 20 confirmed component extension IDs — all 32-char lowercase alpha strings.
BRAVE_COMPONENT_DENYLIST: frozenset[str] = frozenset({
    "eeigpngbgcognadeebkilcpcaedhellh",  # Autofill States Data
    "iodkpdagapdfkphljnddpjlldadblomo",  # Brave Ad Block Updater
    "gkboaolpopklhgplhaaiboijnklogmbc",  # Brave Ad Block List Catalog
    "mfddibmblmbccpadfndgakiopmmhebop",  # Brave Ad Block Resources Library
    "afalakplffnnnlkncjhbmahjfjhmlkal",  # Brave Local Data Updater
    "cldoidikboihgcjfkhdeidbpclkineef",  # Brave Tor Client Updater (x86)
    "cpoalefficncklhjfpglfiplenlpccdb",  # Brave Tor Client Updater (arm64)
    "biahpgbdmdkfgndcmfiipgcebobojjkp",  # Brave Tor Client Updater (arm)
    "kkjipiepeooghlclkedllogndmohhnhi",  # Brave User Model Installer
    "giekcmmlnklenlaomppkphknjmnnpneh",  # Certificate Error Assistant
    "hfnkpimlhhgieaddgfemjhofmfblmnib",  # CRLSet
    "ggkkehgbnfjpeggfpleeakpidbkibbmn",  # Crowd Deny
    "khaoiebndkojlmppeemjhbpbandiljpe",  # File Type Policies
    "jamhcnnkihinmdlkakkaopbjbbcngflc",  # Hyphenation
    "laoigpblnllgcgjnjnllmfolckpjlhki",  # MEI Preload
    "gccbbckogglekeggclmmekihdgdpdgoe",  # NTP Sponsored Images
    "aoojcmojmmcbpfgoecoadbdpnagfchel",  # NTP Background Images
    "jflookgnkcckhobaglndicnbbgbonegd",  # Safety Tips
    "oimompecagnajdejgnnjijobebaeigek",  # Widevine
    "ojhpjlocmbogdgmfpkhlaaeamibhnphh",  # Zxcvbn Data Dictionaries
})

_BASE = Path.home() / "Library/Application Support/BraveSoftware/Brave-Browser"
_TITLE = "Brave Browser Extensions"


class BraveCollector(ChromiumBaseCollector):
    """Thin subclass — Brave-specific paths and denylist."""

    _base = _BASE
    _title = _TITLE
    _denylist = COMPONENT_DENYLIST | BRAVE_COMPONENT_DENYLIST
    _browser_name = "Brave Browser"
