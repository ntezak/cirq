# coding=utf-8
__author__ = 'nikolas'

# -----------------------------------------------------------------------------
# Copyright (c) 2014, Nikolas Tezak <Nikolas.Tezak@gmail.com>
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE.txt, distributed with this software.
# -----------------------------------------------------------------------------
"""
These tests can only be run from within an IPython notebook
"""

from cirq import *


def test_mach_zehnder():
    """
    Test some simple things, comprehensive tests would be nice, but complicated because of JavaScript.
    """
    fm = Domain(name="fieldmode", causal=True, one2one=True)
    el = Domain(name="electrical", causal=False, _color="purple")

    ins = [Port(name="In{}".format(k + 1), domain=fm, direction="in") for k in range(5)]
    outs = [Port(name="Out{}".format(k + 1), domain=fm, direction="out") for k in range(5)]
    el_port = Port(name="Control", domain=el, direction="inout")

    bs_type = ComponentType(name="Beamsplitter", ports=clone_ports(ins[:2] + outs[:2]))
    phase_type = ComponentType(name="Phase", ports=clone_ports(ins[:1] + [el_port] + outs[:1]))

    b1, b2 = map(bs_type.make_instance, ["b1", "b2"])
    phi = phase_type.make_instance("phi")

    mz = Circuit(name="MachZehnder",
                 ports=clone_ports(ins[:2] + [el_port] + outs[:2]),
                 component_instances=[b1, b2, phi])

    mz.connections = [
        Connection(source=s, target=t)

        for (s, t) in

        [(mz.p.In1, b1.p.In1),
         (mz.p.In2, b1.p.In2),
         (b1.p.Out1, phi.p.In1),
         (b1.p.Out2, b2.p.In1),
         (phi.p.Out1, b2.p.In2),
         (b2.p.Out1, mz.p.Out1),
         (b2.p.Out2, mz.p.Out2),
         (mz.p.Control, phi.p.Control)]
    ]

    mz_jsonifiable = mz.to_jsonifiable()
    mz2 = Circuit.from_jsonifiable(mz_jsonifiable)

    assert len(mz_jsonifiable) > 0
    assert mz2.name == mz.name
    assert mz2.p.keys() == mz.p.keys()
    assert mz2.c.keys() == mz.c.keys()
    assert mz_jsonifiable == mz2.to_jsonifiable()


