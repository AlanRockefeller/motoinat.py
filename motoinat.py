#!/usr/bin/python3

# Convert Mushroom Observer observation numbers to iNaturalist observation numbers

# Version 1.1 - Alan Rockefeller - May 15, 2025

# Usage: motoinat.py 12345
# Usage: motoinat.py -q --file input-numbers.txt

import sys
import requests
import argparse
import json
import logging

# Helper function to fetch data from iNaturalist API
def _fetch_inat_data(mo_url_to_check, api_params, debug_mode):
    base_url = "https://api.inaturalist.org/v1/observations" # Define base_url here or pass as arg if it can change
    
    logging.debug(f"\n--- DEBUG: Request Details ---")
    logging.debug(f"Base URL: {base_url}")
    logging.debug(f"Mushroom Observer URL: {mo_url_to_check}")
    logging.debug(f"Parameters: {json.dumps(api_params, indent=2)}")

    try:
        response = requests.get(base_url, params=api_params)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        
        logging.debug(f"\n--- DEBUG: Response Details ---")
        logging.debug(f"Status Code: {response.status_code}")
        logging.debug(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}")
        
        data = response.json()
        logging.debug(f"\n--- DEBUG: Response Data ---")
        logging.debug(json.dumps(data, indent=2))
        return data
    except requests.exceptions.RequestException as e:
        # Using logging.error for network/request errors if not handled by caller,
        # or print if it's a direct feedback for a specific URL attempt.
        # For this refactor, find_inaturalist_observation will print the user-facing error.
        logging.warning(f"Network error while contacting iNaturalist API for URL {mo_url_to_check}: {e}")
        return None
    except json.JSONDecodeError as e:
        logging.warning(f"Error decoding JSON response from iNaturalist API for URL {mo_url_to_check}: {e}")
        return None

# Helper function to format and print observation details
def _format_and_print_observation(mo_number, obs_item, matched_mo_url, url_only_flag, number_only_flag):
    inat_url = f"https://www.inaturalist.org/observations/{obs_item['id']}"
    if number_only_flag:
        print(obs_item['id'])
    elif url_only_flag:
        print(inat_url)
    else:
        species_guess = obs_item.get('species_guess', 'N/A')
        place_guess = obs_item.get('place_guess', 'N/A')
        print(f"Mushroom Observer #{mo_number}:") # Removed leading \n
        print(f"  iNaturalist Observation: {inat_url}")
        print(f"  Species: {species_guess}")
        print(f"  Location: {place_guess}")
        print(f"  Matched URL: {matched_mo_url}")
        print()

def find_inaturalist_observation(mo_number, debug_mode=False, url_only=False, number_only=False):
    # All possible URL formats that might be stored in iNaturalist
    mo_urls = [
        f"http://mushroomobserver.org/observer/show_observation/{mo_number}",
        f"https://mushroomobserver.org/observer/show_observation/{mo_number}",
        f"http://mushroomobserver.org/{mo_number}",
        f"https://mushroomobserver.org/{mo_number}",
        f"http://mushroomobserver.org/obs/{mo_number}",
        f"https://mushroomobserver.org/obs/{mo_number}"
    ]

    for mo_url in mo_urls:
        params = {
            "field:Mushroom Observer URL": mo_url,
            "verifiable": "any"
        }
        
        data = _fetch_inat_data(mo_url, params, debug_mode)

        if data and data['total_results'] > 0:
            _format_and_print_observation(mo_number, data['results'][0], mo_url, url_only, number_only)
            return  # Exit the function after finding and printing a match

    # If we get here, no match was found after trying all URL formats
    if url_only or number_only:
        print(f"Mushroom Observer #{mo_number} has no iNaturalist observation associated with it.")
    else:
        # Standardized "not found" message
        print(f"No iNaturalist observation found for Mushroom Observer #{mo_number}")
        print() # Keep the blank line for spacing as per original behavior

def main():
    parser = argparse.ArgumentParser(description="Find iNaturalist observations for Mushroom Observer numbers.")
    parser.add_argument("mo_numbers", nargs="*", help="One or more Mushroom Observer numbers")
    parser.add_argument("--file", type=str, help="File containing Mushroom Observer numbers")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--url", action="store_true", help="Output only the iNaturalist URL")
    parser.add_argument("-q", action="store_true", help="Output only the iNaturalist observation number")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    mo_numbers = args.mo_numbers

    if args.file:
        try:
            with open(args.file, "r") as file:
                for line in file:
                    stripped_line = line.strip()
                    if stripped_line: # Only add non-empty lines
                        mo_numbers.append(stripped_line)
        except FileNotFoundError:
            print(f"Error reading file {args.file}: FileNotFoundError - File not found.")
            sys.exit(1)
        except PermissionError:
            print(f"Error reading file {args.file}: PermissionError - Permission denied.")
            sys.exit(1)
        except IOError as e:
            print(f"Error reading file {args.file}: IOError - {e}")
            sys.exit(1)

    # Validate MO numbers and warn for non-digit entries.
    # mo_numbers currently holds numbers from command line arguments
    # and stripped, non-empty lines from the file (if provided).
    valid_mo_numbers = []
    if mo_numbers:
        for num_str in mo_numbers:
            # It's good practice to strip all inputs, including command line arguments,
            # in case they have accidental spaces.
            processed_num_str = num_str.strip()

            if not processed_num_str: # Skip empty strings (e.g. if an arg was just spaces)
                continue

            if processed_num_str.isdigit():
                valid_mo_numbers.append(processed_num_str)
            else:
                # Using print for user-facing warnings, not logging.warning here
                print(f"Warning: Invalid MO number '{processed_num_str}' provided. Skipping.", file=sys.stderr)
    
    mo_numbers = valid_mo_numbers # Update mo_numbers to only contain valid, processed numbers
    if not mo_numbers: # Check after validation
        print("Error: No valid Mushroom Observer numbers provided.")
        print("Usage: python script.py [mo_numbers] [--file FILE] [--debug] [--url] [-q]")
        sys.exit(1)

    for mo_number in mo_numbers:
        # Pass args.debug to control logging level within find_inaturalist_observation and its helpers
        find_inaturalist_observation(mo_number, args.debug, args.url, args.q)

if __name__ == "__main__":
    main()
