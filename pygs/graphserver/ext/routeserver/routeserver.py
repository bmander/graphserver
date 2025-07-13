import argparse
import sys
import time

from flask import Flask, Response, request

from graphserver.core import State, WalkOptions
from graphserver.graphdb import GraphDatabase

try:
    import json
except ImportError:
    import simplejson as json
import os

import yaml


class SelfEncoderHelper(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "to_jsonable"):
            return obj.to_jsonable()
        return json.JSONEncoder.default(self, obj)


def postprocess_path_raw(vertices, edges):
    retbuilder = []

    retbuilder.append("vertices")
    for i, vertex in enumerate(vertices):
        retbuilder.append("%d %s" % (i, str(vertex)))

    retbuilder.append("")
    retbuilder.append("states")
    for i, vertex in enumerate(vertices):
        retbuilder.append("%d %s" % (i, str(vertex.state)))

    retbuilder.append("")
    retbuilder.append("edges")
    for i, edge in enumerate(edges):
        retbuilder.append("%d %s" % (i, str(edge.payload)))

    return "\n".join(retbuilder)


def postprocess_path(vertices, edges, vertex_events, edge_events):
    context = {}

    for edge1, vertex1, edge2, vertex2 in zip(
        [None] + edges, vertices, edges + [None], vertices[1:] + [None, None]
    ):
        # fire vertex events
        for handler in vertex_events:
            if handler.applies_to(edge1, vertex1, edge2):
                event = handler(edge1, vertex1, edge2, context=context)
                if event is not None:
                    yield handler.__class__.__name__, event

        # fire edge events
        for handler in edge_events:
            if handler.applies_to(vertex1, edge2, vertex2):
                event = handler(vertex1, edge2, vertex2, context=context)
                if event is not None:
                    yield handler.__class__.__name__, event


