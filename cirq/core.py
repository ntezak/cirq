# coding=utf-8
"""
This is the core implementation of the Cirq package.
"""
# -----------------------------------------------------------------------------
# Copyright (c) 2014, Nikolas Tezak <Nikolas.Tezak@gmail.com>
#
#  Distributed under the terms of the Modified BSD License.
#
#  The full license is in the file LICENSE.txt, distributed with this software.
#-----------------------------------------------------------------------------
from IPython.core.display import SVG

__author__ = 'Nikolas Tezak'

import json
import os
from types import FunctionType
from math import sin, cos, pi

from IPython.utils.traitlets import (Unicode, Bool, Instance, Any, Enum,
                                     HasTraits, Float, List, Tuple, Dict)
from IPython.html.widgets import DOMWidget, ContainerWidget, ButtonWidget, PopupWidget, TextWidget, DropdownWidget
from IPython.display import display, Javascript, FileLink


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

    # def __init__(self, name, causal, one2one=False, **kw):
    # super(Domain, self).__init__(**kw)
    # self.name = name
    # self.causal = causal
    # self.one2one = one2one
    #     if not causal and one2one:
    #         raise ValueError("Only non-causal links can be one to one.")

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
    """Clone a list of ports. See Port.clone() doc.
    :param ports: list of ports
    """
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
        if not len(self.p) == len(new):
            raise ValueError("Ports need all have unique names.")

    def layout_ports(self, ports):
        """
        Create layout for a list of ports by setting their individual coordinates
        and orientation angles. Override this method by setting the _layout_ports property.

        :param ports: sequence of ports
        """

        if self._layout_ports:
            return self._layout_ports(self, ports)

        dphi = 2 * pi / len(ports)
        for kk, p in enumerate(ports):
            p._x = self._r * cos(kk * dphi + pi)
            p._y = self._r * sin(kk * dphi + pi)
            p._phi = kk * dphi + pi

    def ports_for_domain(self, domain):
        """
        Return all ports (in correct order) for a given `domain`.
        :param domain: Domain object to filter ports by.
        """
        return filter(lambda p: p.domain is domain, self.ports)


