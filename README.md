# findata-fetcher

This project is a collection of scripts that automate fetching statements or
scraping financial data from financial institutions' websites, e.g.,
Interactive Brokers, BCGE.

You can use the fetched data to process it into a different database, e.g.,
[hledupt](https://github.com/gregorias/hledupt) uses this data to produce
plaintext accounting files.

Currently implemented fetchers are:

* BCGE's account statement
* (BCGE CC) Viseca's latest credit card bill
* Charles Schwab's account history
* Coop receipt PDF from gmail
* Degiro's portfolio and account statements
* Finpension's transaction report (through gmail)
* Interactive Brokers' MTM summary statement
* mBank's account statement
* Splitwise's balance statement

## Installation

1. [Install Selenium Webdriver
   (geckodriver)](https://www.selenium.dev/documentation/en/selenium_installation/installing_webdriver_binaries/)
2. You have two choices for installation. I recommend using pipx, which will
   install the app in a standalone environment:

    pipx install .

   alternatively, you may just go with pip:

    pip install --editable .

### Shell completion

Findata-fetcher provides shell completion through [Click][click]. To enable
shell completion, follow [its
instructions](https://click.palletsprojects.com/en/8.1.x/shell-completion/#enabling-completion).

## Usage example

    pipenv shell # If not already using pipenv
    python -m fetcher.tool --help

## Development notes

This section is meant for developers and provides instruction on how to work with the repository.

### Generic Setup

This project requires [Lefthook](https://github.com/evilmartians/lefthook) and
[Commitlint](https://github.com/conventional-changelog/commitlint).

Set up Pipenv:

    pipenv install --dev

Install lefthook:

    lefthook install

Also install [direnv](https://direnv.net/) to benefit from some dev tools.

### Ubuntu 22.04 Dev Environment Setup

The following commands provide a dev environment on a clean (WSL) Ubuntu 22.04 install. Official repos mostly contains packages that are too old.

#### Install system dependencies

```bash
# Install Node
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs

# Install tools
curl -fsSL https://github.com/tamasfe/taplo/releases/latest/download/taplo-full-linux-x86_64.gz | gzip -d - | install -m 755 /dev/stdin ~/.local/bin/taplo
sudo snap install lefthook --classic
sudo npm install -g @commitlint/cli @commitlint/config-conventional

# Install Python 3.11
sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt install -y python3.11-full
# Install pip
python3.11 -m ensurepip
# (if needed, add pip into PATH)
echo "export PATH=\$PATH:$HOME/.local/bin" >> ~/.bashrc
# Upgrade pip and install pipx
python3.11 -m pip install --upgrade pip pipx
# Install tools
pipx install poetry playwright pipenv
# Install playwright and its system dependencies
sudo playwright install
```

#### Install project dependencies in the virtual env

```bash
pipenv shell
poetry install
```

### Testing

To run tests, use `testall`.

To run tests and check for coverage, use `coverage`.

[click]: https://click.palletsprojects.com/en/8.1.x/
