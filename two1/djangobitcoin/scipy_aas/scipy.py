import json
import inspect

import types
import numpy as np
import scipy.fftpack as fft
import scipy.cluster.vq as cluster_vq
import scipy.cluster.hierarchy as cluster_hierarchy
import scipy.interpolate as interpolate
from rest_framework import views
from django.conf.urls import url
from rest_framework.response import Response


# Template for YAML header, used by django-rest-swagger to describe parameters
param_head_tpl = '''
    ---
    parameters:
    '''

# Swagger doc parameter template
param_tpl = '''
        - name: {0}
          required: {1}
          type: {2}
          paramType: form
'''


def param_desc(source):
    """ Generates the swagger documentation for the given function.
    Args:
        source (func): The function to build the swagger documentation for.
    Returns:
        spec (str): The swagger documentation for the given function.
    """
    # ArgSpec(args=['x', 'n', 'axis', 'overwrite_x'], varargs=None, keywords=None, defaults=(None, -1, False))
    a_specs = inspect.getargspec(source)

    n_defaults = 0
    if a_specs.defaults:
        n_defaults = len(a_specs.defaults)
    n_required = len(a_specs.args) - n_defaults

    def get_arg_desc(idx, arg):
        # data type cannot be extracted in runtime, so we use naming conventions
        param_data_type = scipy_name_type_map[arg]
        # in rare cases, same argument name can be of different types
        override = scipy_name_type_map_overrides.get(source.__name__ + '/' + arg)
        if override:
            param_data_type = override
        # if a parameter is in defaults, it is optional
        return param_tpl.format(arg, idx < n_required, param_data_type)

    return param_head_tpl + '\n    '.join(
        [get_arg_desc(idx, arg) for idx, arg in enumerate(a_specs.args) if arg[0] != '_' and arg != 'self'])


# Casting Utilties
def to_list_of_lists(source):
    # we need to accept both python array literals and JSON array literals.
    # JSON needs to have 0's after comma, so we try to make it happy
    sanitized = source.replace('.,', '.0,').replace('.]', '.0]')
    return json.loads(sanitized)


def to_array(source):
    return np.array(to_list_of_lists(source))


def to_array_tuple(source):
    # TODO parse tuple of arrays (how to express in json?)
    pass


def to_int_or_array(source):
    try:
        return int(source)
    except:
        return to_array(source)


def to_float_or_array(source):
    try:
        return float(source)
    except:
        return to_array(source)


def to_int_or_list(source):
    try:
        return int(source)
    except:
        return list([float(n) for n in source.strip('[]').split(',')])


def to_int_or_list_of_ints(source):
    try:
        return int(source)
    except:
        return list([int(n) for n in source.strip('[]').split(',')])


def to_int_tuple(source):
    try:
        return int(source)
    except:
        return tuple([int(n) for n in source.strip('()').split(',')])


def to_int_or_string(source):
    try:
        return int(source)
    except:
        return source


to_int = lambda s: int(s)
to_float = lambda s: float(s)
to_boolean = lambda s: s == 'true'
to_string = lambda s: s

# weird types go here, standardized populated below
scipy_name_type_map = {
    'k_or_guess': 'int or array',
    'k': 'int or array',
    'shape': 'tuple of ints',
    'axes': 'array[int]',
    'der': 'int or list',
    'orders': 'int or list of ints'
}

scipy_name_type_map_overrides = {
    'fftshift/axes': 'int or tuple of ints',
    'ifftshift/axes': 'int or tuple of ints',
    'fftfreq/d': 'scalar',
    'rfftfreq/d': 'scalar',
    'barycentric_interpolate/x': 'scalar or array',
    'pchip_interpolate/x': 'scalar or array',
    'piecewise_polynomial_interpolate/yi': 'list of lists',
    'interp1d/kind': 'string or integer',
    'interpn/points': 'tuple of array[float]'
}

array_param_names = ['data', 'x', 'xi', 'y', 'yi', 'z', 'obs', 'code_book', 'monocrit', 'points', 'values', 'Y', 'Z',
                     'R', 'X', 'T', 'Q', 'T1', 'T2']
for n in array_param_names:
    scipy_name_type_map[n] = 'array[float]'

boolean_param_names = ['overwrite_x', 'check_finite', 'warning', 'throw', 'copy', 'bounds_error', 'assume_sorted',
                       'rescale']
for n in boolean_param_names:
    scipy_name_type_map[n] = 'boolean'

int_param_names = ['i', 'n', 'd', 'iter', 'axis', 'depth', 'type', 'order']
for n in int_param_names:
    scipy_name_type_map[n] = 'int'

float_param_names = ['k', 'thresh', 't', 'period', 'h', 'a', 'b', 'fill_value']
for n in float_param_names:
    scipy_name_type_map[n] = 'float'

string_param_names = ['minit', 'missing', 'criterion', 'metric', 'method', 'name', 'norm', 'kind']
for n in string_param_names:
    scipy_name_type_map[n] = 'string'

transform_param = {
    'array[float]': to_array,
    'array[int]': to_array,
    'list of lists': to_list_of_lists,
    'tuple of array[float]': to_array_tuple,
    'int': to_int,
    'boolean': to_boolean,
    'float': to_float,
    'scalar': to_float,
    'int or array': to_int_or_array,
    'string': to_string,
    'tuple of ints': to_int_tuple,
    'int or tuple of ints': to_int_tuple,
    'string or integer': to_int_or_string,
    'scalar or array': to_float_or_array,
    'int or list': to_int_or_list,
    'int or list of ints': to_int_or_list_of_ints,
}


