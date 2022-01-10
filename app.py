#!/usr/bin/python3
# -*- coding: utf-8 -*-

from datetime import datetime
from deepdiff import DeepDiff
import requests
import logging
import config
import json
import os

dir_path = os.path.abspath(os.path.dirname(__file__))
logging.basicConfig(filename='app.log', filemode='w', level=logging.INFO,
                    format='%(levelname)s - %(message)s')
this_time = datetime.now().strftime("%H:%M:%S")


def main():
    if is_directory_exists() and is_files_exists:
        update_programs_database()
        update_domains()


def update_programs_database():
    for program in get_programs():
        try:
            with open(f"{dir_path}/data/{program}_data.json") as file:
                old_file = json.loads(file.read())
                new_file = json.loads(github_platform_scopes(program))
                changes = DeepDiff(old_file, new_file, ignore_order=True, report_repetition=True)
                if changes:
                    for old, new in zip(old_file, new_file):
                        response = diff_in_programs(old, new)
                        if response is not None:
                            send_notification(response)
                    save_changes(new_file, program)
                else:
                    logging.info(f'[{this_time}] No Change in {program}_data.json .')
        except Exception as e:
            logging.info(f'[{this_time}] The following Error occurred!\n {e}')


def update_domains():
    ##### 1. data/domains_data.txt changes
    # Get data from data/domains_data.txt And GitHub for Updates
    domains_file = read_file('domains')
    domains_github = github_domains_files('domains')
    # Notification send domains_data.txt changes
    domains_differences = domains_file - domains_github
    send_notification({'domains-changes': domains_differences})
    domains_changes('domains', domains_github)

    ##### 2. data/wildcards_data.txt changes
    # Get data from data/wildcards_data.txt And GitHub for Updates
    wildcards_file = read_file('wildcards')
    wildcards_github = github_domains_files('wildcards')
    # Notification send data/wildcards_data.txt changes
    wildcards_differences = wildcards_file - wildcards_github
    send_notification({'domains-changes': wildcards_differences})
    domains_changes('wildcards', wildcards_github)


def domains_changes(file_name, github):
    domains_text = '\n'.join(github)
    with open(f"{dir_path}/data/{file_name}_data.txt", "w") as file:
        file.write(domains_text)
        logging.info(f'[{this_time}] {file_name}_data.txt Updated Successfully! .')


def read_file(file_name):
    with open(f"{dir_path}/data/{file_name}_data.txt") as file:
        return set(file.read().splitlines())


def diff_in_programs(old_value, new_value):
    program_name = ""
    if old_value != new_value:
        for changed_item in zip(new_value.keys(), old_value.values(), new_value.values()):
            if changed_item[0] == "name":
                program_name = changed_item[2]
            if changed_item[2] != changed_item[1]:
                return {"program_name": program_name,
                        "modified_attribute": str(changed_item[0]),
                        "changed_value": str(changed_item[2])}


def get_programs_link():
    urls = {"bugcrowd": '',
            "hackerone": '',
            "federacy": '',
            "hackenproof": '',
            "intigriti": '',
            "yeswehack": ''}
    prefix_url = "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/master/data/{}_data.json"
    for program in get_programs():
        urls[program] = prefix_url.format(program)
    return urls


def send_notification(*args):
    programs_message = "Program ** {} ** was changed *** {} *** attribute :\n```{}```"
    domains_message = "Changes of ** Domains/WildCards ** :\n ```{}```"
    for arg in args:
        if arg.get('program_name'):
            requests.post(config.DISCORD_WEBHOOK, json={
                "content": programs_message.format(arg['program_name'], arg['modified_attribute'], arg['changed_value'])
            })
        elif arg.get('domains-changes'):
            requests.post(config.DISCORD_WEBHOOK, json={
                "content": domains_message.format(arg['domains-changes'])
            })
    logging.info(
        f'[{this_time}] All of this Platforms/Domains/WildCards changes notified... ')


def save_changes(new_file, program):
    with open(f"{dir_path}/data/{program}_data.json", 'w') as file_update:
        file_update.write(json.dumps(new_file))
        logging.info(f'[{this_time}] file Database {program}_data.json updated.')


def github_domains_files(name):
    url = f"https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/master/data/{name}.txt"
    return set(requests.get(url).text.split('\n'))


def github_platform_scopes(name):
    return requests.get(get_programs_link()[name]).text


def get_programs():
    return ["bugcrowd", "hackerone", "federacy", "hackenproof", "intigriti", "yeswehack"]


def is_directory_exists():
    logging.info(f'[!] help Types: \n [+] True: File exists\n [+] False: File not exists\n\n')
    response = os.path.exists(dir_path + "/data")
    logging.info(f'[{this_time}] Directory status is : {response} .')
    return response


def is_files_exists():
    status = True
    for program in get_programs():
        is_exist = os.path.exists(dir_path + f"/data/{program}_data.json")
        logging.info(f'[{this_time}] status of {program} is : {is_exist} .')
        if not is_exist:
            status = False
    for file in ['domains', 'wildcards']:
        is_exist = os.path.exists(dir_path + f"/data/{file}_data.txt")
        logging.info(f'[{this_time}] status of {file} is : {is_exist} .')
        if not is_exist:
            status = False
    return status


if __name__ == "__main__":
    main()
