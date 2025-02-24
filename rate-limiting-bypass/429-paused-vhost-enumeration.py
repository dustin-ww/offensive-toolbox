# Script to enumerate vhosts on web servers with rate limiting (429 response)
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

def check_vhost(target_url, vhost, exclude_length=None):
    """
    Check if a given VHost exists on the target URL and exclude responses with a specific length.
    """
    global rate_limit_triggered

    try:
        if rate_limit_triggered:
            print(f"{Fore.YELLOW}Rate limit is active. Waiting {RATE_LIMIT_DELAY} seconds...{Style.RESET_ALL}")
            time.sleep(RATE_LIMIT_DELAY)
            rate_limit_triggered = False

        headers = {"Host": vhost}
        response = requests.get(target_url, headers=headers)
        status_code = response.status_code
        content_length = len(response.content) 

        if exclude_length is not None and content_length == exclude_length:
            return vhost, status_code, content_length, False  

        if status_code == 404:
            print(f"{vhost} - {status_code} - Length: {content_length}")
        elif status_code == 200:
            print(f"{Fore.GREEN}{vhost} - {status_code} - Length: {content_length}{Style.RESET_ALL}")
        elif status_code == 403:
            print(f"{Fore.RED}{vhost} - {status_code} - Length: {content_length}{Style.RESET_ALL}")
        elif status_code == 429:
            print(f"{Fore.YELLOW}{vhost} - {status_code} - Length: {content_length}{Style.RESET_ALL}")
            rate_limit_triggered = True
            print(f"{Fore.YELLOW}Rate limit reached. Global pause activated.{Style.RESET_ALL}")
            return vhost, status_code, content_length, True  
        else:
            print(f"{vhost} - {status_code} - Length: {content_length}")

        return vhost, status_code, content_length, False
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}Exception while trying to access {vhost}: {e}{Style.RESET_ALL}")
        return vhost, None, 0, False

def enumerate_vhosts(target_url, wordlist_path, delay, threads, output_file, exclude_length=None):

    try:
        with open(wordlist_path, "r") as file:
            vhosts = file.readlines()
    except FileNotFoundError:
        print(f"Fatal: File '{wordlist_path}' not found!")
        return

    vhosts = [vhost.strip() for vhost in vhosts]
    retry_vhosts = [] 

    with ThreadPoolExecutor(max_workers=int(threads)) as executor:
        while True:
            futures = [executor.submit(check_vhost, target_url, vhost, exclude_length) for vhost in vhosts]

            for future in as_completed(futures):
                vhost, status_code, content_length, needs_retry = future.result()
                if needs_retry:
                    retry_vhosts.append(vhost)  

              
                if status_code in [200, 300] and (exclude_length is None or content_length != exclude_length):
                    with open(output_file, "a") as outfile:
                        outfile.write(f"{vhost} - {status_code} - Length: {content_length}\n")

            if not retry_vhosts:
                break  

            print(f"{Fore.YELLOW}Retrying {len(retry_vhosts)} VHosts after delay...{Style.RESET_ALL}")
            time.sleep(int(delay))
            vhosts = retry_vhosts  
            retry_vhosts = [] 

if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: python3 429-paused-vhost-enumeration.py <TARGET_URL> <WORDLIST> <DELAY_IN_SECONDS> <THREADS> <OUTPUT_FILE> [EXCLUDE_LENGTH]")
        print("Example: python3 429-paused-vhost-enumeration.py http://example.xyz vhosts.txt 10 10 results.txt 1234")
    else:
        target_url = sys.argv[1]
        wordlist_path = sys.argv[2]
        delay = sys.argv[3]
        threads = sys.argv[4]
        output_file = sys.argv[5]
        exclude_length = int(sys.argv[6]) if len(sys.argv) > 6 else None  
        enumerate_vhosts(target_url, wordlist_path, delay, threads, output_file, exclude_length)