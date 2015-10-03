import time
import os
import types
from rest_framework import views
from django.conf.urls import url
from django.conf import settings
from rest_framework.response import Response
import blockspring
import yaml
import base64


def transform_file(request, name):
    fup = request.FILES[name]
    data = base64.b64encode(fup.file.read()).decode('utf-8')
    request.has_files = True
    return {'filename': fup.name, 'data': data}


transforms = {
    'string': lambda request, name: request.DATA[name],
    'int': lambda request, name: int(request.DATA[name]),
    'float': lambda request, name: int(request.DATA[name]),
    'boolean': lambda request, name: request.DATA[name] == 'true',
    'date': lambda request, name: time.strftime('%Y-%m-%d', time.strptime(request.DATA[name], "%m/%d/%Y")),
    'file': transform_file
}


def blockspring_call(self, request):
    # query parameters contain values as arrays, blockspring does not like that
    params = {}
    if self.function_params:
        for param in self.function_params:
            key = param['name']
            try:
                params[key] = transforms[param['type']](request, key)
            except:
                params[key] = None
    if hasattr(request, 'has_files'):
        params['_blockspring_spec'] = True
    resp = blockspring.runParsed(self.function_name, params, {"api_key": settings.BLOCKSPRING_API_KEY})
    return Response(resp.params)


def generate_wrapper(group, function_name, function_desc_params):
    """ Constructs a API endpoint which will wrap a given function.
    Args:
        group (str): The name of the group to put the wrapper in.
        function (str): The function name to wrap.
    Returns:
        url (url): The composed URL object.
    """
    # url will match function name
    path = r'^blockspring-{0}/{1}$'.format(group, function_name)

    # make a copy of the APIView class to hold the code and doc
    wrapper = type(function_name, (views.APIView,), {})

    # make a copy of scipy_post function (needs to have own copy of the doc)
    wrapper.post = types.FunctionType(blockspring_call.__code__, globals=blockspring_call.__globals__,
                                      closure=blockspring_call.__closure__)

    wrapper.post.__doc__ = make_doc(function_desc_params)

    wrapper.function_name = function_name
    wrapper.function_params = function_desc_params['parameters']

    return url(path, wrapper.as_view())


def make_doc(function_desc_params):
    desc = function_desc_params['description'].replace('\n', '\n\n')
    del function_desc_params['description']
    if not function_desc_params['parameters']:
        return desc
    function_desc_params['type'] = {'result': {'type': 'string'}}
    yaml_s = yaml.dump(function_desc_params)
    doc = desc + '\n---\n' + yaml_s
    return doc


def get_urls():
    """ Gets all URLs for the library. """
    data = yaml.load(open(os.path.join(os.path.dirname(__file__), 'blockspring_api.yaml')).read())
    return [generate_wrapper(group, f_name, f_desc_params)
            for group, value in data.items()
            for f_name, f_desc_params in value.items()]
