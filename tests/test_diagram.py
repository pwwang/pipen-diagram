import pytest
from unittest.mock import MagicMock
from panpath import CloudPath, PanPath
from pipen import Pipen, Proc, ProcGroup
from pipen_diagram import PipenDiagram


@pytest.fixture
def pipen(tmp_path):
    index = Pipen.PIPELINE_COUNT + 1
    return Pipen(
        name=f"pipeline_{index}",
        desc="Diagram test",
        loglevel="debug",
        cache=False,
        plugins=[PipenDiagram],
        plugin_opts={"diagram_savedot": True, "diagram_loglevel": "debug"},
        outdir=tmp_path / f"pipen_{index}",
    )


@pytest.fixture
def pipen_dark(tmp_path):
    index = Pipen.PIPELINE_COUNT + 1
    return Pipen(
        name=f"pipeline_{index}",
        desc="Diagram test",
        loglevel="debug",
        cache=False,
        plugins=[PipenDiagram],
        plugin_opts={
            "diagram_savedot": False,
            "diagram_theme": "dark",
            "diagram_loglevel": "debug",
        },
        outdir=tmp_path / f"pipen_dark_{index}",
    )


@pytest.fixture
def pipen_custom_theme(tmp_path):
    index = Pipen.PIPELINE_COUNT + 1
    return Pipen(
        name=f"pipeline_{index}",
        desc="Diagram test",
        loglevel="debug",
        cache=False,
        plugins=[PipenDiagram],
        plugin_opts={
            "diagram_savedot": True,
            "diagram_theme": dict(
                start=dict(
                    style="filled",
                    color="#59b95f",  # green
                    penwidth="2",
                )
            ),
            "diagram_loglevel": "debug",
        },
        outdir=tmp_path / f"pipen_{index}",
    )


class NormalProc(Proc):
    input = "a"
    output = "b:{{in.a}}"


class HiddenProc(NormalProc):
    plugin_opts = {"diagram_hide": True}


@pytest.mark.forked
def test_diagram(pipen, caplog):
    p1 = Proc.from_proc(NormalProc, input_data=[1])
    p2 = Proc.from_proc(NormalProc, requires=p1)
    p3 = Proc.from_proc(HiddenProc, requires=p2)
    p4 = Proc.from_proc(NormalProc, requires=p3)

    pipen.set_starts(p1).run()
    dot = (pipen.outdir / "diagram.dot").read_text()
    assert "digraph pipeline" in dot
    svg = (pipen.outdir / "diagram.svg").read_text()
    assert "<title>pipeline" in svg


@pytest.mark.forked
def test_hide_end_proc(pipen):
    p1 = Proc.from_proc(NormalProc, input_data=[1])
    p2 = Proc.from_proc(HiddenProc, requires=p1)
    # ValueError: Cannot hide end process {node} from diagram.
    #   The above exception was the direct cause of the following exception:
    # simplug.ResultError: Error while calling hook implementation, plugin=diagram; spec=[async]on_start
    with pytest.raises(Exception) as excinfo:
        pipen.set_starts(p1).run()
    # The plugin system may wrap the original ValueError; ensure the original message is present.
    err = excinfo.value
    cause = getattr(err, "__cause__", None)
    assert "Cannot hide end process" in str(err) or (
        cause and "Cannot hide end process" in str(cause)
    )


@pytest.mark.forked
def test_hide_multi_rel_proc(pipen):
    p1 = Proc.from_proc(NormalProc, input_data=[1])
    p2 = Proc.from_proc(NormalProc, input_data=[2])
    p3 = Proc.from_proc(HiddenProc, requires=[p1, p2])
    p4 = Proc.from_proc(NormalProc, requires=p3)
    p5 = Proc.from_proc(NormalProc, requires=p3)
    with pytest.raises(Exception) as excinfo:
        pipen.set_starts(p1, p2).run()

    err = excinfo.value
    cause = getattr(err, "__cause__", None)
    assert "Cannot hide process" in str(err) or (
        cause and "Cannot hide process" in str(cause)
    )


