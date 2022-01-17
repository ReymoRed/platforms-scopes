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
logging.basicConfig(filename=f'{dir_path}/app.log', filemode='w', level=logging.INFO, datefmt='%H:%M:%S',
                    format='%(levelname)s - [%(asctime)s] - %(message)s')


def main():
    if is_directory_exists() and is_files_exists():
        update_programs_database()
        update_domains()
        logging.info('✅ Script completed successfully :)')


def update_programs_database():
    for program in get_programs():
        try:
            with open(f"{dir_path}/data/{program}_data.json") as file:
                old_file = json.loads(file.read())
                logging.info(f'Reading {program}...')
            new_file = json.loads(github_platform_scopes(program))
            changes = DeepDiff(old_file, new_file, ignore_order=True, report_repetition=True)
            if changes != "":
                for old, new in zip(old_file, new_file):
                    response = diff_in_programs(old, new, program)
                    if response is not None:
                        if response.get('type')=='targets' and (response.get('in_scopes') != ['No Changes...'] or response.get('out_of_scopes') != ['No Changes...']):
                            send_notification(response)
                        elif response.get('type')=='programs':
                            send_notification(response)
                        save_changes(new_file, program)
            else:
                logging.info(f'No Change in {program}_data.json .')
        except Exception as e:
            logging.info(f'The following Error occurred!\n {e}')


def update_domains():
    ##### 1. data/domains_data.txt changes
    # Get data from data/domains_data.txt And GitHub for Updates
    domains_file = read_file('domains')
    domains_github = github_domains_files('domains')
    # Notification send domains_data.txt changes
    domains_differences = domains_github - domains_file
    if len(domains_differences) > 0:
        send_notification({'type': 'domains', 'domains-changes': domains_differences})
        domains_changes('domains', domains_github)

    ##### 2. data/wildcards_data.txt changes
    # Get data from data/wildcards_data.txt And GitHub for Updates
    wildcards_file = read_file('wildcards')
    wildcards_github = github_domains_files('wildcards')
    # Notification send data/wildcards_data.txt changes
    wildcards_differences = wildcards_github - wildcards_file
    if len(wildcards_differences) > 0:
        send_notification({'type': 'domains', 'domains-changes': wildcards_differences})
        domains_changes('wildcards', wildcards_github)


def domains_changes(file_name, github):
    domains_text = '\n'.join(github)
    with open(f"{dir_path}/data/{file_name}_data.txt", "w") as file:
        file.write(domains_text)
        logging.info(f'{file_name}_data.txt Updated Successfully! .')


def read_file(file_name):
    with open(f"{dir_path}/data/{file_name}_data.txt") as file:
        return set(file.read().splitlines())


def diff_in_programs(old_value, new_value, platform):
    program_name = ""
    if old_value != new_value:
        for changed_item in zip(new_value.keys(), old_value.values(), new_value.values()):
            key = changed_item[0]
            old = changed_item[1]
            new = changed_item[2]
            if key == "name":
                program_name = new
                continue
            if new != old and key in white_list_fields() and key == "targets":
                changes = check_targets(old, new)
                return {
                    'type': key,
                    'platform': platform,
                    "program_name": program_name,
                    "in_scopes": changes['in_scope'] if len(changes['in_scope']) > 2 else ['No Changes...'],
                    "out_of_scopes": changes['out_of_scope'] if len(changes['out_of_scope']) > 2 else ['No Changes...'],
                }
            if new != old and key in white_list_fields():
                return {'type': 'programs',
                        "program_name": program_name,
                        "modified_attribute": key,
                        "changed_value": new}


