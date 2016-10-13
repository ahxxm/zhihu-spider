#!/bin/sh
pip install pyflakes pep8
pip install -r requirements.txt
pep8 *py
pyflakes *py
