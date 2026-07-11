# -*- coding: utf-8 -*-
'''
    Streetsign Documentation config file.
    -------------------------------------
'''
# pylint: disable=redefined-builtin, invalid-name, unused-import
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '.venv', 'lib',
    'python' + '.'.join(str(x) for x in sys.version_info[:2]),
    'site-packages'))

extensions = [
    'sphinx.ext.autodoc',
]

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

# General information about the project.
project = 'StreetSign'
copyright = '2013-2026, Daniel Fairhead, et al.'

version = '1.1'
# The full version, including alpha/beta/rc tags.
release = '1.1.0'

exclude_patterns = ['_build']
pygments_style = 'sphinx'

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False

rst_epilog = """
.. _Python: http://python.org/
.. _Flask: http://flask.pocoo.org/
.. _Peewee: http://peewee.readthedocs.org/en/latest/
.. _peewee: http://peewee.readthedocs.org/en/latest/
.. _jQuery: http://jquery.com/
.. _Alpine.js: https://alpinejs.dev/
.. _Quill: https://quilljs.com/
.. _Choices.js: https://github.com/Choices-js/Choices
.. _Day.js: https://day.js.org/
.. _Prism.js: https://prismjs.com/
.. _Bootstrap: https://getbootstrap.com/
.. _Bootstrap 5: https://getbootstrap.com/
.. _Bootstrap Icons: https://icons.getbootstrap.com/
.. _jQuery 3: https://jquery.com/
.. _Flatpickr: https://flatpickr.js.org/
.. _pylint: http://www.pylint.org/
.. _sqlite: http://www.sqlite.org/
.. _FeedParser: http://pythonhosted.org/feedparser/
.. _Waitress: http://docs.pylonsproject.org/projects/waitress/en/latest/
.. _WhiteNoise: https://whitenoise.evans.io/
.. _Bleach: https://bleach.readthedocs.io/
.. _bcrypt: https://github.com/pyca/bcrypt/
.. _simpleeval: https://github.com/danthedeckie/simpleeval
"""

# ---------------------------------------------

html_theme = 'furo'

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#html_extra_path = []

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'StreetSigndoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  ('index', 'StreetSign.tex', 'StreetSign Documentation',
   'Daniel Fairhead', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'streetsign', 'StreetSign Documentation',
     ['Daniel Fairhead'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'StreetSign', 'StreetSign Documentation',
   'Daniel Fairhead', 'StreetSign', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False