class RouteServer:
    def __init__(
        self, graphdb_filename, vertex_events, edge_events, vertex_reverse_geocoders
    ):
        graphdb = GraphDatabase(graphdb_filename)
        self.graph = graphdb.incarnate()
        self.vertex_events = vertex_events
        self.edge_events = edge_events
        self.vertex_reverse_geocoders = vertex_reverse_geocoders

    def bounds(self, jsoncallback=None):
        """returns bounding box that encompases the bounding box from all member reverse geocoders"""

        ll, bb, rr, tt = None, None, None, None

        for reverse_geocoder in self.vertex_reverse_geocoders:
            gl, gb, gr, gt = reverse_geocoder.bounds()
            ll = min(ll, gl) if ll else gl
            bb = min(bb, gb) if bb else gb
            rr = max(rr, gr) if rr else gr
            tt = max(tt, gt) if tt else gt

        if jsoncallback is None:
            return json.dumps([ll, bb, rr, tt])
        else:
            return "%s(%s)" % (jsoncallback, json.dumps([ll, bb, rr, tt]))

    def vertices(self):
        return "\n".join([vv.label for vv in self.graph.vertices])

    def get_vertex_id_raw(self, lat, lon):
        for reverse_geocoder in self.vertex_reverse_geocoders:
            ret = reverse_geocoder(lat, lon)
            if ret is not None:
                return ret

        return None

    def get_vertex_id(self, lat, lon):
        return json.dumps(self.get_vertex_id_raw(lat, lon))

    def path(
        self,
        origin,
        dest,
        currtime=None,
        time_offset=None,
        transfer_penalty=0,
        walking_speed=1.0,
        hill_reluctance=1.5,
        turn_penalty=None,
        walking_reluctance=None,
        max_walk=None,
        jsoncallback=None,
    ):
        performance = {}

        if currtime is None:
            currtime = int(time.time())

        if time_offset is not None:
            currtime += time_offset

        # time path query
        t0 = time.time()
        wo = WalkOptions()
        wo.transfer_penalty = transfer_penalty
        wo.walking_speed = walking_speed
        wo.hill_reluctance = hill_reluctance
        if turn_penalty is not None:
            wo.turn_penalty = turn_penalty
        if walking_reluctance is not None:
            wo.walking_reluctance = walking_reluctance
        if max_walk is not None:
            wo.max_walk = max_walk
        spt = self.graph.shortest_path_tree(origin, dest, State(1, currtime), wo)

        try:
            vertices, edges = spt.path(dest)
        except Exception as e:
            return json.dumps({"error": str(e)})

        performance["path_query_time"] = time.time() - t0

        t0 = time.time()
        narrative = list(
            postprocess_path(vertices, edges, self.vertex_events, self.edge_events)
        )
        performance["narrative_postprocess_time"] = time.time() - t0

        t0 = time.time()
        wo.destroy()
        spt.destroy()
        performance["cleanup_time"] = time.time() - t0

        ret = {"narrative": narrative, "performance": performance}

        if jsoncallback is None:
            return json.dumps(ret, indent=2, cls=SelfEncoderHelper)
        else:
            return "%s(%s)" % (
                jsoncallback,
                json.dumps(ret, indent=2, cls=SelfEncoderHelper),
            )

    def geompath(
        self,
        lat1,
        lon1,
        lat2,
        lon2,
        currtime=None,
        time_offset=None,
        transfer_penalty=0,
        walking_speed=1.0,
        hill_reluctance=1.5,
        turn_penalty=None,
        walking_reluctance=None,
        max_walk=None,
        jsoncallback=None,
    ):
        origin_vertex_label = self.get_vertex_id_raw(lat1, lon1)
        dest_vertex_label = self.get_vertex_id_raw(lat2, lon2)

        if origin_vertex_label is None:
            raise Exception("could not find a vertex near (%s,%s)" % (lat1, lon1))
        if dest_vertex_label is None:
            raise Exception("could not find a vertex near (%s,%s)" % (lat2, lon2))

        return self.path(
            origin_vertex_label,
            dest_vertex_label,
            currtime,
            time_offset,
            transfer_penalty,
            walking_speed,
            hill_reluctance,
            turn_penalty,
            walking_reluctance,
            max_walk,
            jsoncallback,
        )

    def path_retro(
        self,
        origin,
        dest,
        currtime=None,
        time_offset=None,
        transfer_penalty=0,
        walking_speed=1.0,
    ):
        if currtime is None:
            currtime = int(time.time())

        if time_offset is not None:
            currtime += time_offset

        wo = WalkOptions()
        wo.transfer_penalty = transfer_penalty
        wo.walking_speed = walking_speed
        spt = self.graph.shortest_path_tree_retro(origin, dest, State(1, currtime), wo)
        wo.destroy()

        vertices, edges = spt.path_retro(origin)

        ret = list(
            postprocess_path(vertices, edges, self.vertex_events, self.edge_events)
        )

        spt.destroy()

        return json.dumps(ret, indent=2, cls=SelfEncoderHelper)

    def path_raw(self, origin, dest, currtime=None):
        if currtime is None:
            currtime = int(time.time())

        wo = WalkOptions()
        spt = self.graph.shortest_path_tree(origin, dest, State(1, currtime), wo)
        wo.destroy()

        vertices, edges = spt.path(dest)

        ret = postprocess_path_raw(vertices, edges)

        spt.destroy()

        return ret

    def path_raw_retro(self, origin, dest, currtime):
        wo = WalkOptions()
        spt = self.graph.shortest_path_tree_retro(origin, dest, State(1, currtime), wo)
        wo.destroy()

        vertices, edges = spt.path_retro(origin)

        ret = postprocess_path_raw(vertices, edges)

        spt.destroy()

        return ret


def import_class(handler_class_path_string):
    sys.path.append(os.getcwd())

    handler_class_path = handler_class_path_string.split(".")

    class_name = handler_class_path[-1]
    package_name = ".".join(handler_class_path[:-1])

    package = __import__(package_name, fromlist=[class_name])

    try:
        handler_class = getattr(package, class_name)
    except AttributeError:
        raise AttributeError("Can't find %s. Only %s" % (class_name, dir(package)))

    return handler_class


def get_handler_instances(handler_definitions, handler_type):
    if handler_definitions is None:
        return

    if handler_type not in handler_definitions:
        return

    for handler in handler_definitions[handler_type]:
        handler_class = import_class(handler["name"])
        handler_instance = handler_class(**handler.get("args", {}))

        yield handler_instance


