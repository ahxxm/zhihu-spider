#!/bin/sh
pip install -U pyflakes pep8
pip install -r requirements.txt
pep8 *py --max-line-length=110 --exclude="settings.py"
pyflakes *py
