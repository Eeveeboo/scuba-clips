"""Typed facade over solid2 for the model sources.

ty is strict: it does not infer a return type from a function body, and it needs
an annotation for every parameter. solid2 loses its types twice.

1. The convenience layer replaces `cube`, `translate`, `rotate`, `scale`,
   `mirror`, `resize` and `square` with `def name(*args, **kwargs)`, so ty sees
   the result as `Unknown`.
2. A node object comes from `ObjectBase.__call__(self, *args)`, whose return is
   unannotated, so calling a builder result is `Unknown` too.

The wrappers below carry the argument types and the return type that this
project uses. Each wrapper forwards to the solid2 builder. Import the builders
from `lib.scad`, not from `solid2`.

A node also takes `+` for union and `-` for difference: `a + b` is
`union()([a, b])` and `a - b` is `difference()([a, b])`. `a += b` and `a -= b`
work too, because Python rebinds the name through `__add__`/`__sub__`.

A node also takes the transforms as methods, so a chain reads in the order that
the part moves:

    a.rotate(45, 0, 0).translate(0, 0, 5).mirror(1, 0, 0)

A method takes the vector as one number for each axis, `a.translate(x, y, z)`,
or as one sequence, `a.translate(v)`. A lone number in `rotate` is a turn about
the z axis, as solid2 reads it: `a.rotate(45)`. The module function keeps its own
argument: `translate(v)`, `rotate(a)`, `mirror(v)`.

The builders return `_Node`, a thin wrapper. solid2's own `+`/`-` flatten a
nested operand of the same type: `(a - b) - c` becomes one `difference(a,b,c)`
instead of a nested pair. That changes the CSG tree, the manifold tessellation
and the non-manifold edge count, and `uv run cli check-baseline` rejects it. `_Node`
keeps the operands nested, so the operators build exactly the tree that
`union()([a, b])` and `difference()([a, b])` build.

solid2 also writes `h: float = None` for an optional parameter. ty reads that as
`float`, not `float | None`, so a forwarded `float | None` fails the check. The
wrappers keep the honest `float | None` and call the builder through a
`Callable[..., ScadNode]` alias, which skips the argument check at that one
internal call.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Protocol, TypeAlias, cast

import solid2 as _solid2

from lib.config import CONFIG


class ScadNode(Protocol):
    """A solid2 node: a builder result that takes children and stays one node."""

    def __call__(self, *children: ScadChild) -> ScadNode: ...

    def __add__(self, other: ScadChild, /) -> ScadNode:
        """`a + b` builds the union of `a` and `b`. `a += b` also works."""
        ...

    def __sub__(self, other: ScadChild, /) -> ScadNode:
        """`a - b` builds the difference: `a` minus `b`. `a -= b` also works."""
        ...

    def translate(
        self,
        x: float | Sequence[float],
        y: float | None = None,
        z: float | None = None,
    ) -> ScadNode:
        """`a.translate(x, y, z)` moves the node by that vector. `a.translate(v)`
        takes the vector as one sequence."""
        ...

    def rotate(
        self,
        x: float | Sequence[float],
        y: float | None = None,
        z: float | None = None,
    ) -> ScadNode:
        """`a.rotate(x, y, z)` turns the node by that many degrees about each
        axis. `a.rotate(45)` turns the node about the z axis."""
        ...

    def mirror(
        self,
        x: float | Sequence[float],
        y: float | None = None,
        z: float | None = None,
    ) -> ScadNode:
        """`a.mirror(x, y, z)` mirrors the node through the plane that has that
        normal vector. `a.mirror(v)` takes the vector as one sequence."""
        ...


# A child argument is one node, or a sequence of nodes and nested sequences.
ScadChild: TypeAlias = "ScadNode | Sequence[ScadChild]"

# What a builder returns: one node. It is deliberately NOT the recursive child
# type. solid2's `OpenSCADObjectPlus` is `Object | Sequence[Object]`, but a
# sequence has no `__add__`, so `scene += part` fails when a builder return is
# annotated with the union. Use `ScadChild` for a parameter that takes children.
OpenSCADObjectPlus: TypeAlias = ScadNode


class _Node:
    """A solid2 object whose `+` and `-` reproduce the original CSG tree.

    solid2's `__add__` and `__sub__` call `_union_op`/`_difference_op`, which
    pull the children of *any* same-type operand into the new node. That pulls
    in a builder result such as `c_ring_rounded_two_openings(...)`, which the
    original `union()([...])` call kept as one child, and the mesh changes.

    _Node flattens only a union node it built itself in an earlier step of the
    same chain. So `a + b + c` becomes one `union(a, b, c)`, exactly the tree
    that the original flat `union()([a, b, c])` call built. A difference never
    flattens: `a - b` is always `difference(a, b)`.

    One limit: the chain mark travels with the value, so a helper that builds
    its result with `+` and is then the left operand of `+` in its caller is
    flattened. Where the original kept that helper's union as one child, the
    helper returns a flat `union()([...])` instead. `c_ring_rounded_two_openings`,
    `_hose_clips_and_blocks`, and `fit_test_clip` do this.
    """

    __slots__ = ("_inner", "_op")

    def __init__(self, inner: Any, op: str | None = None) -> None:
        self._inner = inner
        self._op = op

    def __call__(self, *children: ScadChild) -> ScadNode:
        return _Node(self._inner(*[_unwrap(child) for child in children]))

    def translate(
        self,
        x: float | Sequence[float],
        y: float | None = None,
        z: float | None = None,
    ) -> ScadNode:
        return _Node(_translate(_vector(x, y, z))(self._inner))

    def rotate(
        self,
        x: float | Sequence[float],
        y: float | None = None,
        z: float | None = None,
    ) -> ScadNode:
        return _Node(_rotate(_vector(x, y, z))(self._inner))

    def mirror(
        self,
        x: float | Sequence[float],
        y: float | None = None,
        z: float | None = None,
    ) -> ScadNode:
        return _Node(_mirror(_vector(x, y, z))(self._inner))

    def __add__(self, other: ScadChild, /) -> ScadNode:
        return _Node(self._add_union(other), "union")

    def __sub__(self, other: ScadChild, /) -> ScadNode:
        return _Node(_solid2.difference()(self._inner, _unwrap(other)), "difference")

    def _add_union(self, other: ScadChild) -> Any:
        node = _solid2.union()
        if self._op == "union":
            for child in self._inner._children:
                node.add(child)
        else:
            node.add(self._inner)
        node.add(_unwrap(other))
        return node

    def _render(self) -> str:
        """Render the wrapped object, so solid2's `scad_render_to_file` works."""
        return self._inner._render()


