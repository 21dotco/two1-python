import os
import math
import mimetypes

from django.http import HttpResponse
from rest_framework.decorators import api_view, authentication_classes

from two1.djangobitcoin.auth.djangobitcoin import PaymentRequiredAuthentication
from two1.djangobitcoin.djangobitcoin.settings import STATIC_SERVE_CONFIG
from .configurations import configurations
import yaml


def loadConfig(filePath):
    try:
        fileData = open(filePath).read()
    except:
        fileData = None
    return configurations(fileData)


# ########## Path Helpers ########## #

def componentsFromPath(path):
    if not isinstance(path, str):
        raise ValueError('Path must be a string.')

    # Get components from Path
    components = path.split('/')
    if not isinstance(components, list):
        raise ValueError('Must provide properly delimited components')

    # Normalize components
    if components[0] == '':
        del components[0]

    return components


def getInfoForPath(path):
    # Get Components
    components = componentsFromPath(str(path))

    # Get the path info
    return get_config().infoForPathItems(components)


def getTargetPath(rPath):
    # Get the base navigation path and navigation method for the path
    pathInfo = getInfoForPath(rPath)
    navMethod = None
    basePath = None
    for key in get_config()._infoNavigationKeys():
        if key not in pathInfo[0]:
            continue
        basePath = pathInfo[0][key]
        navMethod = key
        break

    if not isinstance(navMethod, str) or not isinstance(basePath, str):
        e = Exception('File not found. BP: ' + str(isinstance(basePath, str)) + ' nvm: '
                      + str(isinstance(navMethod, str)) + ' I: ' + str(pathInfo) + ' P: ' + rPath)
        e.status_code = 404
        raise e

    # Get the target path
    implicit_path = ''
    if len( pathInfo[1] ) != 0:
        implicit_path = '/' + '/'.join(pathInfo[1])
    compositePath = basePath + implicit_path
    if not isinstance(compositePath, str):
        raise Exception('Failed to build composite path.')

    compositePath = os.path.expanduser(compositePath)

    # if directory try index file
    if os.path.isdir(compositePath):
        sp = '/'.split(compositePath)
        sp.append('index.html')
        compositePath = '/'.join(list(sp))



    # Check if it exsists
    if not os.path.isfile(compositePath):
        print(compositePath)
        e = Exception('File not found.')
        e.status_code = 404
        raise e

    return {
        'path': compositePath,
        'navMethod': navMethod,
        'info': pathInfo
    };


st_srv_config = None


def get_config():
    global st_srv_config
    if not st_srv_config:
        st_srv_config = loadConfig(STATIC_SERVE_CONFIG)
    return st_srv_config


def sanitize_local_path(path, new):
    """
    - Each entry in the config is either a file or folder (defined fy presence of extension.
    - Attempt to use file with folder path or folder with file path should raise en error
    """
    if not os.path.exists(os.path.expanduser(new)):
        raise Exception('Path {0} does not exist'.format(new))
    is_folder_path = os.path.splitext(path)[1] == ''
    if is_folder_path and not os.path.isdir(os.path.expanduser(new)):
        raise Exception('{0} cannot be published as a folder'.format(new))
    if not is_folder_path and os.path.isdir(os.path.expanduser(new)):
        raise Exception('{0} cannot be published as a file'.format(new))
    return new


def add_static_serve_item(path, config):
    try:
        parsed = yaml.load(open(STATIC_SERVE_CONFIG).read())
    except:
        parsed = {'paths': {}}

    if path[0] != '/':
        path = '/' + path
    y_config = {}

    def copy_kv(k1, k2, transform=None):
        value = config.get(k1, None)
        if not value:
            raise Exception('Must provide "{0}" parameter'.format(k1))
        if transform:
            y_config[k2] = transform(value)
        else:
            y_config[k2] = value

    copy_kv('path', 'localPath')
    copy_kv('price', 'basePrice', lambda s: int(s))
    y_config['priceMode'] = 'pricePerByte' if 'pricePerByte' in config else 'pricePerFile'

    y_config['localPath'] = sanitize_local_path(path, y_config['localPath'])

    parsed["paths"][path] = y_config

    with open(STATIC_SERVE_CONFIG, 'w') as outfile:
        yaml.dump(parsed, outfile, default_flow_style=False)


# ########## Custom Payment Class ########## #

class StaticConfigPaymentAuth(PaymentRequiredAuthentication):
    # If the request is a GET request charge more
    def getQuoteFor(self, request):
        quote = 0
        target = getTargetPath(request.path)
        info = target['info']
        path = target['path']

        # Get file metadata
        byteSize = os.path.getsize(path)

        if info[0]['priceMode'] == 'pricePerFile':
            quote = info[0]['basePrice']
        elif info[0]['priceMode'] == 'payPerByte_full':
            quote = info[0]['basePrice'] * byteSize
        else:
            raise Exception('Error: Price mode \'' + info.priceMode + '\' not supported!')

        # convert to satoshi
        return math.floor(quote)


# ########## Static Serve ########## #

@api_view(['GET'])
@authentication_classes([StaticConfigPaymentAuth])
def index(request):
    """
    Serves static content
    """
    # Get the path info
    pathInfo = getTargetPath(request.path)
    compositePath = pathInfo['path']
    navMethod = pathInfo['navMethod']

    # Serve the data
    if navMethod == 'localPath' and request.method == 'GET':
        with open(compositePath, "rb") as f:
            response = HttpResponse(
                f.read(), content_type=mimetypes.guess_type(compositePath)[0])
            response.status_code = 200

    else:
        raise ValueError(
            'Navigation method \'' + navMethod + '\' not supported.')

    return response
