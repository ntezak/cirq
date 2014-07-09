__author__ = 'Nikolas Tezak'
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


from IPython.utils.traitlets import (Unicode, Bool, Instance, Any, Enum,
                                     HasTraits, Float, List, Tuple, Dict)
from types import FunctionType

from IPython.html.widgets import DOMWidget, ContainerWidget, ButtonWidget, PopupWidget, TextWidget, DropdownWidget
from math import sin, cos, pi
from IPython.display import display, Javascript, FileLink

import os

def init_js():
    """
    Run this to load the required javascript files
    """
    path = os.path.join(os.path.dirname(__file__), "static", "cirq.js")
    display(Javascript(filename=path))


class Domain(DOMWidget):
    """
    Describes a connection domain, such as electrical wires,
    propagating optical modes, signal flow in a control system, etc.

    Attributes
    ----------

    1. name: The domain name
    2. causal: Whether the connections are directed.
       Ports for a causal domain must either be inputs or outputs.
    3. one2one: For a causal domain, determines whether
       a given port can have more than one other port connected to it.
    """

    name = Unicode("wire", sync=True)
    causal = Bool(False, sync=True)
    one2one = Bool(False, sync=True)

    _color = Unicode("#3366AA", sync=True)
    _color_selected = Unicode("red", sync=True)
    _color_target = Unicode("green", sync=True)


    @classmethod
    def valid_connection(cls, p1, p2):
        """
        Verify if two ports can be connected validly.

        :param p1: First Port instance
        :param p2: Second Port instancs
        """
        if p1 is p2:
            return False

        if p1.domain is not p2.domain:
            return False

        if p1.domain.causal:

            p1t = p1.is_target
            p1s = p1.is_source
            p2t = p2.is_target
            p2s = p2.is_source

            if p1s and p2t:
                if p2 in p1.connections_out:
                    return False
                if p1.domain.one2one:
                    if len(p1.connections_out) + len(p1.connections_in) > 0:
                        return False
                return p1, p2
            if p2s and p1t:
                if p2 in p1.connections_in:
                    return False
                if p1.domain.one2one:
                    if len(p1.connections_in) + len(p2.connections_out) > 0:
                        return False

                return p2, p1
            return False
        else:
            if p1 in p2.connections_in or p1 in p2.connections_out:
                return False
            return p1, p2

    def __repr__(self):
        return "Domain(name={}, causal={}, one2one={})".format(self.name, self.causal, self.one2one)

    def _ipython_display_(self, **kwargs):
        return repr(self)


def clone_ports(ports):
    """Clone a list of ports. See Port.clone() doc."""
    return [p.clone() for p in ports]


class AttrDict(dict):
    """
    Dict that allows access of elements via dot-accessors.
    Used for convenience access to circuit ports and instances.
    """

    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise KeyError(name)


# noinspection PyTypeChecker
class HasPorts(HasTraits):
    """
    Visual element that has ports. Also stores base offset coordinates for the main object
    and initializes the port positions. Overwrite the `_layout_ports` for customization.
    """

    ports = List(sync=True)

    _x = Float(0., sync=True)
    _y = Float(0., sync=True)
    _r = Float(50., sync=True)

    p = Dict(AttrDict({}))
    _layout_ports = Instance(klass=FunctionType)

    def _ports_changed(self, name, old, new):
        for p in new:
            p._parent = self
        self.layout_ports(new)
        self.p = AttrDict({p.name: p for p in new})

    def layout_ports(self, ports):
        """
        Create layout for a list of ports by setting their individual coordinates
        and orientation angles. Override this method by setting the _layout_ports property.
        """

        if self._layout_ports:
            return self._layout_ports(self, ports)

        dphi = 2 * pi / len(ports)
        for kk, p in enumerate(ports):
            p._x = self._r * cos(kk * dphi + pi)
            p._y = self._r * sin(kk * dphi + pi)
            p._phi = kk * dphi + pi