def create_app(graphdb_filename, config_filename):
    handler_definitions = yaml.safe_load(open(config_filename))

    edge_events = list(get_handler_instances(handler_definitions, "edge_handlers"))
    vertex_events = list(get_handler_instances(handler_definitions, "vertex_handlers"))
    vertex_reverse_geocoders = list(
        get_handler_instances(handler_definitions, "vertex_reverse_geocoders")
    )

    print("edge event handlers:")
    for e in edge_events:
        print(f"   {e}")
    print("vertex event handlers:")
    for v in vertex_events:
        print(f"   {v}")
    print("vertex reverse geocoders:")
    for g in vertex_reverse_geocoders:
        print(f"   {g}")

    rs = RouteServer(graphdb_filename, vertex_events, edge_events, vertex_reverse_geocoders)
    app = Flask(__name__)

    @app.route("/bounds")
    def bounds():
        cb = request.args.get("callback")
        data = rs.bounds(jsoncallback=cb)
        mimetype = "application/javascript" if cb else "application/json"
        return Response(data, mimetype=mimetype)

    @app.route("/vertices")
    def vertices():
        return Response(rs.vertices(), mimetype="text/plain")

    @app.route("/get_vertex_id")
    def get_vertex_id():
        lat = float(request.args["lat"])
        lon = float(request.args["lon"])
        return Response(rs.get_vertex_id(lat, lon), mimetype="application/json")

    @app.route("/path")
    def path_route():
        args = request.args
        data = rs.path(
            origin=args["origin"],
            dest=args["dest"],
            currtime=int(args.get("currtime")) if args.get("currtime") else None,
            time_offset=int(args.get("time_offset")) if args.get("time_offset") else None,
            transfer_penalty=int(args.get("transfer_penalty", 0)),
            walking_speed=float(args.get("walking_speed", 1.0)),
            hill_reluctance=float(args.get("hill_reluctance", 1.5)),
            turn_penalty=float(args.get("turn_penalty")) if args.get("turn_penalty") else None,
            walking_reluctance=float(args.get("walking_reluctance")) if args.get("walking_reluctance") else None,
            max_walk=float(args.get("max_walk")) if args.get("max_walk") else None,
            jsoncallback=args.get("callback"),
        )
        mimetype = "application/javascript" if args.get("callback") else "application/json"
        return Response(data, mimetype=mimetype)

    @app.route("/geompath")
    def geompath_route():
        args = request.args
        data = rs.geompath(
            lat1=float(args["lat1"]),
            lon1=float(args["lon1"]),
            lat2=float(args["lat2"]),
            lon2=float(args["lon2"]),
            currtime=int(args.get("currtime")) if args.get("currtime") else None,
            time_offset=int(args.get("time_offset")) if args.get("time_offset") else None,
            transfer_penalty=int(args.get("transfer_penalty", 0)),
            walking_speed=float(args.get("walking_speed", 1.0)),
            hill_reluctance=float(args.get("hill_reluctance", 1.5)),
            turn_penalty=float(args.get("turn_penalty")) if args.get("turn_penalty") else None,
            walking_reluctance=float(args.get("walking_reluctance")) if args.get("walking_reluctance") else None,
            max_walk=float(args.get("max_walk")) if args.get("max_walk") else None,
            jsoncallback=args.get("callback"),
        )
        mimetype = "application/javascript" if args.get("callback") else "application/json"
        return Response(data, mimetype=mimetype)

    @app.route("/path_retro")
    def path_retro_route():
        args = request.args
        data = rs.path_retro(
            origin=args["origin"],
            dest=args["dest"],
            currtime=int(args.get("currtime")) if args.get("currtime") else None,
            time_offset=int(args.get("time_offset")) if args.get("time_offset") else None,
            transfer_penalty=int(args.get("transfer_penalty", 0)),
            walking_speed=float(args.get("walking_speed", 1.0)),
        )
        return Response(data, mimetype="application/json")

    @app.route("/path_raw")
    def path_raw_route():
        args = request.args
        currtime = int(args.get("currtime")) if args.get("currtime") else None
        data = rs.path_raw(args["origin"], args["dest"], currtime)
        return Response(data, mimetype="text/plain")

    @app.route("/path_raw_retro")
    def path_raw_retro_route():
        args = request.args
        currtime = int(args["currtime"])
        data = rs.path_raw_retro(args["origin"], args["dest"], currtime)
        return Response(data, mimetype="text/plain")

    return app


def main():
    parser = argparse.ArgumentParser(description="Graphserver route server")
    parser.add_argument("graphdb_filename")
    parser.add_argument("config_filename")
    parser.add_argument(
        "-p",
        "--port",
        default=8080,
        type=int,
        help="Port to serve HTTP",
    )

    args = parser.parse_args()

    app = create_app(args.graphdb_filename, args.config_filename)
    app.run(host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
