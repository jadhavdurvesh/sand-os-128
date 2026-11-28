#!/usr/bin/env python3
"""vcc: a tiny compiler from a Python subset to Veylith assembly, with two back ends (raw loads/stores, Sigil capabilities).

Subset (parsed with Python's own `ast`): integer variables, integer constants, + - * // % & | ^ << >>, one comparison per
condition (unsigned), `if/else`, `while`, `for i in range(a[, b])`, global arrays of 128-bit elements declared by the caller
(`arrays={"name": (length, init_list)}`), subscript loads and stores. Everything is unsigned modulo 2^128. No calls, no spills:
at most 60 variables and a temp stack of 20, enough for the study programs and checked by the compiler.
It exists so the capability study can use compiler-generated code instead of hand-written assembly; it is not an optimiser."""
import ast

BASE = 0x10000
OPS = {ast.Add: "add", ast.Sub: "sub", ast.Mult: "mul", ast.FloorDiv: "udiv", ast.Mod: "urem", ast.BitAnd: "and", ast.BitOr: "or",
       ast.BitXor: "xor", ast.LShift: "shl", ast.RShift: "shr"}
VAR0, NVAR, TMP0, NTMP, ARR0 = 30, 60, 10, 20, 100


class Compiler:
    def __init__(self, cap, arrays):
        self.cap, self.arrays, self.out, self.vars, self.nt, self.nl = cap, arrays, [], {}, 0, 0
        self.layout, addr = {}, BASE
        for i, (name, (n, _)) in enumerate(arrays.items()):
            size = 16 * n
            exp = 4
            while (size + (1 << exp) - 1 >> exp) > 256:
                exp += 1
            lenm1 = (size + (1 << exp) - 1 >> exp) - 1
            addr = (addr + (1 << exp) - 1) & ~((1 << exp) - 1)
            self.layout[name] = (ARR0 + i, addr, exp, lenm1); addr += (lenm1 + 1) << exp
        self.end = addr

    def e(self, *ls):
        self.out.extend(ls)

    def label(self):
        self.nl += 1; return f"L{self.nl}"

    def var(self, name):
        if name not in self.vars:
            assert len(self.vars) < NVAR, "too many variables"
            self.vars[name] = VAR0 + len(self.vars)
        return f"v{self.vars[name]}"

    def tmp(self):
        assert self.nt < NTMP, "expression too deep"
        self.nt += 1; return f"v{TMP0 + self.nt - 1}"

    def free(self, n=1):
        self.nt -= n

    def expr(self, node):
        """Returns (register, is_temp)."""
        if isinstance(node, ast.Name):
            return self.var(node.id), False
        if isinstance(node, ast.Constant):
            t = self.tmp(); self.e(f"li {t}, {node.value}"); return t, True
        if isinstance(node, ast.BinOp):
            a, ta = self.expr(node.left)
            if isinstance(node.op, ast.Add) and isinstance(node.right, ast.Constant) and node.right.value < 1 << 80:
                d = a if ta else self.tmp()
                self.e(f"addi {d}, {a}, {node.right.value}"); return d, True
            b, tb = self.expr(node.right)
            d = a if ta else (b if tb else self.tmp())
            self.e(f"{OPS[type(node.op)]} {d}, {a}, {b}")
            if ta and tb:
                self.free()
            elif not ta and tb:
                pass
            elif not ta and not tb:
                pass
            return d, True
        if isinstance(node, ast.Subscript):
            return self.load(node), True
        raise NotImplementedError(ast.dump(node))

    def addr(self, node):
        """Offset register (index * 16)."""
        i, ti = self.expr(node.slice)
        d = i if ti else self.tmp()
        self.e(f"shli {d}, {i}, 4"); return d

    def load(self, node):
        reg = self.layout[node.value.id][0]; off = self.addr(node)
        if self.cap:
            self.e(f"clqx {off}, v{reg}, {off}")
        else:
            self.e(f"add {off}, v{reg}, {off}", f"lq {off}, [{off} + 0]")
        return off

    def store(self, node, value_reg):
        reg = self.layout[node.value.id][0]; off = self.addr(node)
        if self.cap:
            self.e(f"csqx {value_reg}, v{reg}, {off}")
        else:
            self.e(f"add {off}, v{reg}, {off}", f"sq [{off} + 0], {value_reg}")
        self.free()

    def branch_false(self, test, target):
        assert isinstance(test, ast.Compare) and len(test.ops) == 1
        a, ta = self.expr(test.left); b, tb = self.expr(test.comparators[0]); op = type(test.ops[0])
        ins = {ast.Lt: f"bgeu {a}, {b}", ast.LtE: f"bltu {b}, {a}", ast.Gt: f"bgeu {b}, {a}", ast.GtE: f"bltu {a}, {b}",
               ast.Eq: f"bne {a}, {b}", ast.NotEq: f"beq {a}, {b}"}[op]
        self.e(f"{ins}, {target}")
        self.free(int(ta) + int(tb))

    def stmt(self, s):
        if isinstance(s, ast.Assign):
            r, t = self.expr(s.value); tgt = s.targets[0]
            if isinstance(tgt, ast.Name):
                self.e(f"mv {self.var(tgt.id)}, {r}")
                if t: self.free()
            else:
                self.store(tgt, r)
                if t: self.free()
        elif isinstance(s, ast.AugAssign):
            self.stmt(ast.Assign(targets=[s.target], value=ast.BinOp(left=ast.Name(id=s.target.id, ctx=ast.Load()) if isinstance(s.target, ast.Name) else s.target, op=s.op, right=s.value)))
        elif isinstance(s, ast.While):
            top, end = self.label(), self.label()
            self.e(f"{top}:"); self.branch_false(s.test, end)
            for x in s.body: self.stmt(x)
            self.e(f"jmp {top}", f"{end}:")
        elif isinstance(s, ast.If):
            els, end = self.label(), self.label()
            self.branch_false(s.test, els)
            for x in s.body: self.stmt(x)
            self.e(f"jmp {end}", f"{els}:")
            for x in s.orelse: self.stmt(x)
            self.e(f"{end}:")
        elif isinstance(s, ast.For):
            args = s.iter.args; lo, hi = (ast.Constant(value=0), args[0]) if len(args) == 1 else args
            i = s.target.id
            self.stmt(ast.Assign(targets=[ast.Name(id=i, ctx=ast.Store())], value=lo))
            lim = f"__lim{self.nl}"; self.stmt(ast.Assign(targets=[ast.Name(id=lim, ctx=ast.Store())], value=hi))
            test = ast.Compare(left=ast.Name(id=i, ctx=ast.Load()), ops=[ast.Lt()], comparators=[ast.Name(id=lim, ctx=ast.Load())])
            step = ast.AugAssign(target=ast.Name(id=i, ctx=ast.Store()), op=ast.Add(), value=ast.Constant(value=1))
            self.stmt(ast.While(test=test, body=s.body + [step], orelse=[]))
        elif isinstance(s, ast.Pass):
            pass
        else:
            raise NotImplementedError(ast.dump(s))

    def compile(self, src):
        pro = ["li v1, 0x77", "csrw ckey, v1"]
        for name, (reg, addr, exp, lenm1) in self.layout.items():
            if self.cap:
                pro += [f"li v2, {addr}", f"li v3, {3 | exp << 8 | lenm1 << 16}", f"cmint v{reg}, v2, v3"]
            else:
                pro += [f"li v{reg}, {addr}"]
        self.out = []
        for s in ast.parse(src).body: self.stmt(s)
        return "\n".join(pro + self.out + ["halt"])


def compile_program(src, arrays, cap):
    c = Compiler(cap, arrays); return c.compile(src), c


def reference(src, arrays):
    """Run the source as ordinary Python (unbounded ints) and return (variables, arrays)."""
    env = {k: list(v[1]) + [0] * (v[0] - len(v[1])) for k, v in arrays.items()}
    exec(compile(src, "<vcc>", "exec"), {}, env)
    return env
