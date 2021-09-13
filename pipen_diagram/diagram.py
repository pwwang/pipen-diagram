"""Provides Diagram class that builds and saves the diagrams"""

from copy import deepcopy
from typing import TYPE_CHECKING, Any, Mapping, Set, Tuple, Type, Union
from graphviz import Digraph
from diot import Diot

if TYPE_CHECKING:  # pragma: no cover
    from pathlib import Path
    from pipen import Proc

THEMES = Diot(
    default=dict(
        # The base style to be inherited
        base=dict(
            shape="box",
            style="rounded,filled",
            fillcolor="#ffffff",
            color="#000000",
            fontcolor="#000000",
        ),
        # style for start processes
        start=dict(
            style="filled",
            color="#259229",  # green
        ),
        # style for end processes
        end=dict(
            style="filled",
            color="#d63125",  # red
        ),
        # procset=dict(
        #     style="filled",
        #     color="#eeeeee",  # almost white
        # ),
        # style for edges
        edge=dict(),
        # style for edges with hidden processes along the path
        edge_hidden=dict(style="dashed"),
    ),
    dark=dict(
        base=dict(
            shape="box",
            style="rounded,filled",
            fillcolor="#555555",
            color="#ffffff",
            fontcolor="#ffffff",
        ),
        start=dict(
            style="filled",
            color="#59b95d",  # green
            penwidth=2,
        ),
        end=dict(
            style="filled",
            color="#ea7d75",  # red
            penwidth=2,
        ),
        # procset=dict(
        #     style="filled",
        #     color="#eeeeee",  # almost white
        # ),
        edge=dict(),
        edge_hidden=dict(style="dashed"),
    ),
)


class Diagram:
    """Build and save diagrams"""

    def __init__(self, desc: str, outprefix: "Path", savedot: bool) -> None:
        """Constructor"""
        self.graph = Digraph(desc, format="svg")
        self.outprefix = outprefix
        self.savedot = savedot
        self.theme = THEMES.default
        self.nodes: Set[Type["Proc"]] = set()
        self.starts: Set[Type["Proc"]] = set()
        self.ends: Set[Type["Proc"]] = set()
        self.links: Set[Tuple[Type["Proc"], Type["Proc"], bool]] = set()

    def set_theme(
        self,
        theme: Union[str, Mapping[str, Any]],
        base: str = "default",
    ) -> None:
        """Set the theme

        Args:
            theme: The theme, could be the name of a theme defined in
                `pipen_diagram.diagram.THEMES`, or a dict of detailed theme
                items.
            base: The base theme to be based on, when you pass a custom theme
        """
        if isinstance(theme, dict):
            self.theme = deepcopy(THEMES[base])
            for key, val in self.theme.items():
                val.update(theme.get(key, {}))
        elif not theme:  # pragma: no cover
            self.theme = THEMES[base]
        else:
            self.theme = THEMES[theme]

    def add_node(self, node: Type["Proc"], role: str = None) -> None:
        """Add a node to the diagram

        Args:
            node: The process
            role: Is it a start proc, an end proc or None (a normal proc).
        """
        if role == "start":
            self.starts.add(node)

        if role == "end":
            self.ends.add(node)

        self.nodes.add(node)

    def add_link(
        self,
        node1: Type["Proc"],
        node2: Type["Proc"],
        has_hidden: bool = False,
    ) -> None:
        """Add a link to the chart

        Args:
            node1: The first process node.
            node2: The second process node.
            has_hidden: Whether there are processes hidden along the link
        """
        if not has_hidden:
            try:
                self.links.remove((node1, node2, True))
            except KeyError:
                pass

        self.links.add((node1, node2, has_hidden))

    def build(self) -> None:
        """Assemble the graph for compiling"""
        # nodes
        graph = self.graph
        for node in self.nodes:
            # copy the theme
            theme = deepcopy(self.theme["base"])
            if node in self.starts:
                theme.update(self.theme["start"])
            if node in self.ends:
                theme.update(self.theme["end"])
            if node.desc != "Undescribed":
                theme["tooltip"] = node.desc
            graph.node(node.name, **{k: str(v) for k, v in theme.items()})

        # edges
        for node1, node2, has_hidden in self.links:
            self.graph.edge(
                node1.name,
                node2.name,
                **{
                    k: str(v)
                    for k, v in self.theme[
                        "edge_hidden" if has_hidden else "edge"
                    ].items()
                },
            )

    def save(self) -> None:
        """Save the graph"""
        if self.savedot:
            self.graph.save(f"{self.outprefix}.dot")
        self.graph.render(self.outprefix, cleanup=True)
