"""Doppler column methods."""

from jax import numpy as jnp
from jax import vmap

from jaxtyping import Float32, Array
from . import types

from .pose import sensor_to_world


class VirtualRadarColumnMixins:
    """Radar doppler column methods."""

    def angles(
        self, t: Float32[Array, "3 k"]
    ) -> tuple[Float32[Array, "k"], Float32[Array, "k"]]:
        """Get azimuth and elevation from unit sphere values."""
        x, y, z = t
        theta = jnp.arcsin(jnp.clip(z, -0.99999, 0.99999))
        phi = jnp.arcsin(jnp.clip(y / jnp.cos(theta), -0.99999, 0.99999))
        return (theta, phi)

    def gain(self, t: Float32[Array, "3 k"]) -> Float32[Array, "k"]:
        """Compute antenna gain."""
        theta, phi = self.angles(t)
        _theta = theta / jnp.pi * 180 / 56
        _phi = phi / jnp.pi * 180 / 56

        return jnp.exp((
            (0.14 * _phi**6 + 0.13 * _phi**4 - 8.2 * _phi**2)
            + (3.1 * _theta**8 - 22 * _theta**6 + 54 * _theta**4 - 55 * _theta**2)
        ).reshape(1, -1) / 10)

    def render_column(
        self, t: Float32[Array, "3 k"], sigma: types.SigmaField,
        pose: types.RadarPose, weight: Float32[Array, ""]
    ) -> Float32[Array, "nr"]:
        """Render a single doppler column for a radar image.

        Parameters
        ----------
        t: Sensor-space rays on the unit sphere.
        sigma: Field function.
        pose: Sensor pose.
        weight: Sample size weight.

        Returns
        -------
        Rendered column for one doppler value and a stack of range values.
        """
        def project_rays(r):
            t_world = sensor_to_world(r=r, t=t, pose=pose)
            dx = pose.x.reshape(-1, 1) - t_world
            dx_norm = dx / jnp.linalg.norm(dx, axis=0)
            return jnp.nan_to_num(vmap(sigma)(t_world.T, dx=dx_norm.T))

        # Antenna Gain
        gain = self.gain(t)

        # Field steps
        field_vals = vmap(project_rays)(self.r)
        sigma_samples = field_vals[:, :, 0]
        alpha_samples = 1 - field_vals[:, :, 1]

        # Return signal
        transmitted = jnp.concatenate([
            jnp.ones((1, t.shape[1])),
            jnp.cumprod(alpha_samples[:-1], axis=0)
        ], axis=0)
        amplitude = sigma_samples * transmitted * gain

        constant = weight / self.n * self.r
        return jnp.mean(amplitude, axis=1) * constant

    def make_column(
        self, doppler: Float32[Array, ""], pose: types.RadarPose
    ) -> types.TrainingColumn:
        """Create column for training.

        Parameters
        ----------
        d: doppler value.
        pose: sensor pose.

        Returns
        -------
        Training point with per-computed valid bins.
        """
        valid = self.valid_mask(doppler, pose)
        packed = jnp.packbits(valid)
        weight = jnp.sum(valid).astype(jnp.float32) / pose.s
        return types.TrainingColumn(
            pose=pose, valid=packed, weight=weight, doppler=doppler)

    def column_forward(
        self, key: types.PRNGKey, column: types.TrainingColumn,
        sigma: types.SigmaField,
    ) -> Float32[Array, "nr"]:
        """Render a training column.

        Parameters
        ----------
        key : PRNGKey for random sampling.
        column: Pose and y_true.
        sigma: Field function.

        Returns
        -------
        Predicted doppler column.
        """
        valid = jnp.unpackbits(column.valid)
        t = self.sample_rays(
            key, d=column.doppler, valid_psi=valid, pose=column.pose)
        return self.render_column(
            t=t, sigma=sigma, pose=column.pose, weight=column.weight)
