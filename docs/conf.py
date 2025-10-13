# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

import notist

sys.path.insert(0, os.path.abspath(".."))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "NotifyState"
copyright = "2025, Kaito Baba"
author = "Kaito Baba"
release = notist.__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_autodoc_typehints",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

add_module_names = False

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# html_theme = "sphinx_rtd_theme"
html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]
html_css_files = ["css/custom.css"]
html_title = f"{project} v{release} Document"
html_last_updated_fmt = "%b %d, %Y"
html_context = {"default_mode": "light"}

html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/kaito47802/NotifyState",
            "icon": "fa-brands fa-github",
        },
    ],
    "collapse_navigation": True,
    "navbar_end": ["version-switcher", "theme-switcher", "navbar-icon-links"],
    "secondary_sidebar_items": ["page-toc"],
}

html_sidebars = {
    "**": [
        "search-field.html",
        "sidebar-nav-bs.html",
    ]
}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

autodoc_default_options = {
    "members": True,
    "inherited-members": True,
    "special-members": "__init__",
}