class Port(DOMWidget):
    """
    Connection port element. Can be associated with a ComponentType, a ComponentInstance or a Circuit.

    Notes
    -----

    Any Port belongs to a given Domain object. If the domain is causal,
    then the port `direction` must either be `in` or `out`.

    A Port also keeps track of its `_parent` element, the overall `_circuit` it belongs to,
    as well as what connections lead into it and emanate from it.

    The `connections_in` and `connections_out` List-traits store all connections having
    a given Port instance as their target or source, respectively.

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

    # noinspection PyUnusedLocal
    def _domain_changed(self, name, old, new):
        if new.causal:
            if self.direction == "inout":
                self.direction = "in"
        else:
            self.direction = "inout"

    # noinspection PyUnusedLocal
    def _direction_changed(self, name, old, new):
        if self.domain:
            # noinspection PyUnresolvedReferences
            if self.domain.causal:
                if new not in ["in", "out"]:
                    raise ValueError("Causal domains can only have associated input and output ports")

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


def inputs(names, domain):
    """
    Create a list of named input ports for a given causal domain.

    :param names: Sequence of names
    :type names: iterable
    :param domain: Common connection domain for all ports
    :type domain: Domain
    :return: list of input ports
    :rtype: list
    """
    if not domain.causal:
        raise ValueError()
    return [Port(name=n, domain=domain, direction="in") for n in names]


def outputs(names, domain):
    """
    Create a list of named output ports for a given causal domain.

    :param names: Sequence of names
    :type names: iterable
    :param domain: Common connection domain for all ports
    :type domain: Domain
    :return: list of output ports
    :rtype: list
    """
    if not domain.causal:
        raise ValueError()
    return [Port(name=n, domain=domain, direction="out") for n in names]


def inouts(names, domain):
    """
    Create a list of named inout ports for a given non-causal domain.

    :param names: Sequence of names
    :type names: iterable
    :param domain: Common connection domain for all ports
    :type domain: Domain
    :return: list of inout ports
    :rtype: list
    """
    if domain.causal:
        raise ValueError()
    return [Port(name=n, domain=domain, direction="in") for n in names]


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

    A shortcut to accessing the component instance's ports is given by the `p` attribute,
    e.g., `my_instance.p.MyPortName` resolves correctly.
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
        if self._circuit:
            # noinspection PyTypeChecker
            return repr(self._circuit) + ".c." + self.name
        return self.name


class Connection(DOMWidget):
    """
    Class representing a single connection between two ports.

    A connection is always stored in a directed fashion,
    having a `source` and a `target` attribute to store these ports.
    When these attributes are changed the connection automatically
    registers itself with in the `connections_out` list trait of the `source`-Port
    and the `connections_in` list trait of the `target` point.

    Note that a Connection object does not verify whether it is valid.
    """

    # def __init__(self, source, target, **kw):
    # super(Connection, self).__init__(self, **kw)
    # self.source = source
    # self.target = target

    _view_name = Unicode("SVGConnectionView", sync=True)

    source = Instance(klass=Port, sync=True)
    target = Instance(klass=Port, sync=True)

    _circuit = Any(sync=True)

    _color = Unicode("black", sync=True)
    _color_selected = Unicode("red", sync=True)
    _cr = Float(140., sync=True)

    # noinspection PyProtectedMember
    def _source_changed(self, _, old, new):
        if old:
            remove_self = lambda ll: filter(lambda c: c is not self, ll)
            # old.connections_out.remove(self)
            # until we have eventful List traits, need to do this:
            old.connections_out = remove_self(old.connections_out)

        new.connections_out.append(self)
        self._color = new.domain._color
        self._color_selected = new.domain._color_selected

    def _target_changed(self, _, old, new):
        if old:
            # old.connections_in.remove(self)
            remove_self = lambda ll: filter(lambda c: c is not self, ll)
            old.connections_in = remove_self(old.connections_in)

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
        return "Connection(source={!r}, target={!r})".format(self.source, self.target)


class Circuit(ComponentType):
    """
    Circuit widget class. A circuit is defined by:

        1. A name
        2. A set of valid connection domains for connection


    A shortcut to accessing the top-level circuit ports is given by the `p` attribute,
    e.g., `my_circuit.p.MyPortName` resolves correctly.

    Similarly, component instances belonging to the circuit can be accessed via the `c` attribute,
    e.g., as `my_circuit.c.MyComponentInstanceName`.

    To find out connected *nets*, i.e., ports of a non-causal domain, that are mutually connected,
    use the `my_circuit.get_nets(domain)` method.

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
    _svg_callbacks = List()

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

    def __init__(self, **kw):
        super(Circuit, self).__init__(**kw)
        self.on_msg(self.handle_element_msg)

    def layout_ports(self, ports):
        """
        Overriden layout method from HasPorts. See HasPorts.layout_ports doc.

        :param ports: Sequence of ports to compute layout for
        """
        # noinspection PyTypeChecker
        dx = self.width / (len(ports) + 1.)
        for kk, p in enumerate(ports):
            p._x = (kk + 1) * dx
            p._y = self._port_y
            p._phi = pi / 2.

    # def _component_types_changed(self, name, old, new):
    # for ct in new:
    # ct._circuit = self

    def _connections_changed(self, _, old, new):
        sold = set(old)
        snew = set(new)

        for ct in snew - sold:
            ct._circuit = self
            ct.on_msg(self.handle_element_msg)

    @staticmethod
    def delete_connection(c):
        """
        Remove the connection c from its circuit.

        :param c: The connection that should be removed.
        """
        c.remove()

    def connect(self, p1, p2, verify=True):
        """
        Connect two ports p1 and p2 and optionally verify they can be connected.

        :param p1: The first port to be connected
        :param p2: The second port to be connected
        :param verify: Boolean, whether to verify that a connection between `p1` and `p2` is valid, default `True`.
        """
        if verify and not Domain.valid_connection(p1, p2):
            return
        if p1.domain.causal and not p1.is_source:
            p1, p2 = p2, p1
        # print "connecting", p1, p2
        new_connection = Connection(source=p1, target=p2)

        self.connections = self.connections + [new_connection]

    def _component_instances_changed(self, _, old, new):
        # noinspection PyUnresolvedReferences
        ny = int((self.height - self._layout_y0) / self._layout_dy)
        kk = len(old)

        self.c = AttrDict({c.name: c for c in new})

        if not len(self.c) == len(new):
            raise ValueError("Component instances need all have unique names.")

        for ci in new:
            if not ci._circuit is self:
                ci._circuit = self
                kkx = kk // ny
                kky = kk % ny
                # noinspection PyTypeChecker
                ci._x = self._layout_x0 + kkx * self._layout_dx
                # noinspection PyTypeChecker
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

        :param p: Port element that triggered the message
        :param m: Received message object
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

        :param c: Component instance that triggered the message
        :param m: Received message object
        """
        if m == "click":
            if self.selected_element is c:
                return
            self.selected_element = c

    def connection_msg(self, c, m):
        """
        Handle click event sent from Connection model.

        :param c: Connection that triggered the message
        :param m: Received message object
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

        :param m: Received message object
        """
        if m == "click":
            if self.selected_element:
                self.selected_element = None
        elif isinstance(m, dict):
            if m["type"] == "captured_svg":
                # noinspection PyUnresolvedReferences
                self.svg_snapshots.append(m["data"])
                # noinspection PyTypeChecker
                if len(self._svg_callbacks):
                    # noinspection PyUnresolvedReferences
                    self._svg_callbacks.pop(0)(self, m["data"])

    def handle_element_msg(self, element, msg):
        """
        Handle messages from the front-end.

        :param element: Circuit element that triggered the message
        :param msg: Message object
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
        """
        Request current svg to be sent to backend. The requested capture is carried out asynchronously
        and the result is appended to the `svg_snapshots` trait.

        :param callback: Function to be called when the svg has been received from the widget front-end.
        """
        self.send("capture_svg")
        if callback:
            # noinspection PyUnresolvedReferences
            self._svg_callbacks.append(callback)

    # noinspection PyUnresolvedReferences
    def save_last_image(self, filename, display_link=True):
        """
        Save the last snapshot of the circuit. Supported output formats are SVG, PNG and PDF
         (the latter two only if cairosvg is installed).


        :param filename: File name/path under which the image should be stored.
        :param display_link: Display a FileLink for download
        """
        # noinspection PyTypeChecker
        if not len(self.svg_snapshots):
            return

        if filename[-4:] in [".jpg", ".eps", ".bmp", ".tif"]:
            raise ValueError("Cannot write format {}".format(filename[-3:].upper()))

        if filename[-4:] not in [".svg", ".png", ".pdf"]:
            filename += ".svg"

        if filename.endswith(".svg"):
            with open(filename, "w") as svgfile:
                # noinspection PyUnresolvedReferences
                svgfile.write(self.svg_snapshots[-1])
        else:
            try:
                import cairosvg
            except ImportError, e:
                print "Could not import cairosvg for PNG/PDF rendering:\n" + str(e)
                return

            if filename.endswith(".png"):
                converter = cairosvg.svg2png
            elif filename.endswith(".pdf"):
                converter = cairosvg.svg2pdf
            else:
                raise ValueError(filename)

            with open(filename, "wb") as imgfile:
                converter(self.svg_snapshots[-1], write_to=imgfile)

        if display_link:
            display(FileLink(filename))

    def save_image(self, filename):
        """
        Create and save a snapshot of the circuit. Supported output formats are SVG, PNG and PDF
         (the latter two only if cairosvg is installed).

        :param filename: File name/path to store the image at.
        """

        def _callback(*_):
            self.save_last_image(filename, display_link=False)

        self.capture_svg(callback=_callback)

    def get_nets(self, domain):
        """
        For a non-causal `domain`, compute all connected nets/cliques/groups of ports attached to each other.
        Returns a list of lists with circuit ports appearing before component ports.

        :param domain: The domain for which to compute the nets
        """
        all_ports = self.ports_for_domain(domain) + sum((c.ports_for_domain(domain)
                                                         for c in self.component_instances), [])
        nets = {p: (kk, {p}) for kk, p in enumerate(all_ports)}

        # for later
        nets_index = {p: kk for p, (kk, _) in nets.items()}

        nets_by_nk = {}

        # resolve connections
        for c in self.connections:
            # source and target are of same clique, so combine them
            s, t = c.source, c.target
            if s.domain is not domain or t.domain is not domain:
                continue

            (ns, pss), (nt, pts) = nets[s], nets[t]

            mn = min(ns, nt)
            ma = max(ns, nt)
            clique = pss | pts
            for pp in clique:
                # for all members of the clique,
                # set the net index to the lowest possible index
                # store all members of the clique
                nets[pp] = mn, clique

            nets_by_nk[mn] = clique
            if ns != nt and ma in nets_by_nk:
                del nets_by_nk[ma]

        return [sorted(nets_by_nk[kk], key=nets_index.get) for kk in sorted(nets_by_nk.keys())]

    @classmethod
    def load_json(cls, json_path):
        """
        Create a Circuit from a JSON file.

        :param json_path: JSON file containing the circuit representation
        :return: Circuit object
        """

        with open(json_path, "r") as jsonfile:
            ret = cls.from_json(jsonfile.readall())
        return ret

    @classmethod
    def from_json(cls, json_string):
        """
        Create a Circuit from a JSON-serialized string.

        :param json_string: JSON string representing the circuit
        :return: Circuit object
        """
        return cls.from_jsonifiable(json.loads(json_string))

    @classmethod
    def from_jsonifiable(cls, obj):
        """
        Create a Circuit from simple python dicts and lists. See source code of `to_jsonifiable`.

        :param obj: dicts and lists describing the circuit.
        :return: Circuit object
        """
        name = obj.get("name", None)
        if not name:
            raise ValueError()

        domains = {k: Domain(name=k, causal=v["causal"], one2one=v["one2one"])
                   for k, v in obj.get("domains", {}).items()}

        def _make_port(port_info):
            return Port(name=port_info["name"], domain=domains[port_info["domain"]], direction=port_info["direction"])

        ports = map(_make_port, obj.get("ports", []))
        ports_dict = {p.name: p for p in ports}

        component_types = {k: ComponentType(name=k, ports=map(_make_port, v["ports"]))
                           for k, v in obj.get("component_types", {}).items()}

        component_instances = {k: component_types[v].make_instance(k)
                               for k, v in obj.get("component_instances", {}).items()}

        def _resolve_port(cn, pn):
            if cn == name:
                return ports_dict[pn]
            return component_instances[cn].p[pn]

        ret = Circuit(name=name, ports=ports,
                      component_instances=component_instances.values())

        ret.connections = [Connection(source=_resolve_port(sn, spn),
                                      target=_resolve_port(tn, tpn))
                           for sn, spn, tn, tpn in obj.get("connections", [])]
        return ret

    # noinspection PyTypeChecker
    def to_jsonifiable(self):
        """
        Return a representation in terms of nested `dict` and `list` objects that can be converted to JSON.
        """
        domains = {p.domain for p in self.ports}
        ctypes = set()
        for c in self.component_instances:
            domains = domains | {p.domain for p in c.ports}
            ctypes.add(c.ctype)

        def _port_info(p):
            return {
                "name": p.name,
                "domain": p.domain.name,
                "direction": p.direction,
            }

        ports = map(_port_info, self.ports)
        domains_dict = {d.name: {"causal": d.causal, "one2one": d.one2one} for d in domains}
        ctypes_dict = {ct.name: {"ports": map(_port_info, ct.ports)} for ct in ctypes}
        component_instances_dict = {c.name: c.ctype.name for c in self.component_instances}
        # noinspection PyProtectedMember
        connections = [(c.source._parent.name, c.source.name, c.target._parent.name, c.target.name)
                       for c in self.connections]
        return {
            "name": self.name,
            "domains": domains_dict,
            "ports": ports,
            "component_types": ctypes_dict,
            "component_instances": component_instances_dict,
            "connections": connections,
        }

    def to_json(self):
        """
        Return a JSON string encoding the circuit. Re-create the circuit via the classmethod `Circuit.from_json`.
        """
        return json.dumps(self.to_jsonifiable())

    def save_json(self, json_path):
        """
        Save a JSON representation of the circuit.

        :param json_path: The file path under which to save the circuit definition.
        """
        with open(json_path, "w") as jsonfile:
            jsonfile.write(self.to_json())

    def show_svg_snapshot(self, index=-1):
        """
        Show a list of download links

        :param index: Which snapshot to show, defaults to the last one taken
        """
        # noinspection PyUnresolvedReferences
        return SVG(self.svg_snapshots[index])

    def _repr_svg_(self):
        # noinspection PyTypeChecker
        if len(self.svg_snapshots):
            # noinspection PyUnresolvedReferences
            return self.svg_snapshots[-1]