def from_array(obj):
    """ Casts a JSON array to support complex numbers.
    Args:
        obj (str): The json string to cast complex numbers in.
    Returns:
        list (list): The list with casted complex numbers.
    """
    # json does not support complex numbers, so in case return is complex, we transform it to map
    if np.iscomplexobj(obj):
        return json.loads(str(list(map(lambda n: {'real': n.real, 'imag': n.imag}, obj))).replace("'", '"'))
    else:
        return json.loads(str(obj.tolist()))


def from_tuple(obj):
    """ Performs a deep cast in the inputted tuple to a map.
    Args:
        obj (tuple): The tuple to cast.
    Returns:
        dict (dict): The dictionary representing the input.
    """
    return {idx: transform_result(el) for idx, el in enumerate(obj)}


def transform_result(obj):
    """ Performs a deep cast to the input which is best fit for scipy input.
    Args:
        obj (*): The input to cast.
    Returns:
        obj (*): The best fit casted inputs.
    """
    if type(obj) == np.ndarray:
        return from_array(obj)
    elif type(obj) == tuple:
        return from_tuple(obj)
    else:
        return obj


def scipy_post(self, request):
    # convention based parsing of the parameters
    kwargs = {key: transform_param[scipy_name_type_map[key]](value) for key, value in request.data.items()}
    res = self.calc(**kwargs)
    js_res = transform_result(res)
    return Response(js_res)


def generate_wrapper(source, group):
    """ Constructs a API endpoint which will wrap a given function.
    Args:
        source (func): The function to wrap.
        group (str): The name of the group to put the wrapper in.
    Returns:
        url (url): The composed URL object.
    """
    # url will match function name
    path = r'^scipy-{0}/{1}/$'.format(group, source.__name__)

    # make a copy of the APIView class to hold the code and doc
    wrapper = type(source.__name__, (views.APIView,), {})

    # make a copy of scipy_post function (needs to have own copy of the doc)
    wrapper.post = types.FunctionType(scipy_post.__code__, globals=scipy_post.__globals__,
                                      closure=scipy_post.__closure__)

    # create the doc. SciPy documentation has a number of '---------' elements, which break django-rest-swagger
    # which treats '---' as an YAML start, so we remove those groups. Also append yaml with parameters
    wrapper.post.__doc__ = source.__doc__.replace('---', '') + param_desc(source)

    # calc needs to be a static method, otherwise it turns into a bound method and cannot be called by scipy_post
    wrapper.calc = staticmethod(source)

    return url(path, wrapper.as_view())


# # # # # # # # # # # # Per Module URLs # # # # # # # # # # # #

def get_fft_urls():
    """ Get the fft wrappers for the white listed functions. """
    whitelist = [
        # fast fourier transforms
        'fft',
        'ifft',
        'fft2',
        'ifft2',
        'fftn',
        'ifftn',
        'rfft',
        'irfft',
        'dct',
        'idct',
        # differential and pseudo-differential operators
        'diff',
        'tilbert',
        'itilbert',
        'hilbert',
        'ihilbert',
        'cs_diff',
        'sc_diff',
        'ss_diff',
        'cc_diff',
        'shift',
        # helpers
        'fftshift',
        'ifftshift',
        'fftfreq',
        'rfftfreq',
        # fortran functions from scipy.fftpack.convolve and scipy.fftpack._fftpack are omitted, no metadata
    ]
    return [generate_wrapper(fft.__dict__.get(name), 'fft') for name in whitelist]


def get_vq_urls():
    """ Get the vq wrappers for the white listed functions. """
    whitelist = [
        'whiten',
        'vq',
        'kmeans',
        'kmeans2',
    ]
    return [generate_wrapper(cluster_vq.__dict__.get(name), 'cluster-vq') for name in whitelist]


def get_hierarchy_urls():
    """ Get the hierarchy wrappers for the white listed functions. """
    whitelist = [
        # cutters
        'fcluster',
        'fclusterdata',
        'leaders',

        # agglomerate clustering
        'linkage',
        'single',
        'complete',
        'average',
        'weighted',
        'centroid',
        'median',
        'ward',

        # statistics
        'cophenet',
        'from_mlab_linkage',
        'inconsistent',
        'maxinconsts',
        'maxdists',
        'maxRstat',
        'to_mlab_linkage',

        # validity and isomorphism checks
        'is_valid_im',
        'is_valid_linkage',
        'is_isomorphic',
        'is_monotonic',
        'correspond',
        'num_obs_linkage',
        # dendrogram, ClusterNode, leaves_list, to_tree, set_link_color_palette are omitted
    ]
    return [generate_wrapper(cluster_hierarchy.__dict__.get(name), 'cluster-hierarchy') for name in whitelist]


def get_interp_urls():
    """ Get the interpolate wrappers for the white listed functions. """
    whitelist = [
        # univariate interpolation, clases skipped
        'interp1d',
        'barycentric_interpolate',
        'krogh_interpolate',
        'piecewise_polynomial_interpolate',
        'pchip_interpolate',
        # multivariate interpolation, classes skipped
        'griddata',
        'interp2d',
        'interpn',
    ]
    return [generate_wrapper(interpolate.__dict__.get(name), 'interpolate') for name in whitelist]


def get_urls():
    """ Gets all URLs for the library. """
    return get_interp_urls()
    # return \
    #     get_fft_urls() \
    #     + get_vq_urls() \
    #     + get_hierarchy_urls()
