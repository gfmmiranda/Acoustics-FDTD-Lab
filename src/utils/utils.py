from typing import Callable, List
import numpy as np
from scipy.signal import find_peaks


def get_normal_mode_dirichlet(modes: List[int], domain) -> Callable[..., np.ndarray]:
    """
    Return a Dirichlet normal mode function for a rectangular domain.

    The returned callable computes the product of sin(nᵢ·π·xᵢ / Lᵢ)
    over all dimensions. Works for any number of dimensions.

    Parameters
    ----------
    modes : list of int
        Mode number for each dimension, e.g. [n] for 1D or [n, m] for 2D.
    domain : Domain1D or Domain2D
        Computational domain providing physical lengths.

    Returns
    -------
    callable
        Function (*grids) -> np.ndarray, compatible with Wave/Heat solvers.
    """
    L = domain.L
    def field(*grids: np.ndarray) -> np.ndarray:
        result = np.ones_like(grids[0], dtype=float)
        for grid, Li, n in zip(grids, L, modes):
            result = result * np.sin(n * np.pi * grid / Li)
        return result
    return field


def get_normal_mode_neumann(modes: List[int], domain) -> Callable[..., np.ndarray]:
    """
    Return a Neumann normal mode function for a rectangular domain.

    The returned callable computes the product of cos(nᵢ·π·xᵢ / Lᵢ)
    over all dimensions. Works for any number of dimensions.

    Parameters
    ----------
    modes : list of int
        Mode number for each dimension, e.g. [n] for 1D or [n, m] for 2D.
    domain : Domain1D or Domain2D
        Computational domain providing physical lengths.

    Returns
    -------
    callable
        Function (*grids) -> np.ndarray, compatible with Wave/Heat solvers.
    """
    L = domain.L
    def field(*grids: np.ndarray) -> np.ndarray:
        result = np.ones_like(grids[0], dtype=float)
        for grid, Li, n in zip(grids, L, modes):
            if n == 0:
                continue  # mode 0 = no modulation in this dimension
            result = result * np.cos(n * np.pi * grid / Li)
        return result
    return field


def get_initial_gaussian(
    pos: list,
    sigma: float
) -> Callable[..., np.ndarray]:
    """
    Generate an N-dimensional Gaussian pulse function.
    
    Parameters
    ----------
    pos : list of float
        Center coordinates [x0, y0, ...].
    sigma : float
        Standard deviation (pulse width).
    
    Returns
    -------
    callable
        Function computing exp(-|r - r0|² / 2σ²) for any dimension.
    """
    center = np.atleast_1d(np.array(pos, dtype=float))

    def displacement(*coords: np.ndarray) -> np.ndarray:
        dist_sq = 0.0
        for i, grid in enumerate(coords):
            dist_sq += (grid - center[i])**2
        return np.exp(-dist_sq / (2 * sigma**2))

    return displacement


def find_first_arrival(signal: np.ndarray, threshold_ratio: float = 0.1) -> int:
    """
    Detect the first significant peak in a signal (direct sound arrival).
    
    Parameters
    ----------
    signal : np.ndarray
        Input time-domain signal.
    threshold_ratio : float, default=0.1
        Minimum peak height as fraction of global maximum.
    
    Returns
    -------
    int
        Index of first arrival. Falls back to global maximum if no peaks found.
    """
    max_val = np.max(signal)
    min_height = max_val * threshold_ratio
    
    peaks, _ = find_peaks(signal, height=min_height, distance=5)
    
    if len(peaks) > 0:
        return peaks[0]
    else:
        return np.argmax(signal)

