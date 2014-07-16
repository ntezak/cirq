
Visually editing circuits with `cirq`

`Cirq` is a package for creating and editing circuits of arbitrary domain.
The very simple data structure allows for interfacing with further modeling and
simulation backends.

Circuits, i.e., abstract networks of interconnected components with ports,
have found application in various scientific and engineering domains,
ranging from applications close to the physical implementation,
such as electrical circuits, photonic circuits for optical information
processing,
superconducting circuits for quantum information applications
to more abstract circuit representations of dynamical systems,
modeling biological processes or even software algorithms.

Their great applicability has already led to the development of many domain-
specific modeling and simulation
toolkits as well as some very general domain-independent toolkits such as
[Modelica](https://www.modelica.org/),
but to date, there exist very few open source graphical general circuit editing
environments that can be tightly
integrated with custom, domain-specific implementation simulation or
analysis backends as well as [IPython](http://ipython.org).


An in-browser visual circuit editor leads to a rich integrated simulation and
analysis workflow
in which an engineer or researcher can receive very fast feedback when making
changes to his model.
As a consequence, it is much easier to build intuition for the particular kinds
of circuit models
and find novel and creative solutions to an engineering task.


## Example notebooks

Check out (download to see actual circuits)

- [Demo.ipynb](http://nbviewer.ipython.org/github/ntezak/cirq/blob/master/Demo.ipynb) to see how to use cirq
- [Ahkab.ipynb](http://nbviewer.ipython.org/github/ntezak/cirq/blob/master/Ahkab.ipynb) to see how to interface cirq with [Ahkab](https://github.com/ahkab/ahkab)
- [QNET.ipynb](http://nbviewer.ipython.org/github/ntezak/cirq/blob/master/QNET.ipynb) to see how to interface cirq with [QNET](http://mabuchilab.github.io/QNET)


This file is actually based on the first one of these.


    import cirq; reload(cirq);
    from cirq import *
    init_js()


    <IPython.core.display.Javascript at 0x108f0af90>



    import cirq.tests; reload(cirq.tests);
    cirq.tests.test_mach_zehnder()

## Specifying the domain

Let's assume an example from my field, the connections are given by directed
propagating light fields.
Directed connections are called `causal`. Moreover, each input can only be
connected to a single output
due to reasons of unitarity of the underlying physics. All energy/information
must be accounted for.
This is indicated by the `one2one` keyword, which only applies to domains with
`causal=True`.

To provide an additional example, we also define an electrical domain, which is
undirected/acausal and we will draw its ports and connections in purple.


    fm = Domain(name="fieldmode", causal=True, one2one=True)
    el = Domain(name="electrical", causal=False, _color="purple")
    fm, el




    (Domain(name=fieldmode, causal=True, one2one=True),
     Domain(name=electrical, causal=False, one2one=False))



## Ports
We now specify some port instances that will be re-used by multiple component
types by cloning them, because each port can only belong to a single component.


    Inputs = [Port(name="In{}".format(k+1), domain=fm, direction="in") for k in range(5)]
    Outputs = [Port(name="Out{}".format(k+1), domain=fm, direction="out") for k in range(5)]
    el_port = Port(name="Control", domain=el, direction="inout")
    Inputs, Outputs, el_port




    ([In1, In2, In3, In4, In5], [Out1, Out2, Out3, Out4, Out5], Control)



## Component models

We now define two different component models. A Beamsplitter,i.e., a semi-
transparent mirror which interferometrically mixes two input beams, and an
optical phase shifter, that can be controlled electronically.


    BS = ComponentType(name="Beamsplitter", ports=clone_ports(Inputs[:2]+Outputs[:2]))
    Phase = ComponentType(name="Phase", ports=clone_ports(Inputs[:1]+[el_port]+Outputs[:1]))

## Component instances and our circuit, a Mach-Zehnder interferometer


    b1, b2 = map(BS.make_instance, ["b1", "b2"])
    phi = Phase.make_instance("phi")
    
    mz = Circuit(name="MachZehnder",
                   ports=clone_ports(Inputs[:2]+[el_port]+Outputs[:2]),
                   component_instances=[b1,b2,phi])
    
    mz.connections = [Connection(source=s, target=t) 
                            for (s,t) in [
                                (mz.p.In1, b1.p.In1), 
                                (mz.p.In2, b1.p.In2), 
                                (b1.p.Out1, phi.p.In1),
                                (b1.p.Out2, b2.p.In1),
                                (phi.p.Out1, b2.p.In2),
                                (b2.p.Out1, mz.p.Out1),
                                (b2.p.Out2, mz.p.Out2),
                                (mz.p.Control, phi.p.Control)]]
    mz

## It's possible to tweak individual visualization parameters of a circuit element dynamically


    from IPython.html.widgets import interact
    @interact(r=(20,200))
    def resize_b1(r=ComponentInstance._r.default_value):
        b1._r = r
        b1.layout_ports(b1.ports)

## Change the circuit via an extended UI


    cb = CircuitBuilder([fm, el], [BS, Phase], mz)
    cb

## Export a figure of your circuit


    from IPython.display import Image, FileLink, SVG


    cb.circuit.capture_svg()


    cb.circuit.save_last_image("mach_zehnder.svg")
    cb.circuit.save_last_image("mach_zehnder.png")
    cb.circuit.save_last_image("mach_zehnder.pdf")


<a href='mach_zehnder.svg' target='_blank'>mach_zehnder.svg</a><br>



<a href='mach_zehnder.png' target='_blank'>mach_zehnder.png</a><br>



<a href='mach_zehnder.pdf' target='_blank'>mach_zehnder.pdf</a><br>



    # this needs to run in another cell, because the above method writes the SVG file asynchronously
    display(SVG(filename="mach_zehnder.svg"),
    Image(filename="mach_zehnder.png"),
    FileLink("mach_zehnder.pdf"))


![svg](Demo_files/Demo_21_0.svg)



![png](Demo_files/Demo_21_1.png)



<a href='mach_zehnder.pdf' target='_blank'>mach_zehnder.pdf</a><br>


## Serialize a circuit to JSON


    mz.to_jsonifiable()




    {'component_instances': {u'b1': u'Beamsplitter',
      u'b2': u'Beamsplitter',
      u'phi': u'Phase'},
     'component_types': {u'Beamsplitter': {'ports': [{'direction': 'in',
         'domain': u'fieldmode',
         'name': u'In1'},
        {'direction': 'in', 'domain': u'fieldmode', 'name': u'In2'},
        {'direction': 'out', 'domain': u'fieldmode', 'name': u'Out1'},
        {'direction': 'out', 'domain': u'fieldmode', 'name': u'Out2'}]},
      u'Phase': {'ports': [{'direction': 'in',
         'domain': u'fieldmode',
         'name': u'In1'},
        {'direction': 'inout', 'domain': u'electrical', 'name': u'Control'},
        {'direction': 'out', 'domain': u'fieldmode', 'name': u'Out1'}]}},
     'connections': [(u'MachZehnder', u'In1', u'b1', u'In1'),
      (u'MachZehnder', u'In2', u'b1', u'In2'),
      (u'b1', u'Out1', u'phi', u'In1'),
      (u'b1', u'Out2', u'b2', u'In1'),
      (u'phi', u'Out1', u'b2', u'In2'),
      (u'b2', u'Out1', u'MachZehnder', u'Out1'),
      (u'b2', u'Out2', u'MachZehnder', u'Out2'),
      (u'MachZehnder', u'Control', u'phi', u'Control')],
     'domains': {u'electrical': {'causal': False, 'one2one': False},
      u'fieldmode': {'causal': True, 'one2one': True}},
     'name': u'MachZehnder',
     'ports': [{'direction': 'in', 'domain': u'fieldmode', 'name': u'In1'},
      {'direction': 'in', 'domain': u'fieldmode', 'name': u'In2'},
      {'direction': 'inout', 'domain': u'electrical', 'name': u'Control'},
      {'direction': 'out', 'domain': u'fieldmode', 'name': u'Out1'},
      {'direction': 'out', 'domain': u'fieldmode', 'name': u'Out2'}]}



### And read it back in from JSON


    mz2 = Circuit.from_jsonifiable(mz.to_jsonifiable())


    mz2

## Find all nets/cliques of connected ports


    mz.get_nets(fm)




    [[MachZehnder.p.In1, b1.p.In1],
     [MachZehnder.p.In2, b1.p.In2],
     [MachZehnder.p.Out1, b2.p.Out1],
     [MachZehnder.p.Out2, b2.p.Out2],
     [b1.p.Out1, phi.p.In1],
     [b1.p.Out2, b2.p.In1],
     [b2.p.In2, phi.p.Out1]]




    mz.get_nets(el)




    [[MachZehnder.p.Control, phi.p.Control]]


