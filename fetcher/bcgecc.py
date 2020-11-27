# -*- coding: utf-8 -*-
# TODO This module is not finished. I haven't prioritized it, because the
# account's status is linked to BCGE and I'm already handling BCGE, i.e. the
# data is "eventually consistent" so to say.
"""Fetches account data from Viseca"""
from typing import NamedTuple
from selenium import webdriver  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.common.keys import Keys  # type: ignore
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
from selenium.webdriver.support import expected_conditions  # type: ignore


class Credentials(NamedTuple):
    id: str
    pwd: str


LOGIN_PAGE = 'https://one.viseca.ch/login/login'


def login(creds: Credentials,
          driver: webdriver.remote.webdriver.WebDriver) -> None:
    username_field_name = 'Benutzername'
    driver.get(LOGIN_PAGE)
    wait = WebDriverWait(driver, 30)
    wait.until(
        expected_conditions.presence_of_element_located(
            (By.ID, username_field_name)))
    driver.find_element(By.ID,
                        username_field_name).send_keys(creds.id + Keys.TAB)
    driver.find_element(By.ID, "password").send_keys(creds.pwd + Keys.RETURN)
    # TODO wait.until(expected_conditions.url_matches(MAIN_PAGE))


def fetch_all_transactions_since_2018(
        driver: webdriver.remote.webdriver.WebDriver) -> bytes:
    # TODO
    return b''


def fetch_data(creds: Credentials) -> bytes:
    """Fetches Viseca's transaction data using Selenium

    Returns:
        A CSV UTF-8 encoded string with the fetched transactions.
    """
    with webdriver.Firefox() as driver:
        login(creds, driver)
        csv = fetch_all_transactions_since_2018(driver)
        return csv