try:
    from two1.version import VERSION as version
except ImportError:
    try:
        from two1.lib.util.mkrelease import get_version_from_git
        version = get_version_from_git()
    except:
        raise Exception('Version not found. Is there a tag available?')

__version__ = version