def check_targets(old_items, new_items):
    changed_targets_in_scope_list = []
    changed_targets_out_of_scope_list = []

    old_in_scopes = old_items.get('in_scope')
    old_out_of_scopes = old_items.get('out_of_scope')

    new_in_scopes = new_items.get('in_scope')
    new_out_of_scopes = new_items.get('out_of_scope')

    #### changes in scopes
    for old_target, new_target in zip(old_in_scopes, new_in_scopes):
        # in hacker-one file Type of asset == asset_type
        if new_target.get('type') in white_list_types() or new_target.get('asset_type') in white_list_types():
            target_in_scope_changes = set(new_target.items()) - set(old_target.items())
            if len(target_in_scope_changes) > 0:
                changed_targets_in_scope_list.append(get_values(target_in_scope_changes))

    #### changes out of scopes
    for old_target, new_target in zip(old_out_of_scopes, new_out_of_scopes):
        # in hacker-one file Type of asset == asset_type
        if new_target.get('type') in white_list_types() or new_target.get('asset_type') in white_list_types():
            target_out_of_scope_changes = set(new_target.items()) - set(old_target.items())
            if len(target_out_of_scope_changes) > 0:
                changed_targets_out_of_scope_list.append(get_values(target_out_of_scope_changes))

    return {
        'in_scope': json.dumps(changed_targets_in_scope_list, indent=4),
        'out_of_scope': json.dumps(changed_targets_out_of_scope_list, indent=4),
    }


def get_programs_link():
    urls = {"bugcrowd": '',
            "federacy": '',
            "hackenproof": '',
            "intigriti": '',
            "yeswehack": '',
            "hackerone": ''}
    prefix_url = "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/master/data/{}_data.json"
    for program in get_programs():
        urls[program] = prefix_url.format(program)
    return urls


def get_values(changes):
    change = set(dict(changes).keys()) & set(white_list_types())
    changes = dict(tuple(changes))
    if len(changes) > 0:
        return changes[list(change)[0]]


def send_notification(*args):
    programs_message = "Program **{}** was changed **{}** attribute :\n```{}```"
    scopes_message = "Program **{}** updated **in-scopes** targets to :\n```{}``` and **out-of-scopes** to :\n```{}```"
    domains_message = "Changes of ** Domains/WildCards ** :\n ```{}```"
    for arg in args:
        if arg.get('type') == 'targets':
            requests.post(config.DISCORD_WEBHOOK, json={
                "content": scopes_message.format(arg['program_name'], arg['in_scopes'], arg['out_of_scopes'])
            })
        elif arg.get('type') == 'programs':
            requests.post(config.DISCORD_WEBHOOK, json={
                "content": programs_message.format(arg['program_name'], arg['modified_attribute'], arg['changed_value'])
            })
        elif arg.get('type') == 'domains':
            requests.post(config.DISCORD_WEBHOOK, json={
                "content": domains_message.format(arg['domains-changes'])
            })


def save_changes(new_file, program):
    with open(f"{dir_path}/data/{program}_data.json", 'w') as file_update:
        file_update.write(json.dumps(new_file))
        logging.info(f'file Database {program}_data.json updated.')


def github_domains_files(name):
    url = f"https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/master/data/{name}.txt"
    logging.info(f'Requesting to GitHub For Reading {name}...')
    return set(requests.get(url).text.split('\n'))


def github_platform_scopes(name):
    logging.info(f'Requesting to GitHub For Reading {name}...')
    return requests.get(get_programs_link()[name]).text


def white_list_fields():
    return ['submission_state', 'targets', 'eligible_for_bounty', 'eligible_for_submission']


def white_list_types():
    return ['Web', 'web-application', 'api', 'url', 'iprange', 'asset_identifier', 'URL', 'CIDR', 'Code', 'API', 'Protocol',
            'website', 'endpoint']


def get_programs():
    return ["bugcrowd", "federacy", "hackenproof", "intigriti", "yeswehack", "hackerone"]


def is_directory_exists():
    logging.info(f'[!] help Types: \n [+] True: File exists\n [+] False: File not exists\n\n')
    response = os.path.exists(dir_path + "/data")
    logging.info(f'Directory status is : {response} .')
    return response


def is_files_exists():
    status = True
    for program in get_programs():
        is_exist = os.path.exists(dir_path + f"/data/{program}_data.json")
        logging.info(f'status of {program} is : {is_exist} .')
        if not is_exist:
            status = False
    for file in ['domains', 'wildcards']:
        is_exist = os.path.exists(dir_path + f"/data/{file}_data.txt")
        logging.info(f'status of {file} is : {is_exist} .')
        if not is_exist:
            status = False
    return status


if __name__ == "__main__":
    main()
