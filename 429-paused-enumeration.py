# Script to enumerate web servers with rate limiting (429 response)
# On lockout, this tool waits a specified amount of time to enumerate the next entries from a word list.
# Positive status codes are highlighted in different colours. 
# Author: dustin-www https://github.com/dustin-ww

import requests
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import Fore, Style, init

init(autoreset=True)

RATE_LIMIT_DELAY = 10 
MAX_THREADS = 10 
rate_limit_triggered = False

def check_url(target_url):
    global rate_limit_triggered

    try:
        if rate_limit_triggered:
            print(f"{Fore.YELLOW}Rate limit is active. Waiting {RATE_LIMIT_DELAY} seconds...{Style.RESET_ALL}")
            time.sleep(RATE_LIMIT_DELAY)
            rate_limit_triggered = False 

        response = requests.get(target_url)
        status_code = response.status_code

        if status_code == 404:
            print(f"{target_url} - {status_code}")
        else:
            print(f"{Fore.GREEN}{target_url} - {status_code}{Style.RESET_ALL}")

        # Delay on detected rate limiting
        if status_code == 429:
            rate_limit_triggered = True
            print(f"{Fore.YELLOW}Rate limit reached. Global pause activated.{Style.RESET_ALL}")

        return target_url, status_code

    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}Exception while trying to get url: {target_url}: {e}{Style.RESET_ALL}")
        return target_url, None

def enumerate_directories(url, wordlist_path):
    try:
        with open(wordlist_path, "r") as file:
            words = file.readlines()
    except FileNotFoundError:
        print(f"Fatal: file '{wordlist_path}' not found!")
        return

    target_urls = [f"{url}/{word.strip()}" if not url.endswith("/") else f"{url}{word.strip()}" for word in words]

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = [executor.submit(check_url, target_url) for target_url in target_urls]

        for future in as_completed(futures):
            target_url, status_code = future.result()

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python 429-paused-enumeration.py <URL> <WORDLIST> <DELAY_IN_SECONDS> <THREADS>")
        print("Example: python 429-paused-enumeration.py http://example.xyz wordlist.txt 10 10")
    else:
        url = sys.argv[1]
        wordlist_path = sys.argv[2]
        delay = sys.argv[3]
        threads = sys.argv[4]
        enumerate_directories(url, wordlist_path)
