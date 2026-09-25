# -*- coding: utf-8 -*-
"""Английский канал в облаке: обёртка над build_and_publish.py."""

import sys

if __name__ == "__main__":
    sys.argv.insert(1, "en")
    import build_and_publish

    build_and_publish.main()
