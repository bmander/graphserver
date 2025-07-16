import json
from typing import Any

from osmdb import OSMDB


class Visitor(object):
    """Basic interface for an OSM visitor."""

    def visit(self, db: OSMDB, *args: Any) -> None:
        pass


class UniqueTagNames(object):
    def visit(self, db: OSMDB, feature_type: str) -> None:
        tag_names = {}
        if feature_type == "nodes":
            query = "SELECT tags FROM nodes"
        else:
            query = "SELECT tags FROM ways"

        for row in db.execute(query):
            t = json.loads(row[0])
            for k in t.keys():
                if k not in tag_names:
                    tag_names[k] = 1

        for k in tag_names.keys():
            print("KEY: %s" % k)


class UniqueTagValues(object):
    def visit(self, db: OSMDB, feature_type: str, tag_name: str) -> None:
        tag_values = {}
        if feature_type == "nodes":
            query = "SELECT tags FROM nodes"
        else:
            query = "SELECT tags FROM ways"

        for row in db.execute(query):
            t = json.loads(row[0])
            if tag_name in t:
                tag_values[t[tag_name]] = 1

        for k in tag_values.keys():
            print("TAG VALUE: %s" % k)


def main() -> None:
    from sys import argv

    visitor_cls, osmdb_file = argv[1:3]
    try:
        visitor = globals()[visitor_cls]()
    except KeyError:
        raise Exception("Visitor not found.")

    db = OSMDB(osmdb_file)

    if len(argv) > 3:
        extra = argv[3:]
    else:
        extra = []
    # print(extra)
    visitor.visit(db, *extra)


if __name__ == "__main__":
    main()
