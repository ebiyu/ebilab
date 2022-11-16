# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile po ja en watch

po: gettext
	sphinx-intl update -p build/gettext -l en

ja:
	make html

en:
	make html -e SPHINXOPTS='-D language="en"'

watch:
	sphinx-autobuild -b html $(SPHINXOPTS)  "$(SOURCEDIR)" $(BUILDDIR)/html

watch-en:
	sphinx-autobuild -b html $(SPHINXOPTS) -D language="en" "$(SOURCEDIR)" $(BUILDDIR)/html

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
