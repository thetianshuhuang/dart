"""Reflectance field functions."""

from functools import partial
from jaxtyping import Float32, Integer, Array
from beartype.typing import Union, Optional

from jax import numpy as jnp
import jax
import haiku as hk

from .spatial import interpolate, spherical_harmonics

from jax import custom_jvp


class GroundTruth:
    """Ground truth reflectance map.

    Parameters
    ----------
    grid: (reflectance, transmittance) grid; is trilinearly interpolated.
    lower: Lower corner of the grid.
    resolution: Resolution in units per grid cell. Can have the same resolution
        for each axis or different resolutions.
    """

    def __init__(
        self, grid: Float32[Array, "nx ny nz 2"], lower: Float32[Array, "3"],
        resolution: Union[Float32[Array, "3"], Float32[Array, ""]]
    ) -> None:
        self.lower = lower
        self.resolution = resolution
        self.grid = grid

    def __call__(
        self, x: Float32[Array, "3"], dx: Optional[Float32[Array, "3"]] = None
    ) -> Float32[Array, "2"]:
        """Index into reflectance map."""
        index = (x - self.lower) * self.resolution
        valid = jnp.all(
            (0 <= index) & (index <= jnp.array(self.grid.shape[:-1]) - 1))
        return jnp.where(valid, interpolate(index, self.grid), jnp.zeros((2,)))


class SimpleGrid(hk.Module):
    """Simple reflectance grid.

    Parameters
    ----------
    size: Grid size (x, y, z) dimensions.
    lower: Lower corner of the grid.
    resolution: Resolution in units per grid cell. Can have the same resolution
        for each axis or different resolutions.
    """

    def __init__(
        self, size: tuple[int, int, int], lower: Float32[Array, "3"],
        resolution: Union[Float32[Array, "3"], Float32[Array, ""]],
    ) -> None:
        super().__init__()
        self.lower = lower
        self.resolution = resolution
        self.size = size

    def __call__(
        self, x: Float32[Array, "3"], dx: Optional[Float32[Array, "3"]] = None
    ) -> Float32[Array, "2"]:
        """Index into learned reflectance map."""
        grid = hk.get_parameter("grid", (*self.size, 2), init=jnp.zeros)
        index = (x - self.lower) * self.resolution
        valid = jnp.all((0 <= index) & (index <= jnp.array(self.size) - 1))
        return jnp.where(valid, interpolate(index, grid), jnp.zeros((2,)))

    @staticmethod
    def project(params):
        """Project grid parameters to [0, 1]."""
        return jax.tree_util.tree_map(
            partial(jnp.clip, a_min=0.0, a_max=1.0), params)


class NGP:
    """NGP field.

    Parameters
    ----------
    levels: Resolution of each hash table level. The length determines the
        number of hash tables.
    size: Hash table size (and feature dimension).
    units: MLP network parameters.

    References
    ----------
    [1] Muller et al, "Instant Neural Graphics Primitives with a
        Multiresolution Hash Encoding," 2022.
    """

    def __init__(
            self, levels: Float32[Array, "n"],
            size: tuple[int, int] = (16384, 2), units: list[int] = [64, 32]):
        self._init(levels=levels, size=size, units=units, _head=2)

    def _init(
            self, levels: Float32[Array, "n"], _head: int = 2,
            size: tuple[int, int] = (16384, 2), units: list[int] = [64, 32]):
        self.size = size
        self.levels = levels
        mlp = []
        for u in units:
            mlp += [hk.Linear(u), jax.nn.leaky_relu]
        mlp.append(hk.Linear(_head))
        self.head = hk.Sequential(mlp)

    def hash(self, x: Integer[Array, "3"]) -> Integer[Array, ""]:
        """Apply hash function specified by NGP (Eq. 4 [1])."""
        ix = x.astype(jnp.uint32)
        pi2 = jnp.array(2654435761, dtype=jnp.uint32)
        pi3 = jnp.array(805459861, dtype=jnp.uint32)

        return (ix[0] + ix[1] * pi2 + ix[2] * pi3) % self.size[0]

    def lookup(self, x: Float32[Array, "3"]) -> Float32[Array, "n"]:
        """Multiresolution hash table lookup."""
        xscales = x.reshape(1, -1) * self.levels.reshape(-1, 1)
        grid = hk.get_parameter(
            "grid", (self.levels.shape[0], *self.size),
            init=hk.initializers.RandomUniform(0, 0.00001))

        def interpolate_level(xscale, grid_level):
            def hash_table(c):
                return grid_level[self.hash(c)]
            return interpolate(xscale, jax.vmap(hash_table))

        return jax.vmap(interpolate_level)(xscales, grid)

    def __call__(
        self, x: Float32[Array, "3"], dx: Optional[Float32[Array, "3"]] = None
    ) -> Float32[Array, "2"]:
        """Index into learned reflectance map."""
        table_out = self.lookup(x)
        mlp_out = self.head(table_out.reshape(-1))
        alpha = jax.nn.sigmoid(mlp_out[0])
        sigma = jax.nn.relu(mlp_out[1])
        return jnp.array([sigma, alpha])

    @classmethod
    def from_config(cls, levels=8, exponent=0.5, base=4, size=16, features=2):
        """Create NGP haiku closure from config items."""
        def closure():
            return cls(
                levels=base * 2**(exponent * jnp.arange(levels)),
                size=(2**size, features))
        return closure


class NGPSH(NGP):
    """NGP field with spherical harmonics.

    Parameters
    ----------
    levels: Resolution of each hash table level. The length determines the
        number of hash tables.
    harmonics: Number of spherical harmonic coefficients.
    size: Hash table size (and feature dimension).
    units: MLP network parameters.

    References
    ----------
    [1] Muller et al, "Instant Neural Graphics Primitives with a
        Multiresolution Hash Encoding," 2022.
    """

    def __init__(
            self, levels: Float32[Array, "n"], harmonics: int = 25,
            size: tuple[int, int] = (16384, 2), units: tuple = [64, 32]):
        assert harmonics in {1, 4, 9, 16, 25}
        self.harmonics = harmonics
        self._init(levels=levels, size=size, units=units, _head=harmonics + 1)

    def __call__(
        self, x: Float32[Array, "3"], dx: Optional[Float32[Array, "3"]] = None
    ) -> Float32[Array, "2"]:
        """Index into learned reflectance map."""
        table_out = self.lookup(x)
        mlp_out = self.head(table_out.reshape(-1))
        alpha = jax.nn.sigmoid(mlp_out[-1])

        if dx is None:
            sigma = (jnp.sum(mlp_out[0]) - 5)
        else:
            sh = spherical_harmonics(dx, self.harmonics)
            sigma = (jnp.sum(mlp_out[:-1] * sh) - 5)

        return jnp.array([sigma, alpha])
