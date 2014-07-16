/** ---------------------------------------------------------------------------
 Copyright (c) 2014, Nikolas Tezak <Nikolas.Tezak@gmail.com>

 Distributed under the terms of the Modified BSD License.

 The full license is in the file LICENSE.txt, distributed with this software.
 ----------------------------------------------------------------------------- */



// Add helper methods for String manipulation


// Allows simplified version of Python's str.format
// http://stackoverflow.com/questions/610406/javascript-equivalent-to-printf-string-format
if (!String.format) {
    String.format = function (format) {
        var args = Array.prototype.slice.call(arguments, 1);
        return format.replace(/\{(\d+)\}/g, function (match, number) {
            return args[number] !== undefined ? args[number] : match;
        });
    };
}

// Port of Python's str.endswith
// http://stackoverflow.com/questions/280634/endswith-in-javascript
if (typeof String.endsWith !== 'function') {
    String.endsWith = function (str, suffix) {
        return str.indexOf(suffix, str.length - suffix.length) !== -1;
    };
}

console.log("[loading cirq.js]");

require(["//cdnjs.cloudflare.com/ajax/libs/d3/3.4.9/d3.min.js", "widgets/js/widget"], function (d3, WidgetManager) {

    // Query whether a particular circuit element is currently the selected one
    // Will change when multi-selections become possible
    var selectedq = function (model) {
        if (model === null || model.get("_circuit") === null) {
            return false;
        }
        return (model === model.get("_circuit").get("selected_element"));
    };

    // Abstract class for svg-views to inherit from
    // code taken from IPython's ContainerView widget
    // and modified
    // Copyright (c) IPython Development Team.
    // Distributed under the terms of the Modified BSD License.

    var ContainerView = IPython.DOMWidgetView.extend({

        add_child_view: function (parent_el, model) {
            var view = this.create_child_view(model);
            parent_el.append(view.$el);
            if (this.is_displayed) {
                model.trigger('displayed');
            }
        },

        remove_child_view: function (model) {
//            console.log("removing", model, this);
            var view = this.child_views[model.id];
            if (view !== undefined) {
                view.stopListening();
                return this.delete_child_view(model);
            }
        },

        update_children: function (old_list, new_list, parent) {
            // Called when the children list changes.
            this.do_diff(old_list,
                new_list,
                $.proxy(this.remove_child_view, this),
                $.proxy(this.add_child_view, this, parent));
        }

    });

    // View of a single Port (of either the whole circuit or a component)
    //noinspection JSLint
    var SVGPortView = IPython.DOMWidgetView.extend({
        render: function () {
            var el = document.createElementNS('http://www.w3.org/2000/svg', 'g'),
                that = this;
            this.setElement(el);
            this.svg = d3.select(el)
                .attr("class", "port_marker")
                .attr("pointer-events", "painted")
                .style("cursor", "pointer");


            this.svg.on("click", function () {
                that.send("click");
            });


            var circuit = this.model.get("_circuit");

            if (circuit !== null) {
                this.listenTo(this.model.get("_circuit"), "change:selected_element", $.proxy(this.update_selected, this));
            } else {
                //noinspection JSLint
                this.model.on("change:_circuit", function (model, value) {
                    if (value) {
                        this.listenTo(value, "change:selected_element", $.proxy(this.update_selected, this));
                    }
                }, this);
            }

            this.update();
        },


        update_selected: function (cmodel, value) {
            var color,
                selected = value === this.model;

            if (selected) {
                color = this.model.get("domain").get("_color_selected");
            } else {
                color = this.model.get("domain").get("_color");
            }
            this.svg.selectAll(".port_marker").attr("fill", color);
        },


        update: function () {
            var dir = this.model.get("direction"),
                x = this.model.get("_x"),
                y = this.model.get("_y"),
                phi = this.model.get("_phi"),
                x_label = this.model.get("_x_label"),
                y_label = this.model.get("_y_label"),
                name = this.model.get("name"),
                size = this.model.get("_size"),
                color;

            if (selectedq(this.model)) {
                color = this.model.get("domain").get("_color_selected");
            } else {
                color = this.model.get("domain").get("_color");
            }

            this.svg.attr("transform", "translate(" + x + ", " + y + ")");
            this.svg.html("");

            if (this.model.get("_parent") === this.model.get("_circuit")) {
                phi += Math.PI;
            }
            //noinspection FallThroughInSwitchStatementJS
            if (dir === "in" || dir === "out") {
                if (dir === "in") {
                    phi = phi + Math.PI;
                }
                this.svg.append("path")
                    .attr("class", "port_marker_invis")
                    .attr("d", String.format("M -{0} {0} L -{0} -{0} L {0} 0 L -{0} {0}", 1.5 * size))
                    .attr("fill", color)
                    .attr("opacity", 0)
                    .attr("stroke", "none")
                    .attr("transform", "rotate(" + (phi / 2.0 / Math.PI * 360.0) + ")");
                this.svg.append("path")
                    .attr("class", "port_marker")
                    .attr("d", String.format("M -{0} {0} L -{0} -{0} L {0} 0 L -{0} {0}", size))
                    .attr("fill", color)
                    .attr("stroke", "none")
                    .attr("transform", "rotate(" + (phi / 2.0 / Math.PI * 360.0) + ")");
            } else if (dir === "inout") {
                this.svg.append("circle")
                    .attr("class", "port_marker_invis")
                    .attr("cx", 0)
                    .attr("cy", 0)
                    .attr("r", 1.5 * size)
                    .attr("fill", color)
                    .attr("opacity", 0)
                    .attr("stroke", "none");
                this.svg.append("circle")
                    .attr("class", "port_marker")
                    .attr("cx", 0)
                    .attr("cy", 0)
                    .attr("r", size)
                    .attr("fill", color)
                    .attr("stroke", "none");
            } else if (dir === "default") {
                console.log("ERROR", this.svg, this.model);
            }
            this.svg.append("text")
                .attr("class", "port_label")
                .attr("x", x_label)
                .attr("y", y_label)
                .attr("text-anchor", "left")
                .attr("fill", "black")
                .attr("font-face", "sans serif")
                .attr("font-size", "12")
                .text(name);
        }

    });

    WidgetManager.register_widget_view("SVGPortView", SVGPortView);

    // View of a circuit component (instance)
    //noinspection JSLint
    var SVGComponentView = ContainerView.extend({
        render: function () {

            var el = document.createElementNS('http://www.w3.org/2000/svg', 'g'),
                that = this;
            this.setElement(el);
            this.svg = d3.select(el)
                .attr("class", "component")
                .attr("pointer-events", "painted")
                .style("cursor", "move");


            this.svg_inner = this.svg.append("g")
                .attr("class", "component_body");

            this.svg_ports = this.svg.append("g")
                .attr("class", "component_ports");

            //noinspection JSLint
            this.svg.call(d3.behavior.drag()
                .on("dragstart", function () {
//                    /*console.log*/(d3.select(d3.event.sourceEvent.srcElement).attr("class"));
                    if (d3.select(d3.event.sourceEvent.srcElement).attr("class").indexOf("port_marker") > -1) {
                        return;
                    }
                    that.send("click");
                })
                .on("drag", function () {
                    var x, y;
                    x = that.model.get("_x") + d3.event.dx;
                    y = that.model.get("_y") + d3.event.dy;
                    that.svg.attr("transform", String.format("translate({0},{1})", x, y));
                    that.model.set("_x", x);
                    that.model.set("_y", y);
                })
                .on("dragend", function (name) {
                    that.model.save();
                }));


            this.update_children([], this.model.get("ports"), this.$el.find("g.component_ports"));

            var circuit = this.model.get("_circuit");
            if (circuit !== null) {
                this.listenTo(this.model.get("_circuit"), "change:selected_element", $.proxy(this.update_selected, this));
            } else {
                //noinspection JSLint
                this.model.on("change:_circuit", function (model, value) {
                    if (value) {
                        this.listenTo(value, "change:selected_element", $.proxy(this.update_selected, this));
                    }
                }, this);
            }

            this.model.on("change:ports", function (model, value) {
                this.update_children(model.previous("ports"), value, this.$el.find("g.component_ports"));
            }, this);

            this.update();
        },

        update_selected: function (cmodel, smodel) {
            // update colors if selected
            var selected = this.model === smodel,
                color;
            if (selected) {
                color = this.model.get("_inner_color_selected");
            } else {
                color = this.model.get("_inner_color");
            }
            this.svg.select(".inner").attr("fill", color);
            this.svg.select(".outer").attr("fill", color);

        },

        update: function () {
            var x = this.model.get("_x"),
                y = this.model.get("_y"),
                r = this.model.get("_r"),
                x_label = this.model.get("_x_label"),
                y_label = this.model.get("_y_label"),
                color = this.model.get("_inner_color"),
                label_color = this.model.get("_label_color"),
                name = this.model.get("name"),
                inner_svg = this.model.get("_inner_svg"),
                ctype_name = this.model.get("ctype").get("name");


            this.svg.attr("transform", "translate(" + x + ", " + y + ")");

            // if svg not customized
            if (inner_svg === "") {

                // make symbol with two concentric circles, the outer one being nearly transparent
                this.svg_inner.html("");
                this.svg_inner.append("circle")
                    .attr("class", "outer")
                    .attr("cx", 0)
                    .attr("cy", 0)
                    .attr("r", r)
                    .attr("fill", color)
                    .attr("opacity", ".4")
                    .attr("stroke", "none");

                this.svg_inner.append("circle")
                    .attr("class", "inner")
                    .attr("cx", 0)
                    .attr("cy", 0)
                    .attr("r", r / 2)
                    .attr("fill", color)
                    .attr("stroke", "none");
            } else {
                this.svg_inner.html(inner_svg);
            }

            // add tooltip giving the component type
            this.svg_inner
                .append("title")
                .text(ctype_name);

            // add label
            this.svg_inner
                .append("text")
                .attr("class", "component_label")
                .attr("x", x_label)
                .attr("y", y_label)
                .attr("text-anchor", "middle")
                .attr("fill", label_color)
                .attr("font-face", "sans serif") // TODO make option
                .attr("font-size", "14") //TODO make option
                .text(name);

            // update selected
            var circuit_model = this.model.get("_circuit");
            if (circuit_model) {
                this.update_selected(circuit_model, circuit_model.get("selected_element"));
            }
        }

    });

    WidgetManager.register_widget_view("SVGComponentView", SVGComponentView);

    // View of a connection between two ports
    //noinspection JSLint
    var SVGConnectionView = IPython.DOMWidgetView.extend({
        render: function () {
            var el = document.createElementNS('http://www.w3.org/2000/svg', 'g'),
                that = this;

            this.setElement(el);
            this.svg = d3.select(el)
                .attr("class", "connection")
                .attr("pointer-events", "stroke")
                .style("cursor", "crosshair")
                .on("click", function () {
                    // transmit click events to backend
                    that.send("click");
                });

            // listen for coordinate changes for both the source and target ports/components
            this.init_listener(this.model.get("source"));
            this.init_listener(this.model.get("target"));

            // if source/target port is changed, update event listeners to new port model
            this.model.on("change:source", function (model, value) {
                var ps = model.previous("source");
                this.stopListening(ps.get("_parent"));
                this.stopListening(ps);
                this.init_listener(value);
            }, this);
            this.model.on("change:target", function (model, value) {
                var ps = model.previous("target");
                this.stopListening(ps.get("_parent"));
                this.stopListening(ps);
                this.init_listener(value);
            }, this);

            // register event listener for the selected element of the overall circuit
            var circuit = this.model.get("_circuit");

            // handle both the case where the _circuit trait is already set and where it still needs to be set
            if (circuit !== null) {
                this.listenTo(this.model.get("_circuit"), "change:selected_element", $.proxy(this.update_selected, this));
            } else {
                //noinspection JSLint
                this.model.on("change:_circuit", function (model, value) {
                    if (value) {
                        this.listenTo(value, "change:selected_element", $.proxy(this.update_selected, this));
                    }
                }, this);
            }


            var color = this.model.get("_color");

            // mouseover paths
            this.svg.append("path")
                .attr("class", "invis")
                .attr("stroke", color)
                .attr("stroke-width", "20")
                .attr("opacity", 0)
                .attr("fill", "none");

            // visible connection
            this.svg.append("path")
                .attr("class", "vis")
                .attr("stroke", color)
                .attr("stroke-width", "4")
                .attr("fill", "none");


            this.update();
        },

        get_coords: function (pmodel) {

//             console.log(pmodel);

            var parent = pmodel.get("_parent"),
                x1 = pmodel.get("_x"),
                y1 = pmodel.get("_y"),
                phi = pmodel.get("_phi"),
                x0 = parent.get("_x"),
                y0 = parent.get("_y"),
                cr = this.model.get("_cr"),
                x,
                y;

            x = x0 + x1;
            y = y0 + y1;
            return {
                x: x,
                y: y,
                xc: x + cr * Math.cos(phi),
                yc: y + cr * Math.sin(phi)
            };

        },

        init_listener: function (pmodel) {
            this.listenTo(pmodel, "change", $.proxy(this.update, this));
            this.listenTo(pmodel.get("_parent"), "change", $.proxy(this.update, this));
        },

        update_selected: function (cmodel, value) {
            // check if this connection is the selected element
            // and if so, change color

            var selected = value === this.model,
                color;

            if (selected) {
                color = this.model.get("_color_selected");
            } else {
                color = this.model.get("_color");
            }
            this.svg.select("path.vis").attr("stroke", color);
        },

        update: function () {

            var cs = this.get_coords(this.model.get("source")),
                ct = this.get_coords(this.model.get("target"));

            // redraw cubic bezier between ports with control points
            this.svg.selectAll("path")
                .attr("d", String.format(
                    "M {0} {1} C {2} {3} {4} {5} {6} {7}",
                    cs.x,
                    cs.y,
                    cs.xc,
                    cs.yc,
                    ct.xc,
                    ct.yc,
                    ct.x,
                    ct.y
                ));

        }
    });

    WidgetManager.register_widget_view("SVGConnectionView", SVGConnectionView);


    // View of the whole circuit editor pane
    var SVGCircuitView = ContainerView.extend({
        render: function () {

            var container = d3.select(this.el),
                that = this;

            this.svg = container.append("svg")
                .attr("width", this.model.get("width"))
                .attr("height", this.model.get("height"))
                .attr("class", "circuit_editor")
                .attr("version", "1.1")
                .attr("xmlns", "http://www.w3.org/2000/svg");


            // Set up panning and zooming behavior
            this.zoom = d3.behavior.zoom()
                .on("zoom", function () {
                    var trans = d3.event.translate,
                        scale = d3.event.scale;

                    // update transformation
                    that.svg_main.attr("transform",
                            "translate(" + trans + ")" +
                            "scale(" + scale + ")");

                    // during zoom only update front-end backbone model
                    that.model.set("zoom", [trans[0], trans[1], scale]);

                })
                .on("zoomend", function () {
                    // after zoom initiate synchronization with python backend
                    that.touch();
                });

            // limit zoom factors
            this.zoom.scaleExtent([0.25, 2.0]);

            // set up group to capture zoom events
            this.svg_zoom = this.svg.append("g")
                .attr("class", "zoom_area")
                .attr("pointer-events", "all")
                .on("click.deselect", function () {
                    // also capture single click events for element deselection
                    that.send("click");
                })
                .call(this.zoom);

            // add white background rectangle to zoom-capture group
            this.svg_zoom.append("rect")
                .attr("width", "100%")
                .attr("height", "100%")
                .attr("fill", "white");

            // add zoomable main container for all visual elements
            this.svg_main = this.svg.append("g")
                .attr("pointer-events", "all")
                .attr("class", "main");

            // update with current zoom parameters
            var z = this.model.get("zoom");
            this.svg_main
                .attr("transform",
                    "translate(" + z.slice(0, 2) + ") scale(" + z[2] + ")");

            // update d3 zoom object with params from backbone model
            this.zoom.translate(z.slice(0, 2));
            this.zoom.scale(z[2]);

            // container for connections
            this.svg_connections = this.svg_main.append("g")
                .attr("class", "connections");

            // container for external ports
            this.svg_ports = this.svg_main.append("g")
                .attr("class", "ports");

            // container for component instances
            this.svg_components = this.svg_main.append("g")
                .attr("class", "components");

            // draw external port background rectangle
            this.svg_ports.append("rect")
                .attr("width", this.model.get("width") * 0.9)
                .attr("x", this.model.get("width") * 0.05)
                .attr("height", this.model.get("_port_y"))
                .attr("class", "dock")
                .attr("rx", 10).attr("ry", 10)
                .attr("fill", this.model.get("_dock_color"))
                .attr("opacity", 0.4)
                .attr("stroke", "none");

            // initialize components, ports and connections
            this.update_children([], this.model.get("component_instances"), this.$el.find("g.components"));
            this.update_children([], this.model.get("ports"), this.$el.find("g.ports"));
            this.update_children([], this.model.get("connections"), this.$el.find("g.connections"));

            // assure that connections, external ports and instances are always synchronized with backbone model
            this.model.on("change:component_instances", function (model, value) {
                this.update_children(model.previous("component_instances"), value, this.$el.find("g.components"));
            }, this);
            this.model.on("change:ports", function (model, value) {
                this.update_children(model.previous("ports"), value, this.$el.find("g.ports"));
            }, this);
            this.model.on("change:connections", function (model, value) {
                this.update_children(model.previous("connections"), value, this.$el.find("g.connections"));
            }, this);

            this.update();

        },


        update: function () {

            // update pan/zoom
            if (this.model.hasChanged("zoom")) {
                var z = this.model.get("zoom");
                this.svg_main
                    .attr("transform",
                        "translate(" + z.slice(0, 2) + ") scale(" + z[2] + ")");
                this.zoom.translate(z.slice(0, 2));
                this.zoom.scale(z[2]);
            }

            // update width/height
            if (this.model.hasChanged("width")
                    || this.model.hasChanged("height")) {
                this.svg
                    .attr("width", this.model.get("width"))
                    .attr("height", this.model.get("height"));
                this.svg_ports.select("rect.dock")
                    .attr("width", this.model.get("width") * 0.9)
                    .attr("x", this.model.get("width") * 0.05);
            }
        },

        on_msg: function (content) {
            // handle request for capturing current svg
            if (content === "capture_svg") {
                this.send({
                    type: "captured_svg",
                    data: this.$el.html()
                });
            }
        }

    });

    WidgetManager.register_widget_view("SVGCircuitView", SVGCircuitView);

    // View of the Circuit Builder (slightly modified version of
    // IPython's PopupView, which allows for a wider view area.
    //noinspection JSLint
    var CircuitBuilderView = WidgetManager._view_types.PopupView.extend({
        show: function () {
            //noinspection JSLint
            CircuitBuilderView.__super__.show.apply(this);
            if (this.popped_out) {
                this.$window.css("width", this.model.get("circuit").get("width") + "px");
                this.$window.css("left", Math.max(0, (($('body').outerWidth() - this.$window.outerWidth()) / 2) +
                    $(window).scrollLeft()) + "px");

            } else {
                this.$window.css("width", "");
            }
        }


    });

    WidgetManager.register_widget_view("CircuitBuilderView", CircuitBuilderView);


});

console.log("[loaded cirq.js]");