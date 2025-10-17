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

project = "Notist"
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
    "sphinx_toolbox.more_autodoc.autotypeddict",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

add_module_names = False
always_use_bars_union = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# html_theme = "sphinx_rtd_theme"
html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]
html_css_files = ["css/custom.css"]
html_title = f"{project} Documentation"
html_last_updated_fmt = "%b %d, %Y"
html_context = {"default_mode": "light"}

html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/kaito47802/notist",
            "icon": "fa-brands fa-github",
        },
    ],
    "collapse_navigation": True,
    "navbar_end": ["version-switcher", "theme-switcher", "navbar-icon-links"],
    "secondary_sidebar_items": ["page-toc"],
    "switcher": {
        "json_url": "_static/versions.json",
        "version_match": os.getenv("DOC_VERSION_MATCH", "dev"),
    },
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
