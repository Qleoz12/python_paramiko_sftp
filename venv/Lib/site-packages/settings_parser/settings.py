# -*- coding: utf-8 -*-
"""
Created on Fri Oct 14 13:33:57 2016

@author: Pedro
"""
# pylint: disable=E1101

#import sys
import logging
#from collections import OrderedDict
# nice debug printing of settings
import pprint
import copy
import warnings
from typing import Dict, Union, IO, Any, Callable

import ruamel.yaml as yaml

from settings_parser.util import log_exceptions_warnings, SettingsFileError, SettingsFileWarning
from settings_parser.util import SettingsValueError
from settings_parser.value import Value, DictValue


class Settings(dict):
    '''Contains the user settings and a method to validate settings files.'''

    def __init__(self, values_dict: Dict) -> None:  # pylint: disable=W0231
        super(Settings, self).__init__({})

        val_copy = copy.deepcopy(values_dict)
        self._dict_value = DictValue(val_copy)

        namedvalue_list = self._dict_value.values_list
        self._needed_values = set(namedvalue.key for namedvalue in namedvalue_list
                                 if namedvalue.kind is Value.mandatory)
        self._optional_values = set(namedvalue.key for namedvalue in namedvalue_list
                                   if namedvalue.kind is Value.optional)
        self._exclusive_values = set(namedvalue.key for namedvalue in namedvalue_list
                                    if namedvalue.kind is Value.exclusive)
        self._optional_values = self._optional_values | self._exclusive_values

        self._config_file = None  # type: str

    def __repr__(self) -> str:
        '''Representation of a settings instance.'''
        if self._config_file is None:  # not validated
            _dict_value = repr(self._dict_value).replace('DictValue(', '', 1)
            _dict_value = _dict_value[:-1]
            return '{}({})'.format(self.__class__.__name__, _dict_value)
        else:
            return pprint.pformat(self.settings)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Dict):
            return NotImplemented
        for key in self:
            if not key in other or self[key] != other[key]:
                return False
        return True

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, Dict):
            return NotImplemented
        return not self.__eq__(other)

#    def __getstate__(self):
#        '''For pickle'''
#        d = self.__dict__.copy()
#        d['val_type'] = repr(d['val_type'])
#        return d
#
#    def __setstate__(self, d):
#        '''For pickle'''
#        print(d)
#        d['val_type'] = eval(d['val_type'])
#        self.__dict__ = d

    @staticmethod
    def _get_property(key: str) -> Callable:
        '''Returns functions to get dictionary items. Used to create properties.'''
        def _get_prop(self: 'Settings') -> Any:
            '''Property to get values'''
            return self[key]
        return _get_prop

    @staticmethod
    def _set_property(key: str) -> Callable:
        '''Returns functions to set dictionary items. Used to create properties.'''
        def _set_prop(self: 'Settings', value: Any) -> None:
            '''Property to set values'''
            self[key] = value
        return _set_prop

    @staticmethod
    def _del_property(key: str) -> Callable:
        '''Returns functions to delete dictionary items. Used to create properties.'''
        def _del_prop(self: 'Settings') -> None:
            '''Property to delete values: delete from dictionary and the property.'''
            del self[key]
            delattr(self.__class__, key)
        return _del_prop

    def __setitem__(self, key: str, value: Any) -> None:
        '''All items added to the dictionary are accesible via dot notation'''
        dict.__setitem__(self, key, value)
        setattr(self.__class__, str(key), property(fget=self._get_property(key),
                                              fset=self._set_property(key),
                                              fdel=self._del_property(key),
                                              doc=str(key)))

    def __setattr__(self, key: str, value: Any) -> None:
        '''Set attributes as items in the dictionary, accesible with dot notation'''
        # this test allows attributes to be set in the __init__ method
        if not '_config_file' in self.__dict__:
            return dict.__setattr__(self, key, value)
        # known attributes set at __init__ are handled normally
        elif key in self.__dict__:
            dict.__setattr__(self, key, value)
        # own dictionary key (it's a property already)
        elif key in self:
            getattr(self.__class__, key).fset(self, value)
        # add unkown attributes to the dictionary
        else:
            self.__setitem__(key, value)

    @staticmethod
    def load_from_dict(d: Dict) -> 'Settings':
        '''Load the dictionary d as settings.'''
        settings = Settings({})
        for key, value in d.items():
            settings[key] = value
        settings._config_file = ''
        return settings

    @property
    def settings(self) -> Dict:
        '''Returns a dictionary with the settings'''
        return {key: value for key, value in self.items()}

    @log_exceptions_warnings
    def _validate_all_values(self, file_dict: Dict) -> Dict:
        '''Validates the settings in the config_dict
            using the settings list.'''
