"""Власні винятки та переклад помилок у зрозумілі повідомлення."""
import errno

import requests
from minecraft_launcher_lib.exceptions import (
    AccountNotOwnMinecraft,
    AzureAppNotPermitted,
    FileOutsideMinecraftDirectory,
    VersionNotFound,
)

import config


class AuthError(Exception):
    """Помилка входу через Microsoft."""


class InputError(Exception):
    """Некоректні дані, введені користувачем."""


class JavaNotFoundError(Exception):
    """Java не знайдено."""


def friendly_error(exc: Exception) -> str:
    if isinstance(exc, (AuthError, JavaNotFoundError, InputError)):
        return str(exc)
    if isinstance(exc, AzureAppNotPermitted):
        return ("Ваш Azure-застосунок ще не має дозволу на Minecraft API.\n"
                "Подайте заявку: https://aka.ms/mce-reviewappid і дочекайтеся "
                "схвалення (див. README, розділ 4).")
    if isinstance(exc, AccountNotOwnMinecraft):
        return ("Цей Microsoft-акаунт не володіє Minecraft: Java Edition.\n"
                "Увійдіть іншим акаунтом (кнопка «Вийти») або придбайте гру.")
    if isinstance(exc, VersionNotFound):
        return "Обрану версію Minecraft не знайдено. Оберіть іншу версію зі списку."
    if isinstance(exc, FileOutsideMinecraftDirectory):
        return "Бібліотека відмовилась писати файл поза папкою гри. Оберіть іншу папку гри."
    if isinstance(exc, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
        return "Немає з'єднання з інтернетом або сервери Mojang/Microsoft недоступні. Перевірте мережу й спробуйте ще раз."
    if isinstance(exc, requests.exceptions.RequestException):
        return f"Помилка мережі під час завантаження: {exc}"
    if isinstance(exc, PermissionError):
        return f"Немає прав на запис у папку гри ({config.DATA_DIR} або обрана папка). Оберіть іншу папку."
    if isinstance(exc, OSError) and exc.errno == errno.ENOSPC:
        return "Недостатньо місця на диску."
    if isinstance(exc, (KeyError, ValueError)):
        return ("Microsoft/Xbox/Minecraft повернули неочікувану відповідь. Можливі причини: "
                "неправильний Client ID чи Redirect URI, акаунт без Xbox-профілю, "
                f"обмеження регіону/віку акаунта. Технічно: {type(exc).__name__}: {exc}")
    return f"Непередбачена помилка: {type(exc).__name__}: {exc}"