@pytest.mark.forked
def test_dark_theme(pipen_dark):
    p1 = Proc.from_proc(NormalProc, input_data=[1])
    p2 = Proc.from_proc(NormalProc, requires=p1)
    p3 = Proc.from_proc(HiddenProc, requires=p2)
    p4 = Proc.from_proc(NormalProc, requires=p3)

    pipen_dark.set_starts(p1).run()
    svg = (pipen_dark.outdir / "diagram.svg").read_text()
    assert "#333333" in svg


@pytest.mark.forked
def test_custom_theme(pipen_custom_theme):
    p1 = Proc.from_proc(NormalProc, input_data=[1])

    pipen_custom_theme.set_starts(p1).run()
    svg = (pipen_custom_theme.outdir / "diagram.svg").read_text()
    assert "#59b95f" in svg


@pytest.mark.forked
def test_cloud_outdir(pipen_custom_theme, tmp_path):
    p1 = Proc.from_proc(NormalProc, input_data=[1])
    p2 = Proc.from_proc(NormalProc, requires=p1)
    p3 = Proc.from_proc(HiddenProc, requires=p2)
    p4 = Proc.from_proc(NormalProc, requires=p3)
    pipen_custom_theme.outdir = MagicMock(spec=CloudPath)
    outdir = PanPath(tmp_path) / "outdir"
    outdir.mkdir()

    def truediv(self, x):
        subpath = MagicMock(spec=CloudPath)
        subpath.joinpath = lambda x: outdir / x
        subpath.with_name = lambda x: outdir.parent / x
        subpath.name = "xyz"
        subpath.parent = outdir
        return subpath

    pipen_custom_theme.outdir.__truediv__ = truediv
    pipen_custom_theme.outdir.__str__ = lambda x: str(outdir)

    pipen_custom_theme.set_starts(p1).run()
    assert tmp_path.joinpath("xyz.svg").exists()


class PG(ProcGroup):
    """Process Group"""

    @ProcGroup.add_proc
    def c(self):
        """Process C"""

        class C(Proc): ...

        return C

    @ProcGroup.add_proc
    def c1(self):
        """Process C1"""

        class C1(Proc):
            requires = self.c
            plugin_opts = {"diagram_hide": True}

        return C1

    @ProcGroup.add_proc
    def c2(self):
        """Process C2"""

        class C2(Proc):
            requires = self.c1

        return C2

    @ProcGroup.add_proc
    def d(self):
        """Process D"""

        class D(Proc):
            requires = self.c2

        return D


@pytest.mark.forked
def test_group(tmp_path):
    from pipen.exceptions import ProcInputKeyError

    tmp_path = PanPath(tmp_path)

    pg = PG()
    with pytest.raises(ProcInputKeyError, match="No input provided"):
        Pipen(
            "MyPipeline",
            plugin_opts={"diagram_savedot": True, "diagram_loglevel": "debug"},
            outdir=tmp_path / "group1",
        ).set_start(pg.c).run()

    dot = (tmp_path / "group1" / "diagram.dot").read_text()
    assert "digraph MyPipeline" in dot
    assert "subgraph cluster_PG" in dot


@pytest.mark.forked
def test_theme_not_found(tmp_path):
    pg = PG()

    # with pytest.raises(ValueError, match="Theme x not found"):
    with pytest.raises(Exception) as excinfo:
        Pipen(
            "MyPipeline",
            plugin_opts={"diagram_theme": "x", "diagram_loglevel": "debug"},
            outdir=tmp_path / "group2",
        ).set_start(pg.c).run()

    err = excinfo.value
    cause = getattr(err, "__cause__", None)
    assert "Theme x not found" in str(err) or (
        cause and "Theme x not found" in str(cause)
    )
