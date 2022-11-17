# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'ebilab'
copyright = '2022, Yusuke Ebihara'
author = 'Yusuke Ebihara'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ['_templates']
exclude_patterns = []

language = 'ja'
locale_dirs = ['locale/']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
# html_theme = 'alabaster'
html_static_path = ['_static']

import os
import sys
sys.path.insert(0, os.path.abspath('../..'))

extensions = [
    'sphinx.ext.autodoc',  # ソースコード読み込み用
    'sphinx.ext.viewcode',  # ハイライト済みのソースコードへのリンクを追加
    'sphinx.ext.todo',  # ToDoアイテムのサポート
    'sphinx.ext.napoleon', #googleスタイルやNumpyスタイルでdocstringを記述した際に必要
    'sphinx.ext.autosummary',
]

autosummary_generate = False
