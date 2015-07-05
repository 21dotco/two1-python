import os
import math
import mimetypes

from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes
from cloudcall.static_serve.configurations import configurations

from lib.djangobitcoin import PaymentRequiredAuthentication
from django.conf import settings

def loadConfig(filePath):
    fileData = open(filePath).read()
    if not isinstance(fileData, str):
        print("\033[91m" + 'Aborting: Failed to load configuration at \'' +
              filePath + '\'' + "\033[0m")
        exit(-1)

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
    return config.infoForPathItems(components)

def getTargetPath(rPath):
    # Get the base navigation path and navigation method for the path
    pathInfo = getInfoForPath(rPath)
    navMethod = None
    basePath = None
    for key in config._infoNavigationKeys():
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
    compositePath = basePath + '/' + '/'.join(pathInfo[1])
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

# Load the configuration info
config = loadConfig(getattr(settings, 'STATIC_SERVE_CONFIG'))

# ########## Custom Payment Class ########## #

class StaticConfigPaymentAuth(PaymentRequiredAuthentication):
     # If the request is a GET request charge more
    def getQuoteFor(self, request):
        quote = 0
        target = getTargetPath(request.path) 
        info = target['info']
        path = target['path'];

        # Get file metadata
        byteSize = os.path.getsize(path)

        if info[0]['priceMode'] == 'pricePerFile':
            quote = info[0]['basePrice']
        elif info[0]['priceMode'] == 'payPerByte_full':
            quote =  info[0]['basePrice'] * byteSize
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
