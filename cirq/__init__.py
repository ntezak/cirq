# coding=utf-8
"""
Cirq is a package for creating and editing circuits of arbitrary domain.
The very simple data structure allows for interfacing with further modeling and simulation backends.

Circuits, i.e., abstract networks of interconnected components with ports,
have found application in various scientific and engineering domains,
ranging from applications close to the physical implementation,
such as electrical circuits, photonic circuits for optical information processing,
superconducting circuits for quantum information applications
to more abstract circuit representations of dynamical systems,
modeling biological processes or even software algorithms.

Their great applicability has already led to the development of many domain-specific modeling and simulation
toolkits as well as some very general domain-independent toolkits such as [Modelica](https://www.modelica.org/),
but to date, there exist very few open source graphical general circuit editing environments that can be tightly
integrated with custom, domain-specific implementation simulation or
analysis backends as well as [IPython](http://ipython.org).

An in-browser visual circuit editor leads to a rich integrated simulation and analysis workflow
in which an engineer or researcher can receive very fast feedback when making changes to his model.
As a consequence, it is much easier to build intuition for the particular kinds of circuit models
and find novel and creative solutions to an engineering task.
"""

#-----------------------------------------------------------------------------
#  Copyright (c) 2014, Nikolas Tezak <Nikolas.Tezak@gmail.com>
#
#  Distributed under the terms of the Modified BSD License.
#
#  The full license is in the file LICENSE.txt, distributed with this software.
#-----------------------------------------------------------------------------
__author__ = 'Nikolas Tezak'

from cirq.core import (init_js, clone_ports,
                  inputs, outputs, inouts,
                  Domain, Port,
                  ComponentType, ComponentInstance,
                  Connection,
                  Circuit, CircuitBuilder)