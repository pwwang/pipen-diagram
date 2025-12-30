"""Provides Diagram class that builds and saves the diagrams"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from tempfile import mkdtemp
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Mapping,
    Set,
    Tuple,
    Type,
    MutableMapping,
)

from panpath import CloudPath, PanPath
from graphviz import Digraph
from pipen.utils import desc_from_docstring

if TYPE_CHECKING:  # pragma: no cover
    from pipen import Proc, ProcGroup

THEMES = dict(
    default={
        # Basic themes for the graph
        "graph": {"labelloc": "t", "fontname": "Helvetica"},
        # Basic themes for nodes
        "node": {
            "shape": "box",
            "style": "rounded",
            "fontsize": "12",
            "fontname": "Helvetica",
        },
        # Basic themes for edges
        "edge": {"arrowsize": "0.8"},
        # Basic themes for edges with hidden processes
        "edge_hidden": {"style": "dashed"},
        # Basic themes for start nodes
        "start": {"shape": "diamond", "style": "solid"},
        # Basic themes for end nodes
        "end": {"shape": "rectangle", "style": "solid"},
        # Basic themes for process groups
        "procgroup": {
            # Themes for the group
            "style": "filled",
            "color": "#eeeeee",  # almost white
            "labeljust": "l",
            # Themes for the group node
            "node": {},
            # Themes for the group edge
            "edge": {"arrowsize": "0.8"},
            # Themes for the group edge with hidden processes
            "edge_hidden": {},
        },
    },
    fancy={
        # Basic themes for the graph
        "graph": {"labelloc": "t", "fontname": "Helvetica"},
        # Basic themes for nodes
        "node": {
            "shape": "box",
            "style": "rounded,filled",
            "fontsize": "12",
            "fillcolor": "#219ebc",
            "fontcolor": "#ffffff",
            "peripheries": "0",
            "fontname": "Helvetica",
        },
        # Basic themes for edges
        "edge": {"arrowsize": "0.8", "color": "#3d314a"},
        # Basic themes for edges with hidden processes
        "edge_hidden": {"style": "dashed"},
        # Basic themes for start nodes
        "start": {
            "shape": "diamond",
            "style": "solid,filled",
            "fillcolor": "#4c956c",
        },
        # Basic themes for end nodes
        "end": {
            "shape": "rectangle",
            "style": "solid,filled",
            "fillcolor": "#f26419",
        },
        # Basic themes for process groups
        "procgroup": {
            # Themes for the group
            "style": "filled",
            "color": "#eeeeee",  # almost white
            "labeljust": "l",
            # Themes for the group node
            "node": {},
            # Themes for the group edge
            "edge": {"arrowsize": "0.8"},
            # Themes for the group edge with hidden processes
            "edge_hidden": {},
        },
    },
    dark={
        # Basic themes for the graph
        "graph": {
            "labelloc": "t",
            "bgcolor": "#333333",
            "fontcolor": "#eeeeee",
            "fontname": "Helvetica",
        },
        # Basic themes for nodes
        "node": {
            "shape": "box",
            "style": "rounded",
            "color": "#eeeeee",
            "fontcolor": "#eeeeee",
            "fontsize": "12",
            "fontname": "Helvetica",
        },
        # Basic themes for edges
        "edge": {"color": "#eeeeee"},
        # Basic themes for edges with hidden processes
        "edge_hidden": {"style": "dashed"},
        # Basic themes for start nodes
        "start": {"shape": "diamond", "style": "solid"},
        # Basic themes for end nodes
        "end": {"shape": "rectangle", "style": "solid"},
        # Basic themes for process groups
        "procgroup": {
            # Themes for the group
            "style": "filled",
            "color": "#666666",
            "labeljust": "l",
            # Themes for the group node
            "node": {},
            # Themes for the group edge
            "edge": {},
            # Themes for the group edge with hidden processes
            "edge_hidden": {},
        },
    },
    fancy_dark={
        # Basic themes for the graph
        "graph": {
            "labelloc": "t",
            "fontname": "Helvetica",
            "bgcolor": "#333333",
            "fontcolor": "#eeeeee",
        },
        # Basic themes for nodes
        "node": {
            "shape": "box",
            "style": "rounded,filled",
            "fontsize": "12",
            "fillcolor": "#219ebc",
            "fontcolor": "#ffffff",
            "peripheries": "0",
            "fontname": "Helvetica",
        },
        # Basic themes for edges
        "edge": {"color": "#eeeeee"},
        # Basic themes for edges with hidden processes
        "edge_hidden": {"style": "dashed"},
        # Basic themes for start nodes
        "start": {
            "shape": "diamond",
            "style": "solid,filled",
            "fillcolor": "#4c956c",
        },
        # Basic themes for end nodes
        "end": {
            "shape": "rectangle",
            "style": "solid,filled",
            "fillcolor": "#f26419",
        },
        # Basic themes for process groups
        "procgroup": {
            # Themes for the group
            "style": "filled",
            "color": "#666666",
            "labeljust": "l",
            # Themes for the group node
            "node": {},
            # Themes for the group edge
            "edge": {},
            # Themes for the group edge with hidden processes
            "edge_hidden": {},
        },
    },
)


class Group:
    """A group of nodes and edges"""

    def __init__(self, name: str) -> None:
        """Constructor"""
        self.name = name
        self.nodes: Set[Type[Proc]] = set()
        self.edges: Set[Tuple[Type[Proc], Type[Proc], bool]] = set()

    def add_node(self, node: Type[Proc]) -> None:
        """Add a node to the group"""
        self.nodes.add(node)

    def add_edge(
        self,
        node1: Type[Proc],
        node2: Type[Proc],
        has_hidden: bool = False,
    ) -> None:
        """Add an edge to the group"""
        if not has_hidden:  # pragma: no cover
            try:
                self.edges.remove((node1, node2, True))
            except KeyError:
                pass
        self.edges.add((node1, node2, has_hidden))

    def build(self, diagram: Diagram) -> None:
        """Build the group in the graph"""
        pg_theme = deepcopy(diagram.theme.get("procgroup", {}))
        pg_theme_node = pg_theme.pop("node", {})
        pg_theme_edge = pg_theme.pop("edge", {})
        pg_theme_edge_hidden = diagram.theme.get("edge_hidden", {}).copy()
        pg_theme_edge_hidden.update(pg_theme.pop("edge_hidden", {}))
        with diagram.graph.subgraph(name=f"cluster_{self.name}") as sub:
            sub.attr(label=self.name, **pg_theme)
            sub.node_attr.update(**pg_theme_node)
            sub.edge_attr.update(**pg_theme_edge)

            for node in self.nodes:
                if node in diagram.starts:
                    sub.node(
                        node.name,
                        tooltip=(node.desc or desc_from_docstring(node, None) or ""),
                        **diagram.theme.get("start", {}),
                    )
                elif node in diagram.ends:
                    sub.node(
                        node.name,
                        tooltip=(node.desc or desc_from_docstring(node, None) or ""),
                        **diagram.theme.get("end", {}),
                    )
                else:
                    sub.node(
                        node.name,
                        tooltip=(node.desc or desc_from_docstring(node, None) or ""),
                    )

            for node1, node2, has_hidden in self.edges:
                sub.edge(
                    node1.name,
                    node2.name,
                    **(pg_theme_edge_hidden if has_hidden else {}),
                )


class Diagram:
    """Build and save diagrams"""

    def __init__(self, name: str, outprefix: Path, savedot: bool) -> None:
        """Constructor"""
        self.graph = Digraph(name.strip())
        # Add some distance between the label and the graph
        self.graph.attr(label=f"{name.strip()}\n ")
        self.outprefix = outprefix
        self.savedot = savedot
        self.theme = THEMES["default"]
        self.nodes: Set[Type[Proc]] = set()
        self.starts: Set[Type[Proc]] = set()
        self.ends: Set[Type[Proc]] = set()
        self.groups: MutableMapping[str, Group] = {}
        self.edges: Set[Tuple[Type[Proc], Type[Proc], bool]] = set()

    def set_theme(self, theme: str | Mapping[str, Any]) -> None:
        """Set the theme

        Args:
            theme: The theme, could be the name of a theme defined in
                `pipen_diagram.diagram.THEMES`, or a dict of detailed theme
                items.
            base: The base theme to be based on, when you pass a custom theme
        """
        if isinstance(theme, dict):
            self.theme = theme
        else:
            try:
                self.theme = THEMES[theme]  # type: ignore
            except KeyError:
                raise ValueError(f"Theme {theme} not found") from None

    def add_node(
        self,
        node: Type[Proc],
        group: ProcGroup | None = None,
        role: str | None = None,
    ) -> None:
        """Add a node to the diagram

        Args:
            node: The process
            group: The group name
            role: Is it a start proc, an end proc or None (a normal proc).
        """
        if role == "start":
            self.starts.add(node)

        if role == "end":
            self.ends.add(node)

        if group:
            self.groups.setdefault(group.name, Group(group.name)).add_node(node)
        else:
            self.nodes.add(node)

    def add_edge(
        self,
        node1: Type[Proc],
        node2: Type[Proc],
        group: ProcGroup | None = None,
        has_hidden: bool = False,
    ) -> None:
        """Add a edge to the chart

        Args:
            node1: The first process node.
            node2: The second process node.
            group: The group name
            has_hidden: Whether there are processes hidden along the edge
        """
        if group:
            self.groups.setdefault(group.name, Group(group.name)).add_edge(
                node1, node2, has_hidden
            )
        else:
            if not has_hidden:
                try:
                    self.edges.remove((node1, node2, True))
                except KeyError:
                    pass

            self.edges.add((node1, node2, has_hidden))

    def build(self) -> None:
        """Assemble the graph for compiling"""
        self.graph.graph_attr.update(self.theme.get("graph", {}))
        self.graph.attr("node", **self.theme.get("node", {}))
        self.graph.attr("edge", **self.theme.get("edge", {}))
        for group in self.groups.values():
            group.build(self)

        for node in self.nodes:
            if node in self.starts:
                self.graph.node(
                    node.name,
                    tooltip=(node.desc or desc_from_docstring(node, None) or ""),
                    **self.theme.get("start", {}),
                )
            elif node in self.ends:
                self.graph.node(
                    node.name,
                    tooltip=(node.desc or desc_from_docstring(node, None) or ""),
                    **self.theme.get("end", {}),
                )
            else:
                self.graph.node(
                    node.name,
                    tooltip=(node.desc or desc_from_docstring(node, None) or ""),
                )

        # edges
        for node1, node2, has_hidden in self.edges:
            self.graph.edge(
                node1.name,
                node2.name,
                **(self.theme.get("edge_hidden", {}) if has_hidden else {}),
            )

    async def save(self) -> None:
        """Save the graph"""
        outprefix = self.outprefix
        # in case pipeline outdir is not created
        await outprefix.parent.a_mkdir(parents=True, exist_ok=True)

        if isinstance(outprefix, CloudPath):
            dig = sha256(str(outprefix).encode()).hexdigest()[:8]
            outprefix = PanPath(mkdtemp(suffix=dig)) / outprefix.name

        if self.savedot:
            dotfile = outprefix.with_name(f"{outprefix.name}.dot")
            # self.graph.save(dotfile)
            async with dotfile.a_open("w") as f:
                for uline in self.graph:
                    await f.write(uline)

            if outprefix != self.outprefix:  # cloud
                await self.outprefix.with_name(f"{outprefix.name}.dot").a_write_text(
                    await dotfile.a_read_text()
                )

        rendered_file = self.graph.render(outprefix, format="svg", cleanup=True)
        if outprefix != self.outprefix:
            await self.outprefix.with_name(f"{self.outprefix.name}.svg").a_write_text(
                await PanPath(rendered_file).a_read_text()
            )