class Port(DOMWidget):
    """
    Connection port element. Can be associated with a ComponentType, a ComponentInstance or a Circuit.

    Notes
    -----

    Any Port belongs to a given Domain object. If the domain is causal,
    then the port `direction` must either be `in` or `out`.

    A Port also keeps track of its `_parent` element, the overall `_circuit` it belongs to,
    as well as what connections lead into it and emanate from it.

    Finally, it has traits that determine how it is represented visually, including
    coordinates relative to its _parent, its orientation angle _phi, an overall _size,
    and where the label should be placed.
    """

    _view_name = Unicode("SVGPortView", sync=True)

    name = Unicode("n", sync=True)
    domain = Instance(klass=Domain, sync=True, doc="Associated domain, e.g., electrical contact, etc.")
    direction = Enum(("in", "out", "inout"), sync=True)

    params = List(sync=True)

    _circuit = Any(sync=True)
    _parent = Instance(klass=HasPorts, sync=True)
    connections_in = List()
    connections_out = List()

    _x = Float(0., sync=True)
    _y = Float(0., sync=True)
    _phi = Float(0., sync=True)
    _x_label = Float(8., sync=True)
    _y_label = Float(18., sync=True)
    _size = Float(12., sync=True)


    @property
    def is_ext(self):
        """True if the port is external, i.e. the port of a whole circuit."""
        return isinstance(self._parent, Circuit)

    @property
    def is_source(self):
        """True if the port is a valid source of a causal direction"""
        return self.direction == "out" or (self.direction == "in" and self.is_ext)

    @property
    def is_target(self):
        """True if the port is a valid target of a causal direction"""
        return self.direction == "in" or (self.direction == "out" and self.is_ext)

    def clone(self):
        """Create a port with the same name, domain and direction to be associated with a new parent element."""
        return Port(name=self.name, domain=self.domain, direction=self.direction)


    def __repr__(self):
        if self._parent:
            return "{}.p.{}".format(self._parent.name, self.name)
        return self.name




class ComponentType(HasPorts, DOMWidget):
    """
    Declares a component interface, including its port specification,
    and (in the future) its parameters.

    By setting `_inner_svg` to a non-zero string (and overriding the `_layout_ports` method)
    it is possible to customize the visualization of a given component.
    The ComponentInstance elements can still override the defaults stored in the ComponentType.

    """
    name = Unicode("ct", sync=True)

    _inner_svg = Unicode("")
    _x_label = Float(0.)
    _y_label = Float(0.)
    _inner_color = Unicode("#3366AA")
    _inner_color_selected = Unicode("red")
    _label_color = Unicode("white")
    params = List(sync=True)

    def make_instance(self, name, **options):
        """
        Create a ComponentInstance for the ComponentType with the default visualization options
        copied from the ComponentType. Override these via keyword arguments.

        :param name: name for the instance
        :param options: see trait declarations
                _layout_ports = Instance(klass=FunctionType)
                _inner_svg = Unicode("")
                _x_label = Float(0.)
                _y_label = Float(0.)
                _inner_color = Unicode("#3366AA")
                _inner_color_selected = Unicode("red")
                _label_color = Unicode("white")
        """
        default_options = dict(
            _layout_ports=self._layout_ports,
            _inner_svg=self._inner_svg,
            _x_label=self._x_label,
            _y_label=self._y_label,
            _inner_color=self._inner_color,
            _inner_color_selected=self._inner_color_selected,
            _label_color=self._label_color,
        )
        default_options.update(options)

        return ComponentInstance(
            name=name,
            ctype=self,
            ports=clone_ports(self.ports),
            **default_options
        )

    def __repr__(self):
        return "ComponentType(name={}, ports={!r}, params={!r})".format(self.name, self.ports, self.params)


class ComponentInstance(HasPorts, DOMWidget):
    """
    The actual component instances making up a circuit.
    """

    _view_name = Unicode("SVGComponentView", sync=True)

    name = Unicode("ci", sync=True)
    ctype = Instance(klass=ComponentType, sync=True)
    param_assignments = Dict(sync=True)

    _circuit = Any(sync=True)
    _inner_svg = Unicode("", sync=True)
    _x_label = Float(0., sync=True)
    _y_label = Float(0., sync=True)
    _inner_color = Unicode("#3366AA", sync=True)
    _inner_color_selected = Unicode("red", sync=True)
    _label_color = Unicode("white", sync=True)

    def __repr__(self):
        return self.name

    # def __init__(self, *args, **kwargs):
    #     super(ComponentInstance, self).__init__(*args, **kwargs)
    #     self.on_trait_change(self._update_circuit, "_circuit")
    #
    # def _update_circuit(self):


