from rest_framework.response import Response
from rest_framework import views
from django.conf.urls import url
import numpy as np
import types

param_desc = """
        ---
        parameters:
            - name: value
              description: argument
              type: string
              paramType: query

        """


def my_get(self, request):
    return Response(str(self.calc(float(request.QUERY_PARAMS['value']))))


def generate_wrapper(source):
    path = r'^{0}/$'.format(source.__name__)
    wrapper = type(source.__name__, (views.APIView,), {})
    wrapper.get = types.FunctionType(my_get.__code__, globals=my_get.__globals__, closure=my_get.__closure__)
    wrapper.get.__doc__ = source.__doc__ + param_desc
    wrapper.calc = source
    return url(path, wrapper.as_view())


def get_urls():
    functions = [np.math.__dict__.get(name) for name in dir(np.math)]
    return [generate_wrapper(f) for f in functions[6:11]]
