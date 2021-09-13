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
            "diagram_savedot": False,
            "diagram_theme": dict(
                start=dict(
                    style="filled",
                    color="#59b95f",  # green
                    penwidth=2,
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

    pipen.run(p1)
    dot = (pipen.outdir / "diagram.dot").read_text()
    assert "pipen: pipeline" in dot
    svg = (pipen.outdir / "diagram.svg").read_text()
    assert "pipen: pipeline" in svg


def test_hide_end_proc(pipen):
    p1 = Proc.from_proc(NormalProc, input_data=[1])
    p2 = Proc.from_proc(HiddenProc, requires=p1)
    with pytest.raises(ValueError, match="Cannot hide end process"):
        pipen.run(p1)


def test_hide_multi_rel_proc(pipen):
    p1 = Proc.from_proc(NormalProc, input_data=[1])
    p2 = Proc.from_proc(NormalProc, input_data=[2])
    p3 = Proc.from_proc(HiddenProc, requires=[p1, p2])
    p4 = Proc.from_proc(NormalProc, requires=p3)
    p5 = Proc.from_proc(NormalProc, requires=p3)
    with pytest.raises(ValueError, match="Cannot hide process"):
        pipen.run(p1, p2)


def test_dark_theme(pipen_dark):
    p1 = Proc.from_proc(NormalProc, input_data=[1])
    p2 = Proc.from_proc(NormalProc, requires=p1)
    p3 = Proc.from_proc(HiddenProc, requires=p2)
    p4 = Proc.from_proc(NormalProc, requires=p3)

    pipen_dark.run(p1)
    svg = (pipen_dark.outdir / "diagram.svg").read_text()
    assert "#59b95d" in svg


def test_custom_theme(pipen_custom_theme):
    p1 = Proc.from_proc(NormalProc, input_data=[1])

    pipen_custom_theme.run(p1)
    svg = (pipen_custom_theme.outdir / "diagram.svg").read_text()
    assert "#59b95f" in svg
