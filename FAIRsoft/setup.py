#!/usr/bin/env python3

from distutils.core import setup

setup(name='FAIRsoft',
      version='0.1.4',
      description='Library for the aggregation of Life Sciences software metadata and FAIR evaluation.',
      description_content_type='text/markdown',
      log_description='''FAIRsoft indicators are a set of FAIRness indicators for research software, specifically devised to be assesed automatically. 
      This package allows the user to gather metadata about research software specific to Life Sciences, harmonize and integrate it and then perform an evaluation of their compliance with FAIRsoft indicators.''',
      author='Eva Martin del Pico',
      author_email='eva.martin@bsc.es',
      classifiers=['Development Status :: 4 - Beta'],
      install_requires = [
        'bidict',
        'munch',
        'pymongo',
        'requests',
        'simplejson',
        'webdriver_manager',
        'email-validator', 
        'bibtexparser'],
      url='https://gitlab.bsc.es/inb/elixir/software-observatory/FAIRsoft_ETL/-/tree/master/FAIRsoft',
      packages=['FAIRsoft',
                'FAIRsoft.integration',
                'FAIRsoft.transformation',
                'FAIRsoft.pre_integration',
                'FAIRsoft.classes',
                'FAIRsoft.indicators_evaluation'],
     )
