#!/bin/sh
pip install -U pyflakes pep8
pip install -r requirements.txt
pep8 *py
pyflakes *py
