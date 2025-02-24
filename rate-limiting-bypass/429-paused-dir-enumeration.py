# Script to enumerate directories on web servers with rate limiting (429 response)
# On lockout, this tool waits a specified amount of time to enumerate the next entries from a word list.
# Positive status codes are highlighted in different colours. 

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
        elif status_code == 200:
            print(f"{Fore.GREEN}{target_url} - {status_code}{Style.RESET_ALL}")
        elif status_code == 403:
            print(f"{Fore.RED}{target_url} - {status_code}{Style.RESET_ALL}")
        elif status_code == 429:
            print(f"{Fore.YELLOW}{target_url} - {status_code}{Style.RESET_ALL}")
            rate_limit_triggered = True
            print(f"{Fore.YELLOW}Rate limit reached. Global pause activated.{Style.RESET_ALL}")
            return target_url, status_code, True  #
        else:
            print(f"{target_url} - {status_code}")

        return target_url, status_code, False

    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}Exception while trying to access {target_url}: {e}{Style.RESET_ALL}")
        return target_url, None, False

def enumerate_directories(url, wordlist_path, delay, threads, output_file):
    
    try:
        with open(wordlist_path, "r") as file:
            words = file.readlines()
    except FileNotFoundError:
        print(f"Fatal: File '{wordlist_path}' not found!")
        return

    target_urls = [f"{url}/{word.strip()}" if not url.endswith("/") else f"{url}{word.strip()}" for word in words]
    retry_urls = [] 
    with ThreadPoolExecutor(max_workers=int(threads)) as executor:
        while True:
            futures = [executor.submit(check_url, target_url) for target_url in target_urls]

            for future in as_completed(futures):
                target_url, status_code, needs_retry = future.result()
                if needs_retry:
                    retry_urls.append(target_url)  # A


                if status_code in [200, 300]:
                    with open(output_file, "a") as outfile:
                        outfile.write(f"{target_url} - {status_code}\n")

            if not retry_urls:
                break 

            print(f"{Fore.YELLOW}Retrying {len(retry_urls)} URLs after delay...{Style.RESET_ALL}")
            time.sleep(int(delay))  
            target_urls = retry_urls  
            retry_urls = [] 

if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Usage: python 429-paused-dir-enumeration.py <URL> <WORDLIST> <DELAY_IN_SECONDS> <THREADS> <OUTPUT_FILE>")
        print("Example: python 429-paused-dir-enumeration.py http://example.xyz wordlist.txt 10 10 results.txt")
    else:
        url = sys.argv[1]
        wordlist_path = sys.argv[2]
        delay = sys.argv[3]
        threads = sys.argv[4]
        output_file = sys.argv[5]
        enumerate_directories(url, wordlist_path, delay, threads, output_file)