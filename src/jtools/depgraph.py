from __future__ import annotations

import subprocess
import tempfile
import venv
from functools import lru_cache
from pathlib import Path
from typing import TextIO

import networkx as nx
from packaging import markers
from packaging.requirements import Requirement

_DOT_TEMPLATE = """\
// generated using `jtools.depgraph`
digraph {{
    rankdir=RL;
{}}}
"""

_REQUIRES_SCRIPT_TEMPLATE = """\
from importlib.metadata import requires
print(requires("{}"))
"""


def _eval_marker(r: Requirement) -> bool:
    try:
        return bool(not r.marker or r.marker.evaluate())
    except markers.UndefinedEnvironmentName:
        # If a marker isn't unsupported by `packaging` then we simply treat it as false.
        return False


def _requires(pkg: str, py_exe: Path) -> list[str]:
    result_repr = subprocess.run(
        [py_exe, "-c", _REQUIRES_SCRIPT_TEMPLATE.format(pkg)], capture_output=True
    ).stdout.decode()
    # TODO: find a better way to do this?
    return eval(result_repr) or []  # oh dear...


@lru_cache(1000)
def _requirements_and_edges(pkg: str, py_exe):
    reqs = [Requirement(req_str) for req_str in _requires(pkg, py_exe)]
    # TODO: duplicated code here:
    return (r.name for r in reqs if _eval_marker(r)), (
        (pkg, r.name) for r in reqs if _eval_marker(r)
    )


def _get_edges(pkgs, py_exe):
    if not pkgs:
        return []
    edges = set()
    next_pkgs = set()
    for pkg in pkgs:
        more_pkgs, more_edges = _requirements_and_edges(pkg, py_exe)
        edges.update(more_edges)
        next_pkgs.update(more_pkgs)
    edges.update(_get_edges(next_pkgs, py_exe))
    return edges


def mk_depgraph(pkgs: list[str], py_exe: Path | None = None) -> nx.DiGraph:
    """Make a directed graph for the dependency relationships of a set of packages.

    :param pkgs: The packages to analyze - only these are included in the graph. They
        must be installed in the environment pointed to by `py_exe`.
    :param py_exe: Location of the python executable to use to install/look for pkgs. By
        default will generate a temporary venv - this is safer but slower. If the
        packages are already installed, then pass `Path(sys.executable)` or equivalent.
    :return: Dependency relationship graph.
    """

    if py_exe is None:
        with tempfile.TemporaryDirectory() as tempdir_name:
            dep_venv = Path(tempdir_name)
            venv.create(dep_venv, with_pip=True)
            print("venv created at ", dep_venv)
            return mk_depgraph(pkgs, dep_venv / "Scripts" / "python.exe")

    p = subprocess.run(
        [str(py_exe), "-m", "pip", "install", *pkgs], capture_output=True
    )
    if p.returncode:
        raise RuntimeError(f"Installing {pkgs=} failed. Error:\n\n{p.stderr.decode()}")

    g = nx.DiGraph()
    g.add_edges_from(_get_edges(pkgs, py_exe))
    g = nx.transitive_closure(g)
    g.remove_nodes_from(node for node in list(g.nodes) if node not in pkgs)
    return nx.transitive_reduction(g)


def to_dot(g: nx.DiGraph, fp: TextIO | None = None) -> str:
    """Naively convert a directed graph into DOT format & optionally write to file.

    DOT language described here: https://graphviz.org/doc/info/lang.html

    :param g: Directed Graph to convert.
    :param fp: Optional file to write DOT to. Will set `rankdir=RL`.
    :return: Graph `g` in DOT format
    """
    # Why not use `pydot` or `pygraphviz`?
    #
    # - `pydot` is unsupported and will be dropped from `networkx`
    # - `pygraphviz` requires VS 2019 and Graphviz to be installed
    # - no real downside for this simple case, except lack of scalability
    # - by avoiding other packages we can intervene and sort the edges in the DOT format
    #   making the output deterministic and minimizing diffs as graphs are re-generated.
    str_nodes = "".join(f'    "{n}";\n' for n in sorted(g.nodes))
    str_edges = "".join(f'    "{a}" -> "{b}";\n' for a, b in sorted(g.edges))
    result = _DOT_TEMPLATE.format(str_nodes + str_edges)
    if fp:
        fp.write(result)
    return result


def main():
    pkgs = [
        "awscli",
        "pandas",
        "tensorflow",
        "numpy",
        "scipy",
        "matplotlib",
        "keras",
        "torch",
        "scrapy",
        "beautifulsoup4",  # module: bs4
        "typing-extensions",
        "pydot",
        "networkx",
        "black",
        "pylint",
        "mypy",
        "boto3",
        "urllib3",
        "setuptools",
        "requests",
        "botocore",
        "idna",
        "charset-normalizer",
        "wheel",
    ]

    g = mk_depgraph(pkgs)
    with open("./temp.gv", "w") as fp:
        print(to_dot(g, fp))


if __name__ == "__main__":
    main()
