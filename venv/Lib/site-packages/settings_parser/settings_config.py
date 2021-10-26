# -*- coding: utf-8 -*-
"""
Created on Fri Mar 10 16:48:45 2017

@author: villanueva
"""
from fractions import Fraction
import sys
from typing import List, Tuple, Dict
from settings_parser import Value, DictValue, Kind

class f_float(type):
    '''Type that converts numbers or str into floats through Fraction.'''
    def __new__(mcs, x: str) -> float:
        '''Return the float'''
        return float(Fraction(x))  # type: ignore
f_float.__name__ = 'float(Fraction())'
min_float = sys.float_info.min  # smallest float number
Vector = Tuple[f_float, f_float, f_float]

settings = {'version': Value(int, val_min=1, val_max=1),
            'section': DictValue({'subsection1': {'subsubsection1': str, 'subsubsection2': int},
                                  'subsection2': Value(List[int])}),
            'people': Value(Dict[str, DictValue({'age': int, 'city': str})]),  #  type: ignore
            'optional_section': Value(Dict[str, int], kind=Kind.optional),
            'position': Value(Vector, val_min=min_float)
           }
