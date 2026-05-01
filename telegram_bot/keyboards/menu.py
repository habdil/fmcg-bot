from __future__ import annotations

from telegram import ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["/analyze minyak 2 liter", "/crawl 3"],
            ["/insight minyak", "/trend"],
            ["/weekly", "/compare minyak | gula"],
            ["/alert", "/search gula"],
            ["/forecast gula", "/subscribe"],
            ["/menu"],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
