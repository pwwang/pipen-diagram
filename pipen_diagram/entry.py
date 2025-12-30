"""Creates the plugin"""
from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Tuple, Type
from pipen import plugin
from pipen.utils import get_logger

from .diagram import Diagram

logger = get_logger("diagram", "debug")

if TYPE_CHECKING:  # pragma: no cover
    from pipen import Pipen, Proc


def _get_mate(proc: Type[Proc]) -> Iterable[Tuple[Type[Proc], bool]]:
    """Find the mate starting with proc

    Args:
        proc: The process

    Yields:
        A tuple of the dependent process and whether there are hidden processes
        along the path.
    """
    if proc.nexts:
        for nproc in proc.nexts:
            if nproc.plugin_opts and nproc.plugin_opts.get(
                "diagram_hide", False
            ):
                for nnproc, _ in _get_mate(nproc):
                    yield (nnproc, True)
            else:
                yield (nproc, False)


class PipenDiagram:

    """pipen-diagram plugin: Draw pipeline diagrams for pipen"""

    __version__: str = None

    @plugin.impl
    def on_setup(pipen: Pipen) -> None:
        """Default configurations"""
        # pipeline level: name or detailed theme
        pipen.config.plugin_opts.diagram_theme = "default"
        # pipeline level: save dot file?
        pipen.config.plugin_opts.diagram_savedot = False
        # pipeline level: loglevel
        pipen.config.plugin_opts.diagram_loglevel = "info"
        # process level: hide certain processes in diagram
        pipen.config.plugin_opts.diagram_hide = False

    @plugin.impl
    async def on_start(pipen: Pipen) -> None:
        """Print some configuration items of the process"""
        loglevel = pipen.config.plugin_opts.get("diagram_loglevel", "info")
        logger.setLevel(loglevel.upper())

        logger.debug(
            "Building diagram and saving to `%s/diagram.svg`", pipen.outdir
        )
        diagram = Diagram(
            pipen.name,
            pipen.outdir / "diagram",
            savedot=pipen.config.plugin_opts.get("diagram_savedot", False),
        )

        if (
            pipen.config.plugin_opts
            and "diagram_theme" in pipen.config.plugin_opts
        ):
            diagram.set_theme(pipen.config.plugin_opts.diagram_theme)

        for node in pipen.procs:
            if node.plugin_opts and node.plugin_opts.get("diagram_hide", False):
                if not node.nexts:
                    raise ValueError(
                        "Cannot hide end process {node} from diagram."
                    )

                if len(node.requires) > 1 and len(node.nexts) > 1:
                    raise ValueError(
                        f"Cannot hide process {node} from diagram with "
                        "multiple required processes or "
                        "multiple dependent processes."
                    )

                continue  # pragma: no cover

            role = (
                "start"
                if node in pipen.starts
                else "end"
                if not node.nexts
                else None
            )
            diagram.add_node(node, group=node.__meta__["procgroup"], role=role)

            for dep_proc, has_hidden in _get_mate(node):
                if (
                    node.__meta__["procgroup"]
                    and dep_proc.__meta__["procgroup"]
                    == node.__meta__["procgroup"]
                ):
                    group = node.__meta__["procgroup"]
                else:
                    group = None
                diagram.add_edge(
                    node,
                    dep_proc,
                    group=group,
                    has_hidden=has_hidden,
                )

        diagram.build()
        await diagram.save()
