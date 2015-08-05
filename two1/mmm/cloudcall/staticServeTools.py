#!/bin/python
import argparse
import os

# This is a static server configuration validation utility

from cloudcall.static_serve.configurations import configurations


class colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def printOk(str):
    print (colors.OKBLUE + str + colors.ENDC)


def printGood(str):
    print (colors.OKGREEN + str + colors.ENDC)


def printWarning(str):
    print (colors.WARNING + str + colors.ENDC)


def printError(str):
    print (colors.FAIL + str + colors.ENDC)


# Gets arguments from comand line
def getArgs():
    # Application Arguments
    parser = argparse.ArgumentParser(
        description='Static server configuration validation utility')

    # Modes
    parser.add_argument('-tree', action='store_true',
                        help='Renders a tree representation of the configuration')
    parser.add_argument(
        '-info', type=str,
        help='Queries the path tree using the inputted path')

    # Options
    parser.add_argument(
        '--config', default=os.path.dirname(os.path.abspath(__file__)) + '/ss_config.yaml',
        help='the configuration to verify')

    # Get our arguments
    return parser.parse_args()


# Get Arguments from comand line
args = getArgs()
filePath = args.config

# Load the File
if not isinstance(filePath, str):
    printError('Aborting: No configuration...')
    exit(-1)

fileData = open(filePath).read()
if not isinstance(fileData, str):
    printError("Aborting: Failed to load configuration at '" + filePath + "'")
    exit(-1)

data = configurations(fileData)

if args.tree:
    printGood("Rendering Tree:")
    data.renderTree()
    exit(0)

if args.info:
    path = args.info
    dat = data.infoForPathItems(path.split('/'))
    if path.split('/') == dat[1]:
        printError("Failed to resolve path! Look at 'python tool.py -tree' to check routes.")
        exit(-1)

    # Get the base navigation path
    for key in data._infoNavigationKeys():
        if key not in dat[0]:
            continue
        basePath = dat[0][key]
        break


    # Record Computed values
    fullPath = basePath + '/' + '/'.join(dat[1])
    price = dat[0]['basePrice']
    mode = dat[0]['priceMode']

    # Report
    print ("Request for: " + colors.OKBLUE + "'" + str(path) + "'" + colors.ENDC)
    print ("Would cost: " + colors.OKBLUE + str(price) + " satoshi(s)" + colors.ENDC)
    print ("In mode: " + colors.OKBLUE + str(mode) + colors.ENDC)
    print ("Would get: " + colors.OKBLUE + "'" + str(fullPath) + "'\n" + colors.ENDC)
    exit(0)
