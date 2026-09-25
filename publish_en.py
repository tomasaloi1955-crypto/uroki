# -*- coding: utf-8 -*-
"""Английский канал: привычная команда поверх общего publish.py.

    python publish_en.py schedule   ==   python publish.py en schedule
"""

import sys

import publish
from shorts_en import LANG


def load_state():
    return publish.load_state(LANG)


def main_schedule(nums, hours=None):
    return publish.schedule(LANG, nums, hours)


if __name__ == "__main__":
    sys.argv.insert(1, "en")
    publish.main()