class HorizontalContainer(ContainerWidget):
    """
    Equivalent to a `ContainerWidget` but with a css-class `hbox` instead of `vbox` for horizontal layout.
    May be deprecated soon.
    """

    def __init__(self, **kw):
        super(HorizontalContainer, self).__init__(**kw)
        self.on_displayed(self._make_horizontal)

    def _make_horizontal(self, _):
        self.remove_class("vbox")
        self.add_class("hbox")


class CircuitBuilder(PopupWidget):
    """
    Comprehensive circuit creation widget that has control dialogs for adding/modifying component instances as well as
     external ports.
    """
    _view_name = Unicode("CircuitBuilderView", sync=True)
    circuit = Instance(klass=Circuit, sync=True)
    domains = List()
    _domains_by_name = Dict()
    components = List()
    _components_by_name = Dict()

    def __init__(self, domains, components, circuit, **kwargs):
        super(CircuitBuilder, self).__init__(**kwargs)

        if isinstance(circuit, str):
            circuit = Circuit(name=circuit)

        self.button_text = "Launch CircuitBuilder"
        self.description = circuit.name

        def _resize_inputs(el):
            el.set_css({"width": "100px"})

        # ####  make controls
        self.basic_controls = HorizontalContainer()
        self.add_component_controls = HorizontalContainer()
        self.add_port_controls = HorizontalContainer()
        self.change_component_controls = HorizontalContainer()
        self.change_port_controls = HorizontalContainer()

        # 1) basic controls
        self._reset_view_btn = ButtonWidget(description="Reset view")
        self._reset_view_btn.on_click(self.reset_view)

        self._circuit_name = TextWidget(description="Circuit name", value=circuit.name)
        self._circuit_name.on_displayed(_resize_inputs)

        self._rename_circ_btn = ButtonWidget(description="Rename")
        self._rename_circ_btn.on_click(self._rename_circuit)
        self._add_port_btn = ButtonWidget(description="New Port")
        self._add_port_btn.on_click(self.add_port_dialog)
        self._add_comp_btn = ButtonWidget(description="New Component")
        self._add_comp_btn.on_click(self.add_component_dialog)

        self.basic_controls.children = [
            self._reset_view_btn,
            self._circuit_name,
            self._rename_circ_btn,
            self._add_port_btn,
            self._add_comp_btn,
        ]

        # 2) add component
        self._add_comp_type = DropdownWidget(description="ComponentType")
        self._add_comp_name = TextWidget(description="Component name")
        self._add_comp_name.on_displayed(_resize_inputs)

        self._add_comp_add = ButtonWidget(description="Add Component")
        self._add_comp_add.on_click(self._add_component)

        self._add_comp_back = ButtonWidget(description="Back")
        self._add_comp_back.on_click(self.back)

        self.add_component_controls.children = [
            self._add_comp_type,
            self._add_comp_name,
            self._add_comp_add,
            self._add_comp_back,
        ]

        # 3) add port
        self._add_port_name = TextWidget(description="Port name")
        self._add_port_name.on_displayed(_resize_inputs)

        self._add_port_domain = DropdownWidget(description="Domain")
        self._add_port_domain.on_trait_change(self._update_port_directions, "value_name")
        self._add_port_direction = DropdownWidget(description="Direction",
                                                  values={"in": "Input", "out": "Output"})
        self._add_port_add = ButtonWidget(description="Add Port")
        self._add_port_add.on_click(self._add_port)
        self._add_port_back = ButtonWidget(description="Back")
        self._add_port_back.on_click(self.back)

        self.add_port_controls.children = [
            self._add_port_name,
            self._add_port_domain,
            self._add_port_direction,
            self._add_port_add,
            self._add_port_back,
        ]

        # 4) change component
        self._mod_comp_name = TextWidget(description="Component name")
        self._mod_comp_name.on_displayed(_resize_inputs)
        self._mod_comp_rename = ButtonWidget(description="Rename")
        self._mod_comp_rename.on_click(self._rename_component)
        self._mod_comp_delete = ButtonWidget(description="Delete")
        self._mod_comp_delete.on_click(self.delete_selected_component)
        self._mod_comp_back = ButtonWidget(description="Back")
        self._mod_comp_back.on_click(self.back)

        self.change_component_controls.children = [
            self._mod_comp_name,
            self._mod_comp_rename,
            self._mod_comp_delete,
            self._mod_comp_back,
        ]

        # 5) change port
        self._mod_port_name = TextWidget(description="Port name")
        self._mod_port_name.on_displayed(_resize_inputs)
        self._mod_port_rename = ButtonWidget(description="Rename")
        self._mod_port_rename.on_click(self._rename_port)
        self._mod_port_dec = ButtonWidget(description="<")
        self._mod_port_inc = ButtonWidget(description=">")
        self._mod_port_dec.on_click(self.move_selected_port_up)
        self._mod_port_inc.on_click(self.move_selected_port_down)

        self._mod_port_delete = ButtonWidget(description="Delete")
        self._mod_port_delete.on_click(self.delete_selected_port)
        self._mod_port_back = ButtonWidget(description="Back")
        self._mod_port_back.on_click(self.back)

        self.change_port_controls.children = [
            self._mod_port_name,
            self._mod_port_rename,
            self._mod_port_dec,
            self._mod_port_inc,
            self._mod_port_delete,
            self._mod_port_back,
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

    # noinspection PyDocstring
    def reset_view(self, *_):
        """
        Reset the pan and zoom of the circuit editor widget.
        """
        self.circuit.zoom = (0., 0., 1.)

    # noinspection PyDocstring
    def back(self, *_):
        """
        Quit all sub-dialogs and display the default controls for renaming the circuit.
        """
        for c in [
            self.add_component_controls,
            self.add_port_controls,
            self.change_component_controls,
            self.change_port_controls,
        ]:
            c.visible = False
        self.basic_controls.visible = True

    def modify_component_dialog(self, c):
        """
        Show the control dialog for modifying a component.

        :param c: The component to be modified
        """
        self.basic_controls.visible = False
        self.change_component_controls.visible = True
        self._mod_comp_name.value = c.name

    def modify_port_dialog(self, p):
        """
        Show the control dialog for modifying an external port.

        :param p: The external port to be modified
        """
        self.basic_controls.visible = False
        self.change_port_controls.visible = True
        self._mod_port_name.value = p.name

    # noinspection PyDocstring
    def add_port_dialog(self, *_):
        """
        Show the dialog to add a new external port.
        """
        self.basic_controls.visible = False
        self.add_port_controls.visible = True

    # noinspection PyDocstring
    def add_component_dialog(self, *_):
        """
        Show the dialog to add a new component instance.
        """
        self.basic_controls.visible = False
        self.add_component_controls.visible = True

    # noinspection PyDocstring,PyTypeChecker
    def delete_selected_component(self, *_):
        """
        Delete the currently selected component.
        """
        c = self.circuit.selected_element
        if not isinstance(c, ComponentInstance) \
                or not c in self.circuit.component_instances:
            return
        self.circuit.component_instances = filter(lambda comp: comp is not c,
                                                  self.circuit.component_instances)
        # noinspection PyTypeChecker
        for p in c.ports:
            for cc in p.connections_in + p.connections_out:
                cc.remove()

        self.circuit.selected_element = None

    # noinspection PyDocstring,PyTypeChecker
    def delete_selected_port(self, *_):
        """
        Delete the currently selected external port.
        """
        p = self.circuit.selected_element
        if not isinstance(p, Port) \
                or not p in self.circuit.ports:
            return
        self.circuit.ports = filter(lambda pp: pp is not p,
                                    self.circuit.ports)

        # noinspection PyUnresolvedReferences
        for c in p.connections_in + p.connections_out:
            c.remove()

        self.circuit.selected_element = None

    # noinspection PyDocstring,PyTypeChecker
    def move_selected_port_up(self, *_):
        """
        Move the selected port up in the overall order of external ports.
        """
        p = self.circuit.selected_element
        if not isinstance(p, Port) \
                or not p in self.circuit.ports:
            return
        ps = list(self.circuit.ports)
        ii = ps.index(p)
        ps.pop(ii)
        ii = max(1, ii)
        self.circuit.ports = ps[:ii - 1] + [p] + ps[ii - 1:]

    # noinspection PyDocstring,PyTypeChecker
    def move_selected_port_down(self, *_):
        """
        Move the selected port down in the overall order of external ports.
        """
        p = self.circuit.selected_element
        if not isinstance(p, Port) \
                or not p in self.circuit.ports:
            return
        ps = list(self.circuit.ports)
        ii = ps.index(p)
        ps.pop(ii)
        self.circuit.ports = ps[:ii + 1] + [p] + ps[ii + 1:]

    # noinspection PyUnusedLocal
    def _components_changed(self, name, old, new):
        self._add_comp_type.values = {c.name: c.name for c in new}
        self._components_by_name = {c.name: c for c in new}

    # noinspection PyUnusedLocal
    def _domains_changed(self, name, old, new):
        self._add_port_domain.values = {d.name: d.name for d in new}
        self._add_port_domain.value_name = new[0].name
        self._domains_by_name = {d.name: d for d in new}
        self._update_port_directions()

    def _handle_circuit_selection(self):
        e = self.circuit.selected_element
        if e:
            if isinstance(e, Port) and e.is_ext:
                self.back()
                self.modify_port_dialog(e)
                return
            elif isinstance(e, ComponentInstance):
                self.back()
                self.modify_component_dialog(e)
                return
        self.back()

    def _handle_circuit_name(self):
        self._circuit_name.value = self.circuit.name
        self.description = self.circuit.name

    def _update_port_directions(self):
        d = self._domains_by_name.get(self._add_port_domain.value_name, False)
        if isinstance(d, Domain):
            self._add_port_direction.visible = d.causal

    def _rename_circuit(self, *_):
        if len(self._circuit_name.value):
            self.circuit.name = self._circuit_name.value

    # noinspection PyUnresolvedReferences
    def _add_component(self, *_):
        ctype = self._components_by_name[self._add_comp_type.value_name]
        cname = self._add_comp_name.value

        if len(cname) and not cname in self.circuit.c:
            new_comp = ctype.make_instance(cname)
            self.circuit.component_instances = self.circuit.component_instances + [new_comp]

    # noinspection PyUnresolvedReferences
    def _add_port(self, *_):
        d = self._domains_by_name[self._add_port_domain.value_name]
        direction = self._add_port_direction.value_name
        if not d.causal:
            direction = "inout"
        pname = self._add_port_name.value
        if len(pname) and not pname in self.circuit.p:
            newp = Port(name=pname, domain=d, direction=direction)
            self.circuit.ports = self.circuit.ports + [newp]

    def _rename_component(self, *_):
        c = self.circuit.selected_element
        if not isinstance(c, ComponentInstance):
            return
        newname = self._mod_comp_name.value
        if len(newname) and not newname in self.circuit.c:
            del self.circuit.c[c.name]
            c.name = newname
            self.circuit.c[c.name] = c

    def _rename_port(self, *_):
        p = self.circuit.selected_element
        if not isinstance(p, Port):
            return
        newname = self._mod_port_name.value
        if len(newname) and not newname in self.circuit.p:
            del self.circuit.p[p.name]
            p.name = newname
            self.circuit.p[p.name] = p
