"""Common DART types."""

from jaxtyping import Array, Integer, Float32, UInt8
from beartype.typing import Union, Callable, NamedTuple


#: PRNGKey
PRNGKey = Integer[Array, "2"]

#: PRNGKey seed
PRNGSeed = Union[PRNGKey, int]

#: Loss function
LossFunc = Callable[
    [Float32[Array, "..."], Float32[Array, "..."]], Float32[Array, "..."]]

#: Reflectance field
SigmaField = Callable[[Float32[Array, "3"]], Float32[Array, "2"]]


class CameraPose(NamedTuple):
    """Camera pose parameters for simple ray rendering.

    x: sensor location in global coordinates.
    A: 3D rotation matrix for sensor pose; should transform sensor-space to
        world-space.
    """

    x: Float32[Array, "3"]
    A: Float32[Array, "3 3"]


class RadarPose(NamedTuple):
    """Radar pose parameters (24 x 4 = 96 bytes).

    Attributes
    ----------
    v: normalized velocity direction (``||v||_2=1``).
    p, q: orthonormal basis along with ``v``.
    s: speed (magnitude of un-normalized velocity).
    x: sensor location in global coordinates.
    A: 3D rotation matrix for sensor pose; should transform sensor-space to
        world-space.
    """

    v: Float32[Array, "3"]
    p: Float32[Array, "3"]
    q: Float32[Array, "3"]
    s: Float32[Array, ""]
    x: Float32[Array, "3"]
    A: Float32[Array, "3 3"]


class TrainingColumn(NamedTuple):
    """Single column for training.

    For 256 range bins and 256 angular bins, this takes::

        96 + 256 / 8 + 4 + 4 = 136 bytes.

    Attributes
    ----------
    pose: pose for each column (96 bytes).
    valid: validity of each angular bin; bit-packed bool array (n / 8 bytes).
    weight: velocity-corrected weight of each bin (4 bytes).
    doppler: doppler value for this column (4 bytes).
    """

    pose: RadarPose
    valid: UInt8[Array, "n8"]
    weight: Float32[Array, ""]
    doppler: Float32[Array, ""]
