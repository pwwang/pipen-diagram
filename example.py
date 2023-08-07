from pipen import Proc, Pipen, ProcGroup


class A(Proc):
    """Process A"""
    input = "a"


class B(Proc):
    """Process B"""
    requires = A
    input = "b"
    plugin_opts = {"diagram_hide": True}


class PG(ProcGroup):
    """Process Group"""
    @ProcGroup.add_proc
    def c(self):
        """Process C"""
        class C(Proc):
            input = "c"

        return C

    @ProcGroup.add_proc
    def c1(self):
        """Process C1"""
        class C1(Proc):
            requires = self.c
            input = "c1"
            plugin_opts = {"diagram_hide": True}

        return C1

    @ProcGroup.add_proc
    def d(self):
        """Process D"""
        class D(Proc):
            input = "d"
            requires = self.c1

        return D


pg = PG()
pg.c.requires = B


class E(Proc):
    """Process E"""
    input = "e1,e2"
    requires = pg.d, A


class F(Proc):
    """Process F"""
    input = "f"
    requires = E


# Pipen("MyPipeline").set_start(A).run()
# Dark theme
Pipen("MyPipeline", plugin_opts={"diagram_theme": "dark", "diagram_savedot": True}).set_start(A).run()
