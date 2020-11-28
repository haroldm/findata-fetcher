# -*- coding: utf-8 -*-
"""Fetches account statement data from Interactive Brokers"""
import base64
import json
import logging
from typing import Dict, NamedTuple

from selenium import webdriver  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.common.keys import Keys  # type: ignore
from selenium.webdriver.support import expected_conditions  # type: ignore
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
import requests

from .driverutils import driver_cookie_jar_to_requests_cookies


class Credentials(NamedTuple):
    id: str
    pwd: str


def login(creds: Credentials,
          driver: webdriver.remote.webdriver.WebDriver) -> None:
    LOGIN_PAGE = 'https://www.interactivebrokers.co.uk/sso/Login?RL=1'
    driver.get(LOGIN_PAGE)
    driver.find_element(By.ID, "user_name").send_keys(creds.id + Keys.TAB)
    driver.find_element(By.ID, "password").send_keys(creds.pwd + Keys.RETURN)


def wait_for_logged_in_state(
        driver: webdriver.remote.webdriver.WebDriver) -> None:
    wait = WebDriverWait(driver, 120)
    wait.until(
        expected_conditions.element_to_be_clickable(
            (By.CSS_SELECTOR, '[aria-label="Reports"]')))


def go_to_reports_page(driver: webdriver.remote.webdriver.WebDriver) -> None:
    driver.find_element(By.CSS_SELECTOR, '[aria-label="Reports"]').click()
    # Wait for the page to load
    driver.find_element_by_xpath(
        "//*[normalize-space(text()) = 'MTM Summary']/../../..")


def fetch_account_statement_csv(
    am_session_id: str,
    cookies: Dict[str, str],
) -> bytes:
    FETCH_URL = ('https://www.interactivebrokers.co.uk' +
                 '/AccountManagement/Statements/Run')
    payload = {
        'format': 13,
        'fromDate': '20201126',
        'reportDate': '20201126',
        'toDate': '20201126',
        'language': 'en',
        'period': 'DATE_RANGE',
        'statementCategory': 'DEFAULT_STATEMENT',
        'statementType': 'MTM_SUMMARY'
    }
    headers = {
        'SessionId': am_session_id,
    }
    response = requests.get(
        FETCH_URL,
        params=payload,  # type: ignore
        cookies=cookies,
        headers=headers)
    if not response.ok:
        raise Exception("The statement fetch request has failed. " +
                        ('Response reason: {0}, parameters: {1}'
                         ).format(response.reason, (FETCH_URL, cookies)))
    return base64.decodestring(
        json.loads(response.content)['fileContent'].encode('ascii'))


def fetch_account_statement(
        driver: webdriver.remote.webdriver.WebDriver) -> bytes:
    logging.info("Going to the reports page.")
    go_to_reports_page(driver)
    logging.info("Reports page loaded, fetching cookies.")
    am_session_id = driver.execute_script('return AM_SESSION_ID;')
    cookies = driver_cookie_jar_to_requests_cookies(driver.get_cookies())
    logging.info("Fetching the CSV file.")
    return fetch_account_statement_csv(am_session_id, cookies)


def fetch_data(creds: Credentials) -> bytes:
    """Fetches Interactive Brokers's transaction data using Selenium

    Returns:
        A CSV with the fetched transactions.
    """
    with webdriver.Firefox() as driver:
        driver.implicitly_wait(60)
        login(creds, driver)
        wait_for_logged_in_state(driver)
        return fetch_account_statement(driver)
