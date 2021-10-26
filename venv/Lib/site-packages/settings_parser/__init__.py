# -*- coding: utf-8 -*-
"""
Created on Mon Oct 31 14:27:37 2016

@author: Pedro
"""
VERSION = '1.3.2'
DESCRIPTION = 'settings_parser: Load, parse and validate user settings'

from settings_parser.settings import Settings
from settings_parser.value import Value, DictValue, Kind
from settings_parser.util import SettingsValueError, SettingsTypeError
from settings_parser.util import SettingsFileError, SettingsFileWarning
from settings_parser.util import SettingsExtraValueWarning

__all__ = ["Settings", "Value", "DictValue", 'Kind',
           'SettingsValueError', 'SettingsExtraValueWarning']