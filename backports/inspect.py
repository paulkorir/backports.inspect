from __future__ import absolute_import

from collections import namedtuple
# backports.inspect : backports of Python 3's inspect module
from copy import copy
# re-export :mod:`funcsigs` for :class:`Signature` objects
from funcsigs import *
# re-export the public API from ``inspect`` (which is noisy!)
from inspect import *

# borrowed from Python 3.3's inspect.py
FullArgSpec = namedtuple('FullArgSpec',
                         'args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations')


# borrowed and tweaked from Python 3.3's inspect.py
def getfullargspec(func):
    """Get the names and default values of a function's arguments.

    A tuple of seven things is returned:
    (args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults annotations).
    'args' is a list of the argument names.
    'varargs' and 'varkw' are the names of the * and ** arguments or None.
    'defaults' is an n-tuple of the default values of the last n arguments.
    'kwonlyargs' is an empty list
    'kwonlydefaults' is None
    'annotations' is a dictionary mapping argument names to annotations.

    The first four items in the tuple correspond to getargspec().

    Python 2.x doesn't have keyword-only arguments, and we don't have
    a backported alternative. We therefore fill ``kwonlyargs`` and
    ``kwonlydefaults`` as though the function were defined without any
    keyword-only arguments. (i.e., an empty list and ``None``,
    respectively).

    We synthesize a new ``__annotations__`` member if one isn't
    already present because callers expect it to exist, and be
    mutable, and have those side effects persist.
    """

    if ismethod(func):
        func = func.__func__
    if not isfunction(func):
        raise TypeError('{!r} is not a Python function'.format(func))
    args, varargs, kwonlyargs, varkw = _getfullargs(func.__code__)
    func.__annotations__ = getattr(func, '__annotations__', {})
    return FullArgSpec(args, varargs, varkw, func.__defaults__,
                       kwonlyargs, None, func.__annotations__)


# borrowed and tweaked from Python 3.3's inspect.py
def _getfullargs(co):
    """Get information about the arguments accepted by a code object.

    Four things are returned: (args, varargs, kwonlyargs, varkw), where
    'args' and 'kwonlyargs' are lists of argument names, and 'varargs'
    and 'varkw' are the names of the * and ** arguments or None.

    Python 2.x doesn't have keyword-only arguments, and we don't have
    a backported alternative. We therefore fill ``kwonlyargs`` and
    ``kwonlydefaults`` as though the function were defined without any
    keyword-only arguments. (i.e., an empty list and ``None``,
    respectively)."""

    if not iscode(co):
        raise TypeError('{!r} is not a code object'.format(co))

    nargs = co.co_argcount
    names = co.co_varnames
    # nkwargs = co.co_kwonlyargcount
    args = list(names[:nargs])
    # kwonlyargs = list(names[nargs:nargs+nkwargs])
    kwonlyargs = []
    step = 0

    # nargs += nkwargs
    varargs = None
    if co.co_flags & CO_VARARGS:
        varargs = co.co_varnames[nargs]
        nargs = nargs + 1
    varkw = None
    if co.co_flags & CO_VARKEYWORDS:
        varkw = co.co_varnames[nargs]
    return args, varargs, kwonlyargs, varkw


# borrowed from Python 3.8's inspect.py (Paul K. Korir, PhD)
# ------------------------------------------------ static version of getattr

_sentinel = object()


def _static_getmro(klass):
    return type.__dict__['__mro__'].__get__(klass)


def _check_instance(obj, attr):
    instance_dict = {}
    try:
        instance_dict = object.__getattribute__(obj, "__dict__")
    except AttributeError:
        pass
    return dict.get(instance_dict, attr, _sentinel)


def _check_class(klass, attr):
    for entry in _static_getmro(klass):
        if _shadowed_dict(type(entry)) is _sentinel:
            try:
                return entry.__dict__[attr]
            except KeyError:
                pass
    return _sentinel


def _is_type(obj):
    try:
        _static_getmro(obj)
    except TypeError:
        return False
    return True


def _shadowed_dict(klass):
    dict_attr = type.__dict__["__dict__"]
    for entry in _static_getmro(klass):
        try:
            class_dict = dict_attr.__get__(entry)["__dict__"]
        except KeyError:
            pass
        else:
            if not (type(class_dict) is types.GetSetDescriptorType and
                    class_dict.__name__ == "__dict__" and
                    class_dict.__objclass__ is entry):
                return class_dict
    return _sentinel


def getattr_static(obj, attr, default=_sentinel):
    """Retrieve attributes without triggering dynamic lookup via the
       descriptor protocol,  __getattr__ or __getattribute__.
       Note: this function may not be able to retrieve all attributes
       that getattr can fetch (like dynamically created attributes)
       and may find attributes that getattr can't (like descriptors
       that raise AttributeError). It can also return descriptor objects
       instead of instance members in some cases. See the
       documentation for details.
    """
    instance_result = _sentinel
    if not _is_type(obj):
        klass = type(obj)
        dict_attr = _shadowed_dict(klass)
        if (dict_attr is _sentinel or
                type(dict_attr) is types.MemberDescriptorType):
            instance_result = _check_instance(obj, attr)
    else:
        klass = obj

    klass_result = _check_class(klass, attr)

    if instance_result is not _sentinel and klass_result is not _sentinel:
        if (_check_class(type(klass_result), '__get__') is not _sentinel and
                _check_class(type(klass_result), '__set__') is not _sentinel):
            return klass_result

    if instance_result is not _sentinel:
        return instance_result
    if klass_result is not _sentinel:
        return klass_result

    if obj is klass:
        # for types we check the metaclass too
        for entry in _static_getmro(type(klass)):
            if _shadowed_dict(type(entry)) is _sentinel:
                try:
                    return entry.__dict__[attr]
                except KeyError:
                    pass
    if default is not _sentinel:
        return default
    raise AttributeError(attr)
