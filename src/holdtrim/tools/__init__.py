"""The checks CI runs, kept in the package so they ship with it.

A check that lives in a CI configuration file is a check nobody can run before
pushing, and one that lives in a shell script is a check nobody can test. These
are ordinary modules with ordinary tests, and CI runs them the same way anybody
else does.
"""