class Connection(DOMWidget):
    """
    Class representing a single connection between two ports.
    """
    _view_name = Unicode("SVGConnectionView", sync=True)

    source = Instance(klass=Port, sync=True)
    target = Instance(klass=Port, sync=True)

    _circuit = Any(sync=True)

    _color = Unicode("black", sync=True)
    _color_selected = Unicode("red", sync=True)
    _cr = Float(140., sync=True)

    def _source_changed(self, name, old, new):
        new.connections_out.append(self)
        self._color = new.domain._color
        self._color_selected = new.domain._color_selected

    def _target_changed(self, name, old, new):
        new.connections_in.append(self)

    def remove(self):
        """
        Remove the connection from the circuit and the relevant connections_in/out lists of its ports.
        """
        remove_self = lambda ll: filter(lambda c: c is not self, ll)
        self._circuit.connections = remove_self(self._circuit.connections)
        self.source.connections_out = remove_self(self.source.connections_out)
        self.target.connections_in = remove_self(self.target.connections_in)

    def __repr__(self):
        return "Connection({!r}, {!r})".format(self.source, self.target)


class Circuit(ComponentType):
    """
    Circuit widget class. A circuit is defined by:

        1. A name
        2. A set of valid connection domains for connection

    """

    _view_name = Unicode("SVGCircuitView", sync=True)

    name = Unicode("C", sync=True)
    width = Float(1024, sync=True)
    height = Float(600, sync=True)
    zoom = Tuple((0., 0., 1.), sync=True)

    # domains = List(sync=True)

    # component_types = List(sync=True)
    component_instances = List(sync=True)
    connections = List(sync=True)

    svg_snapshots = List()

    # ct = Dict()
    c = Dict(AttrDict({}))

    selected_element = Any(sync=True)

    _layout_x0 = Float(80., sync=True)
    _layout_y0 = Float(120., sync=True)

    _layout_dx = Float(180., sync=True)
    _layout_dy = Float(180., sync=True)

    _port_y = Float(30., sync=True)
    _dock_color = Unicode("#3366AA", sync=True)

    def __init__(self, *a, **kw):
        super(Circuit, self).__init__(*a, **kw)
        self.on_msg(self.handle_element_msg)


    def layout_ports(self, ports):
        """
        Overriden layout method from HasPorts. See HasPorts.layout_ports doc.
        """
        dx = self.width / (len(ports) + 1.)
        for kk, p in enumerate(ports):
            p._x = (kk + 1) * dx
            p._y = self._port_y
            p._phi = pi / 2.

    # def _component_types_changed(self, name, old, new):
    #     for ct in new:
    #         ct._circuit = self

    def _connections_changed(self, name, old, new):
        sold = set(old)
        snew = set(new)

        for ct in snew - sold:
            ct._circuit = self
            ct.on_msg(self.handle_element_msg)

    @staticmethod
    def delete_connection(c):
        """
        Remove the connection c from its circuit.
        """
        # print "disconnecting", c
        c.remove()

    def connect(self, p1, p2, verify=True):
        """
        Connect two ports p1 and p2 and optionally verify they can be connected.
        """
        if verify and not Domain.valid_connection(p1, p2):
            return
        if p1.domain.causal and not p1.is_source:
            p1, p2 = p2, p1
        # print "connecting", p1, p2
        new_connection = Connection(source=p1, target=p2)

        self.connections = self.connections + [new_connection]

    def _component_instances_changed(self, name, old, new):
        ny = int((self.height - self._layout_y0) / self._layout_dy)
        kk = len(old)

        self.c = AttrDict({c.name: c for c in new})

        for ci in new:
            if not ci._circuit is self:
                ci._circuit = self
                kkx = kk // ny
                kky = kk % ny
                ci._x = self._layout_x0 + kkx * self._layout_dx
                ci._y = self._layout_y0 + kky * self._layout_dy
                ci.on_msg(self.handle_element_msg)

                kk += 1
                for p in ci.ports:
                    p._circuit = self
                    p.on_msg(self.handle_element_msg)

    def _ports_changed(self, name, old, new):
        super(Circuit, self)._ports_changed(name, old, new)
        for p in new:
            p._circuit = self
            p.on_msg(self.handle_element_msg)

    def port_msg(self, p, m):
        """
        Handle click event sent from Port model.
        """
        if m == "click":
            se = self.selected_element
            if se:
                if isinstance(se, Port):
                    if p is self.selected_element:
                        self.selected_element = None
                        return
                    elif Domain.valid_connection(se, p):
                        # print "valid connection, connecting..."
                        self.connect(se, p)
                        return
            self.selected_element = p

    def component_msg(self, c, m):
        """
        Handle click event sent from Component model.
        """
        if m == "click":
            if self.selected_element is c:
                return
            self.selected_element = c

    def connection_msg(self, c, m):
        """
        Handle click event sent from Connection model.
        """
        if m == "click":
            if self.selected_element is c:
                self.delete_connection(c)
                self.selected_element = None
            else:
                self.selected_element = c

    def msg(self, m):
        """
        Handle click event sent from Circuit model.
        """
        if m == "click":
            if self.selected_element:
                self.selected_element = None
        elif isinstance(m, dict):
            if m["type"] == "captured_svg":
                self.svg_snapshots.append(m["data"])
                if self._svg_callback:
                    self._svg_callback(self, m["data"])
                    self._svg_callback = None




    def handle_element_msg(self, element, msg):
        """
        Handle messages from the front-end.
        """
        # print element, msg
        if isinstance(element, Port):
            return self.port_msg(element, msg)
        if isinstance(element, ComponentInstance):
            return self.component_msg(element, msg)
        if isinstance(element, Connection):
            return self.connection_msg(element, msg)
        if element is self:
            return self.msg(msg)

    def capture_svg(self, callback=None):
        """Request current svg to be sent to backend."""
        self.send("capture_svg")
        self._svg_callback = callback



    def save_last_svg(self, filename, append_suffix=True):
        """Save the svg code to a file, append .svg if not present"""
        if not len(self.svg_snapshots):
            return

        if append_suffix and not filename.endswith(".svg"):
            filename = filename + ".svg"

        with open(filename, "w") as svgfile:
            svgfile.write(self.svg_snapshots[-1])

        display(FileLink(filename))

    def save_svg(self, filename, append_suffix=True):
        def _callback(*a):
            self.save_last_svg(filename, append_suffix)
        self.capture_svg(callback=_callback)