def _vector(
    x: float | Sequence[float],
    y: float | None,
    z: float | None,
) -> float | Sequence[float | None]:
    """Return the one argument that a solid2 transform takes.

    The caller gives the vector as `x`, or as one number for each axis. A lone
    number stays alone, because solid2 reads `rotate(45)` as a turn about the z
    axis.
    """
    if isinstance(x, Sequence) or (y is None and z is None):
        return x
    return (x, y, z)


def _unwrap(node: Any) -> Any:
    """Return the solid2 object inside a `_Node`, and inside a nested sequence."""
    if isinstance(node, _Node):
        return node._inner
    if isinstance(node, (list, tuple)):
        return [_unwrap(item) for item in node]
    return node


# The solid2 primitives declare optional parameters as `T = None`. ty reads that
# as `T`, so the wrapper's `T | None` argument fails its check. Call through this
# alias instead; the wrapper's own signature is still the typed one.
_Primitive: TypeAlias = Callable[..., ScadNode]

_translate = cast(_Primitive, _solid2.translate)
_rotate = cast(_Primitive, _solid2.rotate)
_mirror = cast(_Primitive, _solid2.mirror)
_sphere = cast(_Primitive, _solid2.sphere)
_cylinder = cast(_Primitive, _solid2.cylinder)
_polygon = cast(_Primitive, _solid2.polygon)
_linear_extrude = cast(_Primitive, _solid2.linear_extrude)
_rotate_extrude = cast(_Primitive, _solid2.rotate_extrude)
_text = cast(_Primitive, _solid2.text)


def cube(
    size: float | Sequence[float] | None = None,
    center: bool | None = None,
) -> ScadNode:
    return _Node(_solid2.cube(size=size, center=center))


def square(
    size: float | Sequence[float] | None = None,
    center: bool | None = None,
) -> ScadNode:
    return _Node(_solid2.square(size=size, center=center))


def sphere(
    r: float | None = None,
    d: float | None = None,
    _fn: int | None = CONFIG.library.tessellation_resolution,
) -> ScadNode:
    return _Node(_sphere(r=r, d=d, _fn=_fn))


def cylinder(
    h: float | None = None,
    r: float | None = None,
    r1: float | None = None,
    r2: float | None = None,
    d: float | None = None,
    d1: float | None = None,
    d2: float | None = None,
    center: bool | None = None,
    _fn: int | None = CONFIG.library.tessellation_resolution,
) -> ScadNode:
    return _Node(
        _cylinder(h=h, r=r, r1=r1, r2=r2, d=d, d1=d1, d2=d2, center=center, _fn=_fn)
    )


Point2: TypeAlias = tuple[float, float]
Point3: TypeAlias = tuple[float, float, float]


def polygon(
    points: Sequence[Point2 | Point3],
    paths: Sequence[int] | Sequence[Sequence[int]] | None = None,
    convexity: int | None = None,
) -> ScadNode:
    return _Node(_polygon(points=points, paths=paths, convexity=convexity))


def union() -> ScadNode:
    return _Node(_solid2.union())


def difference() -> ScadNode:
    return _Node(_solid2.difference())


def hull() -> ScadNode:
    return _Node(_solid2.hull())


def translate(v: Sequence[float] | None = None) -> ScadNode:
    return _Node(_translate(v))


def rotate(a: float | Sequence[float] | None = None) -> ScadNode:
    return _Node(_rotate(a))


def mirror(v: Point3) -> ScadNode:
    return _Node(_mirror(v))


def linear_extrude(
    height: float | None = None,
    center: bool | None = None,
    convexity: int | None = None,
    twist: float | None = None,
    slices: int | None = None,
    scale: float | None = None,
) -> ScadNode:
    return _Node(
        _linear_extrude(
            height=height,
            center=center,
            convexity=convexity,
            twist=twist,
            slices=slices,
            scale=scale,
        )
    )


def rotate_extrude(
    angle: float | None = 360,
    convexity: int | None = None,
    _fn: int | None = CONFIG.library.tessellation_resolution,
) -> ScadNode:
    return _Node(_rotate_extrude(angle=angle, convexity=convexity, _fn=_fn))


def text(
    text: str,
    size: float | None = None,
    font: str | None = None,
    halign: str | None = None,
    valign: str | None = None,
    spacing: float | None = None,
    direction: str | None = None,
    language: str | None = None,
    script: str | None = None,
    _fn: int | None = CONFIG.library.tessellation_resolution,
) -> ScadNode:
    return _Node(
        _text(
            text=text,
            size=size,
            font=font,
            halign=halign,
            valign=valign,
            spacing=spacing,
            direction=direction,
            language=language,
            script=script,
            _fn=_fn,
        )
    )


def scad_render(root: OpenSCADObjectPlus) -> str:
    return _solid2.scad_render(_unwrap(root))
