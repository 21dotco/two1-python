# @dongcarl
import json
import os
from abc import ABCMeta
from abc import abstractmethod
from contextlib import ContextDecorator

import yaml


class LoadableDumpableDataContext(ContextDecorator, metaclass=ABCMeta):
    """A context manager for data that can be dumped and loaded from disk
    """
    def __init__(self, file_path, loader_callable, dumper_callable):
        """Instantiate a loadable, dumpable data context with the specified file path, loader callable, and dumper callable.

        Args:
            file_path (str): The file path that the data is loaded and dumped from.
            loader_callable (callable): Takes in a file-like object and returns a deserialized Python object.
            dumper_callable (callable): Serializes its first argument (a Python object) to its second argument
                                        (a file-like object).

        Returns:
            LoadableDumpableDataContext: Instance of LoadableDumpableDataContext.

        """
        self.file_path = file_path
        self.loader = loader_callable
        self.dumper = dumper_callable

    def __enter__(self):
        """Deserializes the data stored at self.file_path and bind said data to the target in the as clause of the with
           statement, if self.file_path does not exist on disk, bind the result of self._filler() instead

        Returns (obj): deserialized from self.file_path or the return value of self._filler() if self.file_path does not
                       exist on disk

        """
        try:
            with open(self.file_path, 'r') as f:
                self.data = self.loader(f)
        except FileNotFoundError:
            self.fell_back = True
            self.data = self._filler()
        except:
            raise
        return self.data

    @abstractmethod
    def _filler(self):
        """ Returns initial data as fallback to self.file_path being non-existent on disk,
            subclasses should implement this method without any positional arguments
        """

    def __exit__(self, *exc):
        """Serializes the maybe-modified self.data to disk at self.file_path, making sure that all intermediate paths
           exist for self.file_path
        """
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, 'w') as f:
            self.dumper(self.data, f)


class JsonDataContext(LoadableDumpableDataContext):
    """A context manager for loading and dumping json files from disk
    """

    def _filler(self):
        return {}

    def __init__(self, json_file_path):
        """Instantiate a loadable, dumpable json data context with the specified file path.

        Args:
            json_file_path (str): The file path that the json data is loaded and dumped from.

        Returns:
            JsonDataContext: Instance of JsonDataContext.

        """
        super().__init__(json_file_path, json.load, json.dump)


class YamlDataContext(LoadableDumpableDataContext):
    """A context manager for loading and dumping yaml files from disk
    """

    def _filler(self):
        return {}

    def __init__(self, yaml_file_path):
        """Instantiate a loadable, dumpable yaml data context with the specified file path.

        Args:
            yaml_file_path (str): File path that the yaml data is loaded and dumped from.

        Returns:
            YamlDataContext: Instance of YamlDataContext.

        """
        def dumper(data, f):
            """A wrapper around yaml.dump which dumps to a file object à la json.dump
            """
            f.write(yaml.safe_dump(data, default_flow_style=False))
        super().__init__(yaml_file_path, yaml.safe_load, dumper)