#        pprint.pprint(file_cte)
        present_values = set(file_dict.keys())

        # if present values don't include all needed values
        if not present_values.issuperset(self._needed_values):
            raise SettingsFileError('Sections that are needed but not present in the file: ' +
                                    str(self._needed_values - present_values) +
                                    '. Those sections must be present!')

        set_extra = present_values - self._needed_values
        # if there are extra values and they aren't optional
        if set_extra and not set_extra.issubset(self._optional_values):
            warnings.warn('WARNING! The following values are not recognized:: ' +
                          str(set_extra - self._optional_values) +
                          '. Those values or sections should not be present', SettingsFileWarning)

        parsed_dict = dict(self._dict_value.validate(file_dict))

#        pprint.pprint(parsed_dict)
        return parsed_dict

    @log_exceptions_warnings
    def validate(self, filename: str) -> None:
        ''' Load filename and extract the settings for the simulations
            If mandatory values are missing, errors are logged
            and exceptions are raised
            Warnings are logged if extra settings are found
        '''
        logger = logging.getLogger(__name__)
        logger.info('Reading settings file (%s)...', filename)

        # load file into config_cte dictionary.
        # the function checks that the file exists and that there are no errors
        file_cte = Loader().load_settings_file(filename)

        # store original configuration file
        with open(filename, 'rt') as file:
            self._config_file = file.read()

        # validate all values in the configuration file
        settings_dict = self._validate_all_values(file_cte)

        # access settings directly as Setting.setting
        for key, value in settings_dict.items():
            self[key] = value

        # log read and validated settings
        # use pretty print
        logger.debug('Settings dump:')
        logger.debug('File dict (config_cte):')
        logger.debug(pprint.pformat(file_cte))
        logger.debug('Validated dict (cte):')
        logger.debug(repr(self))
        logger.info('Settings loaded!')


class Loader():
    '''Load a settings file'''

    def __init__(self) -> None:
        '''Init variables'''
        self.file_dict = {}  # type: Dict

    @log_exceptions_warnings
    def load_settings_file(self, filename: Union[str, bytes], file_format: str = 'yaml') -> Dict:
        '''Loads a settings file with the given format (only YAML supported at this time).
            If the file doesn't exist ir it's empty, raise SettingsFileError.'''
        if file_format.lower() == 'yaml':
            self.file_dict = self._load_yaml_file(filename)
        else:
            raise NotImplementedError

        if not self.file_dict:
            msg = 'The settings file is empty or otherwise invalid ({})!'.format(filename)
            raise SettingsFileError(msg)

        return self.file_dict

    @log_exceptions_warnings
    def _load_yaml_file(self, filename: str) -> Dict:
        '''Open a yaml filename and loads it into a dictionary
            SettingsFileError exceptions are raised if the file doesn't exist or is invalid.
        '''
        file_dict = {}  # type: Dict
        try:
            with open(filename) as file:
                file_dict = self._no_duplicate_load(file, yaml.SafeLoader)
        except OSError as err:
            raise SettingsFileError('Error reading file ({})! '.format(filename) +
                                    str(err.args)) from err
        except yaml.YAMLError as exc:
            msg = 'Error while parsing the config file: {}! '.format(filename)
            if hasattr(exc, 'problem_mark'):
                msg += str(exc.problem_mark).strip()
                if exc.context is not None:
                    msg += str(exc.problem).strip() + ' ' + str(exc.context).strip()
                else:
                    msg += str(exc.problem).strip()
                msg += 'Please correct data and retry.'
            else:  # pragma: no cover
                msg += 'Something went wrong while parsing the config file ({}):'.format(filename)
                msg += str(exc)
            raise SettingsFileError(msg) from exc

        return file_dict

    @staticmethod
    def _no_duplicate_load(stream: IO, Loader: yaml.BaseLoader = yaml.Loader) -> Dict:
        '''Load data and raise SettingsValueError if there's a duplicate key.'''

        class NoDuplicateLoader(Loader):  # type: ignore
            '''Load the yaml file use an OderedDict'''
            pass

        def no_duplicates_constructor(loader: yaml.BaseLoader, node: yaml.Node,
                                      deep: bool = False) -> Dict:
            """Check for duplicate keys."""
            mapping = {}  # type: Dict
            for key_node, value_node in node.value:
                key = loader.construct_object(key_node, deep=deep)
                if key in mapping:
                    msg = "Duplicate label {}!".format(key)
                    raise SettingsValueError(msg)
                value = loader.construct_object(value_node, deep=deep)
                mapping[key] = value

            # Load the yaml file use an OderedDict
            loader.flatten_mapping(node)
            return dict(loader.construct_pairs(node))

        NoDuplicateLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            no_duplicates_constructor)

        res = yaml.load(stream, NoDuplicateLoader)
        if not isinstance(res, Dict):
            return {}
        else:
            return dict(res)


#if __name__ == "__main__":
#    import settings_parser.settings_config as settings_config
#    settings = Settings(settings_config.settings)
#    settings.validate('config_file.cfg')
