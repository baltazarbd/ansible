#!/usr/bin/python3
import json
import requests
import xml.etree.ElementTree as ET
from re import match

#TODO xml_data
#TODO requests with continuationToken
xml_data = './PrematchService.Server.csproj'
include_regex = r"LiveCenter\.Robots\."
tag_mask = 'PackageReference'
include_attr = 'Include'
version_attr = 'Version'

versions_request_path = 'https://nexus.fbsvc.bz/service/rest/v1/search/assets?repository=dotnet_nuget&name=LiveCenter.Robots.*'


def get_last_versions():
    r = requests.get(versions_request_path, auth=('usrNexusJenkins','51dC5iDcGwHg'))
    last_versions = {}

    for i in r.json()['items']:
        if i['nuget']['is_latest_version'] is True:
            last_versions[i['nuget']['id']] = i['nuget']['version']    
    while True:
        r = requests.get(versions_request_path+"&continuationToken="+r.json()['continuationToken'], auth=('usrNexusJenkins','51dC5iDcGwHg'))
        for i in r.json()['items']:
                    if i['nuget']['is_latest_version'] is True:
                        last_versions[i['nuget']['id']] = i['nuget']['version']        
        if r.json()['continuationToken'] is None:
            break

    return last_versions


def replace_versions():
    last_versions = get_last_versions()
    tree = ET.parse(xml_data)
    root = tree.getroot()

    for reference in root.iter(tag_mask):
        reference_name = reference.attrib[include_attr]

        if match(include_regex, reference_name):
            reference.set(version_attr, last_versions[reference_name])

    tree.write(xml_data, encoding='UTF-8', xml_declaration=False)


if __name__ == "__main__":
    replace_versions()
