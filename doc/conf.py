# -*- coding: utf-8 -*-
# Copyright (C) 2009  Warp Networks, S.L.
# Author:  David Francos Cuartero <dfrancos@warp.es>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""
Wader documentation build configuration file, created by
sphinx-quickstart on Mon Apr 20 09:16:21 2009.
"""

from wader.common.consts import APP_VERSION, APP_NAME

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc',
                'sphinx.ext.autosummary',
                'sphinx.ext.coverage']

# Add any paths that contain templates here, relative to this directory.
templates_path = []

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'contents'

# General substitutions.
project = APP_NAME
copyright = 'The Wader project and contributors'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = APP_VERSION
release = version

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%d %B, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = False

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'trac'

# Sphinx will recurse into subversion configuration folders and try to read
# any document file within. These should be ignored.
# Note: exclude_dirnames is new in Sphinx 0.5
exclude_dirnames = ['.svn', '.git']

# Options for HTML output
# -----------------------

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
#html_style = 'wader.css'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
#html_static_path = ["_static"]

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
html_use_smartypants = True

# Content template for the index page.
#html_index = ''

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
html_additional_pages = {}

# If false, no module index is generated.
html_use_modindex = True

# If true, the reST sources are included in the HTML build as _sources/<name>.
html_copy_source = True

# Output file base name for HTML help builder.
htmlhelp_basename = 'Waderdoc'

html_show_sourcelink = True

# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author,
#   document class [howto/manual]).
#latex_documents = []
latex_documents = [
  ('contents', 'wader.tex', 'Wader Documentation', 'The Wader project',
    'manual'),
]

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
# If this isn't set to True, the LaTex writer can only handle six levels of
# headers.
latex_use_parts = True
