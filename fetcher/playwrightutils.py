"""A collection of utilities for working with Playwright."""

import asyncio
import contextlib
from enum import Enum
import os
import pathlib
import playwright.async_api
from playwright.async_api import async_playwright
import shutil
import time
import typing
from typing import AsyncIterator, Optional, TypedDict

from .contextextra import async_closing


class Browser(Enum):
    FIREFOX = 1
    CHROMIUM = 2
    WEBKIT = 3


def get_browser_type(
        pw: playwright.async_api.Playwright,
        browser_type: Browser) -> playwright.async_api.BrowserType:
    if browser_type == Browser.FIREFOX:
        return pw.firefox
    elif browser_type == Browser.CHROMIUM:
        return pw.chromium
    elif browser_type == Browser.WEBKIT:
        return pw.webkit
    raise Exception(f"Unknown browser type: {browser_type}")


def playwright_cookie_jar_to_requests_cookies(
        playwright_cookies: list[playwright.async_api.Cookie]) -> dict:
    """
    Transforms a cookie jar from Playwright into a Requests-compatible dict.

    :param playwright_cookies list[dict]
    :rtype dict
    """
    return {c['name']: c['value'] for c in playwright_cookies}


# Using an async context manager, because it's more natural:
# * The client can now define the timeout using an orthogonal asyncio.timeout
# * The client can combine it with other concurrent operations without
#   blocking.
@contextlib.asynccontextmanager
async def preserve_new_file(dir: pathlib.Path):
    """
    A context manager that preserves files downloaded in a Playwright session.

    Playwright may asynchronously download a file. This context manager watches
    for this event and copies the file once it happens.

    :param dir pathlib.Path: The downloads directory used by Playwright.
    """
    async with get_new_files(dir) as get_new_files_task:

        async def copy_new_files():
            new_files = await get_new_files_task
            for nf in new_files:
                # We need to copy the file, because playwright deletes
                # downloaded files on browser close.
                shutil.copy(nf, str(nf) + ".csv")

        copy_new_files_task = asyncio.create_task(copy_new_files())
        yield copy_new_files_task
        await copy_new_files_task


# Using an async context manager, because it's more natural:
# * The client can now define the timeout using an orthogonal asyncio.timeout
# * The client can combine it with other concurrent operations without
#   blocking.
@contextlib.asynccontextmanager
async def get_new_files(dir: pathlib.Path):
    """
    A context manager that returns files downloaded in a Playwright session.

    Playwright may asynchronously download a file. This context
    manager watches for new files and returns their paths.

    Example:

    async with get_new_files(dir) as get_new_files_task:
        await trigger_download()
        new_files = await get_new_files_task
        copy(new_files, dest)

    :param dir pathlib.Path: The downloads directory used by Playwright.
    """
    old_entries = set(os.listdir(dir))

    async def wait_for_new_files():
        while True:
            new_entries = set(os.listdir(dir))
            if len(new_entries) > len(old_entries):
                new_files = new_entries.difference(old_entries)
                return [pathlib.Path(dir / nf) for nf in new_files]
            else:
                await asyncio.sleep(1)
                continue

    wait_for_new_files_task = asyncio.create_task(wait_for_new_files())
    yield wait_for_new_files_task
    await wait_for_new_files_task


class Download:

    def __init__(self, download_info):
        self.download_info = download_info

    async def wait_for_download(self):
        download = await self.download_info.value
        download_path = await download.path()
        if not download_path:
            raise Exception("The download interception has failed.")
        with open(download_path, "rb") as f:
            self.value = f.read()

    def downloaded_content(self) -> bytes:
        """Returns the bytes of the downloaded file."""
        return self.value


@contextlib.asynccontextmanager
async def intercept_download(
        page: playwright.async_api.Page) -> typing.AsyncIterator[Download]:
    """An async context manager that waits for a download to finish.

    Returns the object representing the downloaded content."""
    async with page.expect_download() as download_info:
        download = Download(download_info)
        yield download
    await download.wait_for_download()


@contextlib.asynccontextmanager
async def new_page(
    browser_type: Browser,
    headless: bool = False,
    downloads_path: Optional[pathlib.Path] = None
) -> typing.AsyncIterator[playwright.async_api.Page]:
    """Opens a new page in a new context.

    :param browser playwright.async_api.BrowserType: The browser to use.
    :param headless bool: Whether to run a fixed-viewport headless browser or a
    :param downloads_path Optional[pathlib.Path]: The path used for downloads.
    responsive one. Defaults to False.
    """
    async with (async_playwright() as pw,
                async_closing(
                    get_browser_type(pw, browser_type).launch(
                        headless=headless, downloads_path=downloads_path)) as
                browser,
                async_closing(browser.new_context(no_viewport=not headless)) as
                context, async_closing(context.new_page()) as page):
        yield page
