from pathlib import Path
from shutil import rmtree
from tempfile import gettempdir
import pytest
from pipen import Pipen, Proc
from pipen_diagram import PipenDiagram

TEST_TMPDIR = Path(gettempdir()) / "pipen_diagram_tests"
rmtree(TEST_TMPDIR, ignore_errors=True)
TEST_TMPDIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture
def pipen():
    index = Pipen.PIPELINE_COUNT + 1
    return Pipen(
        name=f"pipeline_{index}",
        desc="Diagram test",
        loglevel="debug",
        cache=False,
        plugins=[PipenDiagram],
        plugin_opts={"diagram_savedot": True},
        outdir=TEST_TMPDIR / f"pipen_{index}",
    )


@pytest.fixture
def pipen_dark():
    index = Pipen.PIPELINE_COUNT + 1
    return Pipen(
        name=f"pipeline_{index}",
        desc="Diagram test",
        loglevel="debug",
        cache=False,
        plugins=[PipenDiagram],
        plugin_opts={"diagram_savedot": False, "diagram_theme": "dark"},
        outdir=TEST_TMPDIR / f"pipen_{index}",
    )


@pytest.fixture
def pipen_custom_theme():
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
        },
        outdir=TEST_TMPDIR / f"pipen_{index}",
    )


class NormalProc(Proc):
    input = "a"
    output = "b:{{in.a}}"


class HiddenProc(NormalProc):
    plugin_opts = {"diagram_hide": True}


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


def test_hide_end_proc(pipen):
    p1 = Proc.from_proc(NormalProc, input_data=[1])
    p2 = Proc.from_proc(HiddenProc, requires=p1)
    with pytest.raises(ValueError, match="Cannot hide end process"):
        pipen.set_starts(p1).run()


def test_hide_multi_rel_proc(pipen):
    p1 = Proc.from_proc(NormalProc, input_data=[1])
    p2 = Proc.from_proc(NormalProc, input_data=[2])
    p3 = Proc.from_proc(HiddenProc, requires=[p1, p2])
    p4 = Proc.from_proc(NormalProc, requires=p3)
    p5 = Proc.from_proc(NormalProc, requires=p3)
    with pytest.raises(ValueError, match="Cannot hide process"):
        pipen.set_starts(p1, p2).run()


def test_dark_theme(pipen_dark):
    p1 = Proc.from_proc(NormalProc, input_data=[1])
    p2 = Proc.from_proc(NormalProc, requires=p1)
    p3 = Proc.from_proc(HiddenProc, requires=p2)
    p4 = Proc.from_proc(NormalProc, requires=p3)

    pipen_dark.set_starts(p1).run()
    svg = (pipen_dark.outdir / "diagram.svg").read_text()
    assert "#333333" in svg


def test_custom_theme(pipen_custom_theme):
    p1 = Proc.from_proc(NormalProc, input_data=[1])

    pipen_custom_theme.set_starts(p1).run()
    svg = (pipen_custom_theme.outdir / "diagram.svg").read_text()
    assert "#59b95f" in svg


def test_group():
    from pipen import Proc, Pipen, ProcGroup
    from pipen.exceptions import ProcInputKeyError

    class PG(ProcGroup):
        """Process Group"""
        @ProcGroup.add_proc
        def c(self):
            """Process C"""
            class C(Proc):
                ...

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

    pg = PG()
    with pytest.raises(ProcInputKeyError, match="No input provided"):
        Pipen(
            "MyPipeline",
            plugin_opts={"diagram_savedot": True},
            outdir=TEST_TMPDIR / "group1",
        ).set_start(pg.c).run()

    dot = (TEST_TMPDIR / "group1" / "diagram.dot").read_text()
    assert "digraph MyPipeline" in dot
    assert "subgraph cluster_PG" in dot

    with pytest.raises(ValueError, match="Theme x not found"):
        Pipen(
            "MyPipeline",
            plugin_opts={"diagram_theme": "x"},
            outdir=TEST_TMPDIR / "group2",
        ).set_start(pg.c).run()