class HorizontalContainer(ContainerWidget):

    def __init__(self, *a, **kw):
        super(HorizontalContainer, self).__init__(*a, **kw)
        self.on_displayed(self._make_horizontal)

    def _make_horizontal(self, _):
        self.remove_class("vbox")
        self.add_class("hbox")


class CircuitBuilder(PopupWidget):
    """
    Adds additional controls to the circuit widget for
    adding/removing external ports and component instances.
    """
    _view_name = Unicode("CircuitBuilderView", sync=True)
    circuit = Instance(klass=Circuit, sync=True)
    domains = List()
    _domains_by_name = Dict()
    components = List()
    _components_by_name = Dict()

    def _components_changed(self, name, old, new):
        self.add_comp_type.values = {c.name: c.name for c in new}
        self._components_by_name = {c.name: c for c in new}

    def _domains_changed(self, name, old, new):
        self.add_port_domain.values = {d.name: d.name for d in new}
        self._domains_by_name = {d.name: d for d in new}

    def __init__(self, domains, components, circuit=None, **kwargs):
        super(CircuitBuilder, self).__init__(**kwargs)
        self.button_text = "Launch CircuitBuilder"
        self.description = circuit.name


        #####  make controls
        self.basic_controls = HorizontalContainer()
        self.add_component_controls = HorizontalContainer()
        self.add_port_controls = HorizontalContainer()
        self.change_component_controls = HorizontalContainer()
        self.change_port_controls = HorizontalContainer()

        # 1) basic controls
        self.reset_view_btn = ButtonWidget(description="Reset view")
        self.reset_view_btn.on_click(self.reset_view)

        self.circname = TextWidget(description="Circuit name", value=circuit.name)
        self.rename_circ_btn = ButtonWidget(description="Rename")
        self.rename_circ_btn.on_click(self.rename_circuit)
        self.add_port_btn = ButtonWidget(description="New Port")
        self.add_port_btn.on_click(self.show_add_port_controls)
        self.add_comp_btn = ButtonWidget(description="New Component")
        self.add_comp_btn.on_click((self.show_add_comp_controls))
        # self.download_btn = ButtonWidget(description="SaveAsSVG")
        # self.download_btn.on_click()

        self.basic_controls.children = [
            self.reset_view_btn,
            self.circname,
            self.rename_circ_btn,
            self.add_port_btn,
            self.add_comp_btn,
        ]

        # 2) add component
        self.add_comp_name = TextWidget(description="Component name")
        self.add_comp_type = DropdownWidget(description="ComponentType")
        self.add_comp_add = ButtonWidget(description="Add Component")
        self.add_comp_add.on_click(self.add_component)

        self.add_comp_back = ButtonWidget(description="Back")
        self.add_comp_back.on_click(self.back)

        self.add_component_controls.children = [
            self.add_comp_name,
            self.add_comp_type,
            self.add_comp_add,
            self.add_comp_back,
        ]

        # 3) add port
        self.add_port_name = TextWidget(description="Port name")
        self.add_port_domain = DropdownWidget(description="Domain")
        self.add_port_domain.on_trait_change(self._update_port_directions, "value_name")
        self.add_port_direction = DropdownWidget(description="Direction",
                                                 values={"in": "Input", "out": "Output"})
        self.add_port_add = ButtonWidget(description="Add Port")
        self.add_port_add.on_click(self.add_port)
        self.add_port_back = ButtonWidget(description="Back")
        self.add_port_back.on_click(self.back)

        self.add_port_controls.children = [
            self.add_port_name,
            self.add_port_domain,
            self.add_port_direction,
            self.add_port_add,
            self.add_port_back,
        ]

        # 4) change component
        self.mod_comp_name = TextWidget(description="Component name")
        self.mod_comp_rename = ButtonWidget(description="Rename")
        self.mod_comp_rename.on_click(self.rename_component)
        self.mod_comp_delete = ButtonWidget(description="Delete")
        self.mod_comp_delete.on_click(self.delete_component)
        self.mod_comp_back = ButtonWidget(description="Back")
        self.mod_comp_back.on_click(self.back)

        self.change_component_controls.children = [
            self.mod_comp_name,
            self.mod_comp_rename,
            self.mod_comp_delete,
            self.mod_comp_back,
        ]

        # 5) change port
        self.mod_port_name = TextWidget(description="Port name")
        self.mod_port_rename = ButtonWidget(description="Rename")
        self.mod_port_rename.on_click(self.rename_port)
        self.mod_port_dec = ButtonWidget(description="<")
        self.mod_port_inc = ButtonWidget(description=">")
        self.mod_port_dec.on_click(self.dec_port_order)
        self.mod_port_inc.on_click(self.inc_port_order)

        self.mod_port_delete = ButtonWidget(description="Delete")
        self.mod_port_delete.on_click(self.delete_port)
        self.mod_port_back = ButtonWidget(description="Back")
        self.mod_port_back.on_click(self.back)

        self.change_port_controls.children = [
            self.mod_port_name,
            self.mod_port_rename,
            self.mod_port_dec,
            self.mod_port_inc,
            self.mod_port_delete,
            self.mod_port_back,
        ]

        # has to come at end!!
        self.domains = domains
        self.components = components
        self.circuit = circuit

        self.circuit.on_trait_change(self._handle_circuit_selection, "selected_element")
        self.circuit.on_trait_change(self._handle_circuit_name, "name")


        self.children = [
            self.basic_controls,
            self.add_component_controls,
            self.add_port_controls,
            self.change_component_controls,
            self.change_port_controls,
            self.circuit
        ]
        self.back()



    def _handle_circuit_selection(self):
        e = self.circuit.selected_element
        if e:
            if isinstance(e, Port) and e.is_ext:
                self.back()
                self.show_mod_port_controls(e)
                return
            elif isinstance(e, ComponentInstance):
                self.back()
                self.show_mod_comp_controls(e)
                return
        self.back()

    def _handle_circuit_name(self):
        self.circname.value = self.circuit.name
        self.description = self.circuit.name

    def reset_view(self, *_):
        self.circuit.zoom = (0., 0., 1.)

    def back(self, *_):
        for c in [
            self.add_component_controls,
            self.add_port_controls,
            self.change_component_controls,
            self.change_port_controls,
        ]:
            c.visible = False
        self.basic_controls.visible = True

    def show_mod_comp_controls(self, c):
        self.basic_controls.visible = False
        self.change_component_controls.visible = True
        self.mod_comp_name.value = c.name

    def show_mod_port_controls(self, p):
        self.basic_controls.visible = False
        self.change_port_controls.visible = True
        self.mod_port_name.value = p.name

    def show_add_port_controls(self, *_):
        self.basic_controls.visible = False
        self.add_port_controls.visible = True

    def show_add_comp_controls(self, *_):
        self.basic_controls.visible = False
        self.add_component_controls.visible = True

    def _update_port_directions(self):
        d = self._domains_by_name.get(self.add_port_domain.value_name, False)
        if isinstance(d, Domain):
            self.add_port_direction.visible = d.causal

    def rename_circuit(self, *_):
        if len(self.circname.value):
            self.circuit.name = self.circname.value

    def add_component(self, *_):
        ctype = self._components_by_name[self.add_comp_type.value_name]
        cname = self.add_comp_name.value

        if len(cname) and not cname in self.circuit.c:

            new_comp = ctype.make_instance(cname)
            self.circuit.component_instances = self.circuit.component_instances + [new_comp]

    def add_port(self, *_):
        d = self._domains_by_name[self.add_port_domain.value_name]
        dir = self.add_port_direction.value_name
        if not d.causal:
            dir = "inout"
        pname = self.add_port_name.value
        if len(pname) and not pname in self.circuit.p:
            newp = Port(name=pname, domain=d, direction=dir)
            self.circuit.ports = self.circuit.ports + [newp]


    def rename_component(self, *_):
        c = self.circuit.selected_element
        if not isinstance(c, ComponentInstance):
            return
        newname = self.mod_comp_name.value
        if len(newname) and not newname in self.circuit.c:
            del self.circuit.c[c.name]
            c.name = newname
            self.circuit.c[c.name] = c

    def rename_port(self, *_):
        p = self.circuit.selected_element
        if not isinstance(p, Port):
            return
        newname = self.mod_port_name.value
        if len(newname) and not newname in self.circuit.p:
            del self.circuit.p[p.name]
            p.name = newname
            self.circuit.p[p.name] = p

    def delete_component(self, *_):
        c = self.circuit.selected_element
        if not isinstance(c, ComponentInstance) \
                or not c in self.circuit.component_instances:
            return
        self.circuit.component_instances = filter(lambda cc: cc is not c,
                                                  self.circuit.component_instances)
        for p in c.ports:
            for cc in p.connections_in + p.connections_out:
                cc.remove()

        self.circuit.selected_element = None

    def delete_port(self, *_):
        p = self.circuit.selected_element
        if not isinstance(p, Port) \
                or not p in self.circuit.ports:
            return
        self.circuit.ports = filter(lambda pp: pp is not p,
                                                  self.circuit.ports)

        for c in p.connections_in + p.connections_out:
            c.remove()

        self.circuit.selected_element = None


    def dec_port_order(self, *_):
        p = self.circuit.selected_element
        if not isinstance(p, Port) \
                or not p in self.circuit.ports:
            return
        ps = list(self.circuit.ports)
        ii = ps.index(p)
        ps.pop(ii)
        ii = max(1, ii)
        self.circuit.ports = ps[:ii-1] + [p] + ps[ii-1:]


    def inc_port_order(self, *_):
        p = self.circuit.selected_element
        if not isinstance(p, Port) \
                or not p in self.circuit.ports:
            return
        ps = list(self.circuit.ports)
        ii = ps.index(p)
        ps.pop(ii)
        self.circuit.ports = ps[:ii+1] + [p] + ps[ii+1:]






