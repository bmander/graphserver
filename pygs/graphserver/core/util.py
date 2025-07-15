from ctypes import c_int


def failsafe(return_arg_num_on_failure):
    """Decorator to prevent segfaults during failed callbacks."""

    def deco(func):
        def safe(*args):
            try:
                return func(*args)
            except Exception:
                import sys
                import traceback

                sys.stderr.write("ERROR: Exception during callback ")
                try:
                    sys.stderr.write("%s\n" % (map(str, args)))
                except Exception:
                    pass
                traceback.print_exc()
                return args[return_arg_num_on_failure]

        return safe

    return deco


def indent(a: str, n: int) -> str:
    return "\n".join([" " * n + x for x in a.split("\n")])


# TODO this is probably defined somewhere else, too
def unparse_secs(secs):
    return "%02d:%02d:%02d" % (secs // 3600, (secs % 3600) // 60, secs % 60)


ServiceIdType = c_int
