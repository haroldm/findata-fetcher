"""Charles Schwab browser automation tools."""
import asyncio
import pathlib
from typing import Callable, NamedTuple, Awaitable

import playwright
import playwright.async_api

from fetcher.playwrightutils import intercept_download


class Credentials(NamedTuple):
    id: str
    pwd: str


def fetch_credentials() -> Credentials:
    """Fetches credentials from my 1Password vault."""
    from . import op
    username = op.read("Private", "Charles Schwab", "username")
    password = op.read("Private", "Charles Schwab", "password")
    return Credentials(id=username, pwd=password)


async def do_nothing(p: playwright.async_api.Page):
    return


async def select_eac_account_on_transaction_history_page(p):
    await p.get_by_role("combobox").filter(has_text='grzegorzmilka').click()
    await p.get_by_role("link", name="Equity Award Center").click()


async def trigger_transaction_history_export(
    page: playwright.async_api.Page,
    select_account: Callable[[playwright.async_api.Page], Awaitable[None]]
) -> None:
    await page.goto(
        'https://client.schwab.com/app/accounts/transactionhistory/#/')
    await select_account(page)
    async with page.expect_popup() as popup_info:
        await page.locator("#bttnExport button").click()
    popup = await popup_info.value

    try:
        await popup.locator(
            '#ctl00_WebPartManager1_wpExportDisclaimer_ExportDisclaimer_btnOk'
        ).click()
    except playwright._impl._api_types.Error as e:  # type: ignore
        if not e.message.startswith("Target closed"):
            raise e
        # Playwright for some reason throws "Target closed" error after the
        # click. It doesn't interfere with the download so, just ignore it.


async def login(page: playwright.async_api.Page, creds: Credentials) -> None:
    """Logs in to Charles Schwab.

    Returns once the authentication process finishes. The page will contain
    Charles Schwab's dashboard.

    :param page playwright.async_api.Page: A blank page.
    :param creds Credentials
    :rtype None
    """
    await page.goto(
        'https://client.schwab.com/Login/SignOn/CustomerCenterLogin.aspx')
    await page.frame_locator('#lmsSecondaryLogin').get_by_placeholder(
        'Login ID').focus()
    await page.keyboard.type(creds.id)
    await page.keyboard.press('Tab')
    await page.keyboard.type(creds.pwd)
    await page.keyboard.press('Enter')
    await page.locator('#placeholderCode').focus()
    await page.wait_for_url('https://client.schwab.com/clientapps/**')


async def download_brokerage_account_transaction_history(
        page: playwright.async_api.Page, creds: Credentials) -> bytes:
    """
    Downloads Charles Schwab brokerage account's transaction history.

    :param page playwright.async_api.Page: A blank page.
    :param creds Credentials
    :rtype bytes The downloaded statement.
    """
    await login(page, creds)
    async with intercept_download(page) as download:
        await trigger_transaction_history_export(page, do_nothing)
    return download.downloaded_content()


async def download_eac_transaction_history(page: playwright.async_api.Page,
                                           creds: Credentials) -> bytes:
    """
    Downloads Charles Schwab's EAC's transaction history.

    :param page playwright.async_api.Page: A blank page.
    :param creds Credentials
    :rtype bytes The downloaded statement.
    """
    await login(page, creds)
    async with intercept_download(page) as download:
        await trigger_transaction_history_export(
            page, select_eac_account_on_transaction_history_page)
    return download.downloaded_content()


class ForFurtherCreditInstructions(NamedTuple):
    # For example, 'U0123456'
    account_number: str
    # For example, Main St 1
    address: str
    name: str
    # For example, Zuerich ZH
    city_and_state: str
    # The two letter country code, e.g., 'CH'.
    country: str
    notes: str


class WireInstructions(NamedTuple):
    # The amount to wire, e.g., '21.37'.
    amount: str
    # The 9-digit ABA number.
    bank_routing_number: str
    # The beneficiary account number.
    beneficiary_account_number: str
    for_further_credit: ForFurtherCreditInstructions


async def send_wire_to_ib(page: playwright.async_api.Page, creds: Credentials,
                          wire_instructions: WireInstructions) -> None:
    """
    Sends a wire transfer to Interactive Brokers.

    :param page playwright.async_api.Page: A blank page.
    :param creds Credentials
    :rtype None
    """
    await login(page, creds)

    async def select_my_brokerage_account():
        await page.locator('#wireaccountselector').click()
        await page.locator('#wireaccountselector-header-0-account-0').click()

    async def select_domestic_wire_type():
        await page.locator('#wiretypeselector').click()
        await page.locator('#wiretypeselector-header-0-account-0').click()

    async def enable_for_further_credit_intructions():
        await page.locator('#yes-radio-id').click()

    await page.goto(
        'https://client.schwab.com/app/accounts/wire-transfers/#/wire/setup')

    await select_my_brokerage_account()
    await select_domestic_wire_type()

    await page.locator('#amount-input').type(wire_instructions.amount)
    await page.keyboard.press('Tab')
    # AKA ABA
    await page.locator('#routingnumber-input').type(
        wire_instructions.bank_routing_number)
    await page.keyboard.press('Tab')

    await page.locator('#recipientaccountnumber-input').type(
        wire_instructions.beneficiary_account_number)
    await page.keyboard.press('Tab')
    await page.keyboard.type(wire_instructions.beneficiary_account_number)
    await page.keyboard.press('Tab')
    await page.locator('#recipientaccountholdername-input').type(
        "Interactive Brokers LLC")
    await page.keyboard.press('Tab')
    await page.locator('#recipientaccountholderadress-input').type(
        "One Pickwick Plaza")
    await page.keyboard.press('Tab')
    await page.locator('#recipientcity-input').type(
        "Greenwich, Connecticut 06830")
    await page.keyboard.press('Tab')

    await enable_for_further_credit_intructions()
    await page.locator('#furthercreditaccountnumber-input').type(
        wire_instructions.for_further_credit.account_number)
    await page.keyboard.press('Tab')
    await page.keyboard.type(
        wire_instructions.for_further_credit.account_number)
    await page.keyboard.press('Tab')
    await page.locator('#furthercreditaccountholdername-input').type(
        wire_instructions.for_further_credit.name)
    await page.keyboard.press('Tab')
    await page.locator('#furthercreditaccountholderadress-input').type(
        wire_instructions.for_further_credit.address)
    await page.keyboard.press('Tab')
    await page.locator('#furthercreditcity-input').type(
        wire_instructions.for_further_credit.city_and_state)
    await page.keyboard.press('Tab')
    await page.locator('#furthercreditcountry-select-id').select_option(
        wire_instructions.for_further_credit.country)
    await page.keyboard.press('Tab')
    await page.locator('#transmissionnotes1-input').type(
        wire_instructions.for_further_credit.notes)
    await page.keyboard.press('Tab')
