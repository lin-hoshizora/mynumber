"""Finder classes that extract key information from OCR results.

Instead of indpendent usage, finders are typically used inside an analyzer.
"""
from .simple import SimpleFinder
from .date import DatesFinder
from .wide import WideFinder
from .jgngak import JgnGakFinder
from .rouftnkbn import RouFtnKbnFinder
from .kigo_num import KigoNumFinder
