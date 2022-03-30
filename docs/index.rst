.. PyVmt documentation master file, created by
   sphinx-quickstart on Mon Nov 29 11:10:45 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to PyVmt's documentation!
=================================

============
Introduction
============

PyVmt is a python library to work with Verification Modulo Theory problems.

It provides an interface to read and write `VMT-LIB`_ script, allowing the creation
of **transition models** through the addition of state variables, inputs,
init constraints, and trans constraints.

.. _VMT-LIB: https://vmt-lib.fbk.eu/

The library is based on `PySmt`_ to provide *parsing* and *printing* of `SMT-LIB`_ and
for *formula manipulation*, you can read the docs `here <https://pysmt.readthedocs.io/en/latest/>`_.

.. _`PySmt`: https://github.com/pysmt/pysmt
.. _SMT-LIB: http://smt-lib.org

The library allows the addition of *invariant* and *live properties* to the model
that can be serialized and used as part of the VMT-LIB script.

Invar properties are of the form "G (formula)".

Live properties are of the form "F G (formula)".

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api_ref

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
