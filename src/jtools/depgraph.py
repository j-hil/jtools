r"""Tools to generate dependency graphs for python packages.

Use `write_dot_depgraph` to create a DOT file to render/view,                 AAA
or use `mk_depgraph` to return the equivalent `networkx.DepGraph`            /   \
object for further manipulation.                                           BBB    CCC
                                                                            |    /   \
The information displayed is intentionally minimal, as the primary         DDD  EEE  FFF
use-case is visualizing the data; only inputted packages are displayed
as nodes and the information is transitively reduced.
"""

from __future__ import annotations

import ast
import logging
import subprocess
import tempfile
import venv
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import networkx as nx
from packaging import markers
from packaging.requirements import Requirement

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

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
    """Runs `importlib.metadata.requires` but in environment specified by `py_exe`."""
    result_repr = subprocess.run(
        [py_exe, "-c", _REQUIRES_SCRIPT_TEMPLATE.format(pkg)],
        capture_output=True,
        check=True,
    ).stdout.decode()
    return ast.literal_eval(result_repr) or []


@lru_cache(1000)
def _requirements_and_edges(
    pkg: str, py_exe: Path
) -> tuple[list[str], list[tuple[str, str]]]:
    reqs = [Requirement(req_str) for req_str in _requires(pkg, py_exe)]
    req_strs = [r.name for r in reqs if _eval_marker(r)]
    return req_strs, [(pkg, r) for r in req_strs]


def _get_edges(pkgs: Iterable[str], py_exe: Path) -> set[tuple[str, str]]:
    if not pkgs:
        return set()

    edges = set()
    next_pkgs = set()
    for pkg in pkgs:
        more_pkgs, more_edges = _requirements_and_edges(pkg, py_exe)
        logger.debug("Package %s upstream dependencies acquired as: %s", pkg, more_pkgs)

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
            logger.info("No python executable specified, venv created at %s", dep_venv)
            return mk_depgraph(pkgs, dep_venv / "Scripts" / "python.exe")

    logger.info("Installing packages with %s", py_exe)
    p = subprocess.run(
        [str(py_exe), "-m", "pip", "install", *pkgs], capture_output=True, check=False
    )
    if p.returncode:
        raise RuntimeError(f"Installing {pkgs=} failed. Error:\n\n{p.stderr.decode()}")

    logger.info("Packages installed. Creating network graph.")
    g = nx.DiGraph()
    g.add_edges_from(_get_edges(pkgs, py_exe))

    logger.info("Reducing network graph.")
    g = nx.transitive_closure(g)
    g.remove_nodes_from(node for node in list(g.nodes) if node not in pkgs)
    return nx.transitive_reduction(g)


def to_dot(g: nx.DiGraph) -> str:
    """Naively convert a directed graph into DOT format & optionally write to file.

    DOT language described here: https://graphviz.org/doc/info/lang.html. Note Will set
    `rankdir=RL` since it makes nicer graphs when rendered.

    :param g: Directed Graph to convert.
    :return: Graph `g` in DOT format as a string
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
    return _DOT_TEMPLATE.format(str_nodes + str_edges)


def write_dot_depgraph(pkgs: list[str], path: Path) -> None:
    g = mk_depgraph(pkgs)
    path.write_text(to_dot(g))
    logger.info("Result written to file %s", path)


def _main() -> None:
    # test example
    pkgs = (
        "awscli pandas tensorflow numpy scipy matplotlib keras torch scrapy "
        "beautifulsoup4 typing-extensions pydot networkx black pylint mypy boto3 "
        "urllib3 setuptools requests botocore idna charset-normalizer wheel"
    ).split()
    write_dot_depgraph(pkgs, Path.cwd() / "temp.gv")


if __name__ == "__main__":
    _main()
