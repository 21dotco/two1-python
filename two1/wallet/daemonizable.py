import builtins
import inspect

_funcs = {}
_inst_methods = {}
_inst_properties = {}


def property(p):
    global _inst_properties
    if not isinstance(p, builtins.property):
        raise TypeError("p must be a property")

    cls_name = p.fget.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0]
    if cls_name not in _inst_properties:
        _inst_properties[cls_name] = []
    if p.fget.__name__ not in _inst_properties[cls_name]:
        _inst_properties[cls_name].append(p.fget.__name__)

    return p


def method(f):
    global _inst_methods
    n = f.__name__
    qn = f.__qualname__
    cls_name = qn.split('.<locals>', 1)[0].rsplit('.', 1)[0]
    if cls_name not in _inst_methods:
        _inst_methods[cls_name] = {}
    if n not in _inst_methods[cls_name]:
        _inst_methods[cls_name][n] = dict(qualname=qn,
                                          function=f,
                                          sig=inspect.signature(f),
                                          args=dict(),
                                          return_value=dict())

    return f


def arg(arg_name, serializer, deserializer):
    def decorator(f):
        global _inst_methods
        method(f)

        n = f.__name__
        qn = f.__qualname__
        cls_name = qn.split('.<locals>', 1)[0].rsplit('.', 1)[0]
        arg_dict = dict(serializer=serializer,
                        deserializer=deserializer)
        _inst_methods[cls_name][n]['args'][arg_name] = arg_dict
        return f

    return decorator


def return_value(serializer, deserializer):
    def decorator(f):
        global _inst_methods
        method(f)

        n = f.__name__
        qn = f.__qualname__
        cls_name = qn.split('.<locals>', 1)[0].rsplit('.', 1)[0]
        rv_dict = dict(serializer=serializer,
                       deserializer=deserializer)
        _inst_methods[cls_name][n]['return_value'] = rv_dict
        return f

    return decorator


def _get_method_dict(cls, method_name):
    class_name = cls.__name__
    if class_name not in _inst_methods:
        raise ValueError("%s is not registered as daemonizable." % class_name)
    if method_name not in _inst_methods[class_name]:
        return None

    return _inst_methods[class_name][method_name]


def serdes_args(serialize, cls, method_name, *args, **kwargs):
    new_args = []
    new_kwargs = {}

    t = 'serializer' if serialize else 'deserializer'
    ms = _get_method_dict(cls, method_name)
    if ms is None:
        return (new_args, new_kwargs)

    sig = ms['sig']
    param_names = list(sig.parameters)[1:]  # Remove 'self'

    ms_args = ms['args']

    for i, a in enumerate(args):
        pname = param_names[i]

        def serdes(x):
            return x
        if pname in ms_args:
            serdes = ms_args[pname].get(t, serdes)
        new_args.append(serdes(a))

    for pname, val in kwargs.items():
        def serdes(x):
            return x
        if pname in ms_args:
            serdes = ms_args[pname].get(t, serdes)
        new_kwargs[pname] = serdes(val)

    return (new_args, new_kwargs)


def serdes_return_value(serialize, cls, method_name, val):
    t = 'serializer' if serialize else 'deserializer'
    ms = _get_method_dict(cls, method_name)
    rv = val
    if ms is not None:
        serdes = ms['return_value'].get(t, lambda x: x)
        rv = serdes(val)

    return rv


def get_daemon_methods(cls):
    if cls.__name__ in _inst_methods:
        return _inst_methods[cls.__name__]
    else:
        return {}


def get_daemon_properties(cls):
    if cls.__name__ in _inst_properties:
        return _inst_properties[cls.__name__]
    else:
        return []
