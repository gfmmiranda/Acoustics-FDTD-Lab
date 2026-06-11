import numpy as np
import matplotlib.pyplot as plt
from fractions import Fraction
from scipy.signal import fftconvolve, resample_poly
from scipy.io import wavfile
from src.components import Listener, HarmonicSource
from src.utils import find_first_arrival

class BaseExperiment:
    """
    Manages the simulation lifecycle: Setup -> Run -> Analyze.
    """
    def __init__(self, domain, solver_class, **solver_kwargs):
        self.domain = domain
        self.SolverClass = solver_class
        self.solver_kwargs = solver_kwargs
        self.solver = None
        self.results = {}

    def setup(self):
        """Place measurement microphones (Listeners). Override in subclasses."""
        pass

    def run(self, duration):
        """Execute the physics engine."""
        print(f"🧪 Starting Experiment: {self.__class__.__name__}")
        self.solver = self.SolverClass(self.domain, **self.solver_kwargs)
        
        steps = int(duration / self.solver.dt)
        print(f"   Simulating {duration:.3f}s ({steps} steps)...")
        
        for i in range(steps):
            self.solver.step()
            
        print("✅ Experiment Complete.")

    def analyze(self):
        """Process listener data. Override in subclasses."""
        raise NotImplementedError

class DirectivityExperiment(BaseExperiment):
    """
    Virtual Anechoic Chamber: Measures polar patterns.
    """
    def __init__(self, domain, solver_class, radius=2.0, num_points=72, **solver_kwargs):
        super().__init__(domain, solver_class, **solver_kwargs)
        self.center = domain.L/2.0
        self.radius = radius
        self.num_points = num_points
        self.listeners = []
        self.angles = np.linspace(0, 2*np.pi, num_points, endpoint=False)

    def setup(self):
        """Deploys a ring of listeners around the center."""
        cx, cy = self.center
        self.listeners = []
        
        for theta in self.angles:
            lx = cx + self.radius * np.cos(theta)
            ly = cy + self.radius * np.sin(theta)
            
            l = Listener(pos=[lx, ly], tag=f"deg_{int(np.degrees(theta))}")
            self.domain.add_listener(l)
            self.listeners.append(l)
            
        print(f"   Deployed {len(self.listeners)} microphones at r={self.radius}m.")

    def analyze(self):
        """Extracts peak amplitude from each microphone."""
        magnitudes = []
        for l in self.listeners:
            _, signal = l.get_time_series()
            # Get steady-state peak (last 20% of signal)
            steady_state = signal[int(len(signal)*0.8):]
            magnitudes.append(np.max(np.abs(steady_state)))
            
        self.results['angles'] = self.angles
        self.results['magnitudes'] = np.array(magnitudes)
        
        return self.results

    def plot(self, ax=None, label='Measured', color=None):
        """
        Plot the normalised polar directivity pattern.

        Parameters
        ----------
        ax : matplotlib PolarAxes, optional
            Existing polar axis to draw on. If None, a new figure is created.
        label : str
            Legend label for this pattern.
        color : str or tuple, optional
            Line (and fill) colour. If None, the next colour in the axes cycle is used.

        Returns
        -------
        ax : matplotlib PolarAxes
        """
        if 'magnitudes' not in self.results:
            self.analyze()

        theta = np.concatenate([self.results['angles'], [self.results['angles'][0]]])
        r = np.concatenate([self.results['magnitudes'], [self.results['magnitudes'][0]]])
        r_norm = r / (np.max(r) + 1e-12)

        created = ax is None
        if created:
            fig = plt.figure(figsize=(8, 8))
            ax = fig.add_subplot(111, projection='polar')

        plot_kw = {'linewidth': 2, 'label': label}
        if color is not None:
            plot_kw['color'] = color

        # Capture the colour actually used so the fill matches the line exactly.
        line = ax.plot(theta, r_norm, **plot_kw)[0]
        line_color = line.get_color()

        # Fill only in standalone mode; overlays with multiple patterns become
        # unreadable when fills stack up.
        if created:
            ax.fill(theta, r_norm, alpha=0.20, color=line_color)

        ax.set_theta_zero_location('E')
        ax.set_theta_direction(1)

        if created:
            ax.set_title('Directivity Pattern', va='bottom')
            ax.legend()
            plt.show()

        return ax

class ImpulseResponseExperiment(BaseExperiment):
    """
    Measures the System Response (Impulse Response & Frequency Response).
    
    Requirements:
    - The Domain should contain a broadband source (e.g., RickerSource).
    """
    def __init__(self, domain, solver_class, measure_pos, **solver_kwargs):
        super().__init__(domain, solver_class, **solver_kwargs)
        self.measure_pos = measure_pos
        self.listener = None
        
    def setup(self):
        """Places a measurement microphone."""
        self.listener = Listener(pos=self.measure_pos, tag="measurement_mic")
        self.domain.add_listener(self.listener)
        print(f"   Microphone placed at {self.measure_pos}")

    def analyze(self):
        """Computes FFT of the recorded signal."""
        if not self.listener:
            raise ValueError("Experiment not set up.")
            
        times, signal = self.listener.get_time_series()
        freqs, mag = self.listener.compute_spectrum()

        # Record source signal at the same time grid
        source_signal = np.zeros_like(times)
        if self.domain.sources:
            src = self.domain.sources[0]
            source_signal = np.array([src.value(t) for t in times])
        
        # Convert to dB (avoid log(0) errors)
        mag_db = 20 * np.log10(mag + 1e-12)
        
        # Normalize peak to 0 dB for readability
        mag_db = mag_db - np.max(mag_db)
        
        self.results['times'] = times
        self.results['signal'] = signal
        self.results['source_signal'] = source_signal
        self.results['freqs'] = freqs
        self.results['mag_db'] = mag_db
        
        return self.results

    def plot(self):
        """Plots Time Domain (IR) and Frequency Domain (FR)."""
        if 'signal' not in self.results:
            self.analyze()

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        
        # 1. Impulse Response (Time)
        ax1.plot(self.results['times'], self.results['signal'], color='black', lw=1)
        ax1.set_title("Impulse Response (Time Domain)")
        ax1.set_xlabel("Time (s)")
        ax1.set_ylabel("Amplitude")
        ax1.grid(True, alpha=0.3)
        
        # 2. Frequency Response (Bode Magnitude)
        ax2.semilogx(self.results['freqs'], self.results['mag_db'], color='tab:blue', lw=1.5)
        ax2.set_title("Frequency Response (0dB Normalized)")
        ax2.set_xlabel("Frequency (Hz)")
        ax2.set_ylabel("Magnitude (dB)")
        ax2.set_xlim(20, 20000) # Audio range
        ax2.set_ylim(-60, 5)    # Typical dynamic range
        ax2.grid(True, which="both", alpha=0.3)
        
        plt.tight_layout()
        plt.show()

class SubwooferArrayExperiment(BaseExperiment):
    """
    Simulates coherent low-frequency source arrays and analyses spatial sound coverage.

    Runs a harmonic steady-state simulation and computes the RMS pressure field
    over the quasi-steady tail of the run using an online accumulator, avoiding
    the memory cost of storing all time-step frames.

    Parameters
    ----------
    domain : Domain2D
        Computational domain.
    solver_class : type
        PDE solver class to instantiate, typically ``Wave``.
    frequency : float
        Source frequency in Hz.
    sources : list of dict
        Source configurations. Each dict must contain:
            ``pos``       – [x, y] physical position.
        Optional keys:
            ``amplitude`` – float, default 1.0  (use -1.0 for polarity inversion).
            ``phase``     – float, phase offset in radians, default 0.0.
            ``delay``     – float, time delay in seconds (converted to phase internally).
    steady_fraction : float, default 0.5
        Fraction of the run over which to accumulate RMS (tail of the simulation).
    audience_region : dict, optional
        Rectangular region for coverage metrics:
        ``{"x_min": ..., "x_max": ..., "y_min": ..., "y_max": ...}``
    **solver_kwargs
        Forwarded verbatim to the solver constructor (e.g. ``c``, ``boundary_type``).
    """

    def __init__(
        self,
        domain,
        solver_class,
        frequency,
        sources,
        steady_fraction=0.5,
        audience_region=None,
        **solver_kwargs,
    ):
        super().__init__(domain, solver_class, **solver_kwargs)
        self.frequency       = frequency
        self.sources         = sources
        self.steady_fraction = steady_fraction
        self.audience_region = audience_region
        self._rms_acc        = None
        self._rms_count      = 0
        self._is_setup       = False

    def setup(self):
        """Register HarmonicSource objects with the domain from the sources config list."""
        self.domain.sources = []   # clear any stale sources from a previous run

        for cfg in self.sources:
            phase = cfg.get("phase", 0.0)
            if "delay" in cfg:
                phase -= 2.0 * np.pi * self.frequency * cfg["delay"]

            src = HarmonicSource(
                pos=cfg["pos"],
                frequency=self.frequency,
                amplitude=cfg.get("amplitude", 1.0),
                phase=phase,
            )
            self.domain.add_source(src)

        self._is_setup = True

    def run(self, duration):
        """
        Step the solver for *duration* seconds, accumulating quasi-steady RMS.

        Calls ``setup()`` automatically if not already done. Uses an online
        running-sum accumulator so memory usage is proportional to domain size,
        not simulation length.

        Returns ``self`` to allow method chaining: ``exp.run(0.2).analyze()``.
        """
        if not self._is_setup:
            self.setup()

        print(f"  [{self.frequency:.0f} Hz] Simulating {duration:.3f} s...")
        self.solver = self.SolverClass(self.domain, **self.solver_kwargs)

        steps  = int(duration / self.solver.dt)
        cutoff = int((1.0 - self.steady_fraction) * steps)

        self._rms_acc   = None
        self._rms_count = 0

        for i in range(steps):
            self.solver.step()
            if i >= cutoff:
                frame = np.array(self.solver.u_curr, dtype=float)
                frame[~self.solver.domain.mask] = np.nan
                self._rms_acc = (
                    frame ** 2 if self._rms_acc is None else self._rms_acc + frame ** 2
                )
                self._rms_count += 1

        print(f"  Done ({self._rms_count} steady-state frames).")
        return self

    def analyze(self):
        """
        Compute RMS map, relative dB map, and optional coverage metrics.

        Populates ``self.results`` with ``rms_map``, ``level_db``, ``ref_rms``,
        and (if ``audience_region`` is set) ``coverage``.

        Returns ``self.results`` and allows method chaining.
        """
        if self._rms_acc is None:
            raise RuntimeError("Call run() before analyze().")

        rms_map  = np.sqrt(self._rms_acc / max(self._rms_count, 1))
        ref      = float(np.nanmax(rms_map))
        level_db = 20.0 * np.log10(rms_map / (ref + 1e-12) + 1e-12)

        self.results["rms_map"]  = rms_map
        self.results["level_db"] = level_db
        self.results["ref_rms"]  = ref

        if self.audience_region is not None:
            self.results["coverage"] = self.compute_coverage_metrics(level_db)

        return self

    def _audience_mask(self):
        r    = self.audience_region
        X, Y = self.domain.grids
        return (
            (X >= r["x_min"]) & (X <= r["x_max"]) &
            (Y >= r["y_min"]) & (Y <= r["y_max"]) &
            self.domain.mask
        )

    def compute_coverage_metrics(self, level_db):
        """Return uniformity statistics for the audience region as a dict."""
        mask   = self._audience_mask()
        values = level_db[mask]
        values = values[~np.isnan(values)]
        if len(values) == 0:
            return {}
        return {
            "mean_db":            float(np.mean(values)),
            "std_db":             float(np.std(values)),
            "spread_p95_p5_db":   float(np.percentile(values, 95) - np.percentile(values, 5)),
            "min_db":             float(np.min(values)),
            "max_db":             float(np.max(values)),
            "fraction_below_m6":  float(np.mean(values < -6.0)),
            "fraction_below_m12": float(np.mean(values < -12.0)),
        }

    def print_coverage(self, label=""):
        """Print a formatted summary of the audience-area coverage metrics."""
        if "coverage" not in self.results:
            if self.audience_region is not None:
                self.analyze()
            else:
                print("No audience_region defined.")
                return
        m   = self.results["coverage"]
        tag = f"  [{label}]" if label else ""
        print(f"\n{'─'*44}{tag}")
        print(f"  Mean level        : {m['mean_db']:+.1f} dB")
        print(f"  Std deviation     : {m['std_db']:.1f} dB")
        print(f"  P95\u2013P05 spread    : {m['spread_p95_p5_db']:.1f} dB")
        print(f"  Min / Max         : {m['min_db']:+.1f} / {m['max_db']:+.1f} dB")
        print(f"  Below \u22126 dB        : {m['fraction_below_m6']*100:.1f}%")
        print(f"  Below \u221212 dB       : {m['fraction_below_m12']*100:.1f}%")

    def compute_fb_ratio(self, forward_pos, backward_pos):
        """
        Compute the front-to-back SPL ratio between two measurement points.

        Parameters
        ----------
        forward_pos  : [x, y]  — target 'forward' position (toward audience).
        backward_pos : [x, y]  — target 'backward' position (toward stage).

        Returns
        -------
        dict with keys ``forward_rms``, ``backward_rms``, ``fb_ratio_db``.
        """
        if "rms_map" not in self.results:
            self.analyze()

        def sample(pos):
            ix = int(np.clip(round(pos[0] / self.domain.ds[0]), 0,
                             self.results["rms_map"].shape[0] - 1))
            iy = int(np.clip(round(pos[1] / self.domain.ds[1]), 0,
                             self.results["rms_map"].shape[1] - 1))
            return float(self.results["rms_map"][ix, iy])

        fwd = sample(forward_pos)
        bck = sample(backward_pos)
        return {
            "forward_rms":  fwd,
            "backward_rms": bck,
            "fb_ratio_db":  20.0 * np.log10((fwd + 1e-12) / (bck + 1e-12)),
        }

    def plot_heatmap(self, ax=None, vmin=-30, vmax=0, title=None,
                     show_colorbar=True, show_audience=False):
        """
        Plot the relative-level dB heatmap of the RMS pressure field.

        Parameters
        ----------
        ax             : matplotlib Axes, optional.  Created if None.
        vmin, vmax     : dB colour-scale limits.
        title          : Axes title.  Defaults to frequency label.
        show_colorbar  : bool.
        show_audience  : bool — overlay audience region as a dashed rectangle.

        Returns
        -------
        (ax, im) — axes and the imshow AxesImage, for external colorbar handling.
        """
        if "level_db" not in self.results:
            self.analyze()

        if ax is None:
            _, ax = plt.subplots(figsize=(10, 6))

        im = ax.imshow(
            self.results["level_db"].T,
            origin="lower",
            extent=[0, self.domain.L[0], 0, self.domain.L[1]],
            cmap="viridis",
            vmin=vmin, vmax=vmax,
            aspect="equal",
        )

        if show_colorbar:
            plt.colorbar(im, ax=ax, label="Relative level [dB]")

        for cfg in self.sources:
            x, y = cfg["pos"]
            ax.plot(x, y, "r*", markersize=14,
                    markeredgecolor="white", markeredgewidth=0.8)

        if show_audience and self.audience_region is not None:
            r    = self.audience_region
            rect = plt.Rectangle(
                (r["x_min"], r["y_min"]),
                r["x_max"] - r["x_min"],
                r["y_max"] - r["y_min"],
                linewidth=1.5, edgecolor="white",
                facecolor="none", linestyle="--",
            )
            ax.add_patch(rect)

        ax.set_xlabel("X [m]")
        ax.set_ylabel("Y [m]")
        ax.set_title(title or f"{self.frequency:.0f} Hz \u2014 RMS level [dB]")

        return ax, im

class AuralizationExperiment(BaseExperiment):
    """
    Renders wet audio by convolving a dry signal with a simulated impulse response.

    This class is intentionally kept separate from the solver-based experiments.
    Use ``ImpulseResponseExperiment`` to obtain an IR, then pass it here for audio
    rendering.

    Workflow::

        aur = AuralizationExperiment(
            dry_audio=dry,
            sample_rate=44100,
            impulse_response=ir_results["signal"],
            ir_sample_rate=1 / ir_exp.solver.dt,
        )
        wet = aur.render()
        aur.export("wet_room.wav")

    Parameters
    ----------
    dry_audio : array-like
        Mono dry input signal (float64, peak-normalized to ±1).
    sample_rate : int
        Sample rate of ``dry_audio`` in Hz.
    impulse_response : array-like
        Simulated impulse response from a listener recording.
    ir_sample_rate : float
        Sample rate of ``impulse_response`` in Hz (typically ``1 / solver.dt``).
    normalize_ir : bool, default True
        Normalize the IR by RMS energy before convolution.
    trim_ir : bool, default True
        Trim near-silent samples from the tail of the IR.
    align_ir : bool, default True
        Trim leading silence/source delay before the first significant arrival.
    alignment_threshold : float, default 0.01
        Detection threshold as a fraction of the signal peak (passed to
        ``find_first_arrival`` as ``threshold_ratio``).
    pre_delay_ms : float, default 2.0
        Milliseconds of signal to retain before the detected first arrival.
    source_signal : array-like or None, default None
        Source excitation signal at ``ir_sample_rate``.  Required when
        ``deconvolve_ir=True``.
    deconvolve_ir : bool, default False
        Estimate the room impulse response by deconvolving the source wavelet
        before further preprocessing.  Requires ``source_signal``.
    deconvolution_reg : float, default 1e-4
        Regularisation factor for the Wiener deconvolution.
    """

    def __init__(
        self,
        dry_audio,
        sample_rate,
        impulse_response,
        ir_sample_rate,
        normalize_ir=True,
        trim_ir=True,
        align_ir=True,
        alignment_threshold=0.01,
        pre_delay_ms=2.0,
        source_signal=None,
        deconvolve_ir=False,
        deconvolution_reg=1e-4,
    ):
        self.dry_audio = np.asarray(dry_audio, dtype=float)
        self.sample_rate = int(sample_rate)
        self.impulse_response = np.asarray(impulse_response, dtype=float)
        self.ir_sample_rate = float(ir_sample_rate)
        self.normalize_ir = normalize_ir
        self.trim_ir = trim_ir
        self.align_ir = align_ir
        self.alignment_threshold = alignment_threshold
        self.pre_delay_ms = pre_delay_ms
        self.source_signal = None if source_signal is None else np.asarray(source_signal, dtype=float)
        self.deconvolve_ir = deconvolve_ir
        self.deconvolution_reg = deconvolution_reg
        self.ir_trim_time = 0.0
        self._ir_processed = None
        self._wet_audio = None

    def prepare_ir(self):
        """
        Preprocess the impulse response.

        Steps applied in order:

        1. Remove DC offset.
        2. Deconvolve source wavelet (optional).
        3. Align to first significant arrival (optional).
        4. Trim near-silent tail (optional).
        5. Resample to match ``sample_rate`` (if needed).
        6. Normalise by RMS energy (optional).

        Returns
        -------
        ir : np.ndarray
            Processed impulse response at ``sample_rate``.
        """
        ir = self.impulse_response.copy()

        # 1. Remove DC offset
        ir = ir - np.mean(ir)

        # 2. Deconvolve source wavelet (at simulation rate, before any resampling)
        if self.deconvolve_ir:
            if self.source_signal is None:
                raise ValueError(
                    "source_signal must be provided when deconvolve_ir=True"
                )
            ir = deconvolve_source(ir, self.source_signal, reg=self.deconvolution_reg)

        # 3. Align to first significant arrival (before resampling)
        if self.align_ir:
            first = find_first_arrival(np.abs(ir), threshold_ratio=self.alignment_threshold)
            pre = int(round(self.pre_delay_ms * 1e-3 * self.ir_sample_rate))
            start = max(0, first - pre)
            ir = ir[start:]
            self.ir_trim_time = start / self.ir_sample_rate

        # 3. Trim near-silent tail
        if self.trim_ir:
            peak = np.max(np.abs(ir))
            if peak > 0:
                threshold = 1e-5 * peak
                nonzero = np.where(np.abs(ir) > threshold)[0]
                if len(nonzero) > 0:
                    ir = ir[: nonzero[-1] + 1]

        # 4. Resample to audio sample rate
        if not np.isclose(self.ir_sample_rate, self.sample_rate, rtol=1e-3):
            ratio = Fraction(self.sample_rate, int(round(self.ir_sample_rate))).limit_denominator(1000)
            ir = resample_poly(ir, ratio.numerator, ratio.denominator)

        # 5. Normalise by RMS energy
        if self.normalize_ir:
            ir = ir / (np.sqrt(np.sum(ir ** 2)) + 1e-12)

        self._ir_processed = ir
        return ir

    def render(self):
        """
        Convolve the dry signal with the processed IR.

        Returns
        -------
        wet : np.ndarray
            Peak-normalised wet output signal.
        """
        if self._ir_processed is None:
            self.prepare_ir()

        wet = fftconvolve(self.dry_audio, self._ir_processed, mode="full")

        # Avoid clipping without always forcing peak to 1
        peak = np.max(np.abs(wet)) + 1e-12
        if peak > 0.99:
            wet = 0.99 * wet / peak

        self._wet_audio = wet
        return wet

    def export(self, path):
        """
        Write the wet audio to a 16-bit PCM WAV file.

        Parameters
        ----------
        path : str
            Output file path (e.g. ``"wet_room.wav"``).
        """
        if self._wet_audio is None:
            self.render()

        pcm = np.int16(np.clip(self._wet_audio, -1.0, 1.0) * 32767)
        wavfile.write(path, self.sample_rate, pcm)
        print(f"   Exported: {path}")

    def plot(self, title="Auralization"):
        """
        Four-panel diagnostic plot: dry waveform, processed IR, wet waveform,
        and wet spectrogram.

        Parameters
        ----------
        title : str
            Figure suptitle.
        """
        if self._wet_audio is None:
            self.render()

        t_dry = np.arange(len(self.dry_audio)) / self.sample_rate
        t_ir = np.arange(len(self._ir_processed)) / self.sample_rate
        t_wet = np.arange(len(self._wet_audio)) / self.sample_rate

        fig, axes = plt.subplots(2, 2, figsize=(14, 8))
        fig.suptitle(title, fontsize=14)

        axes[0, 0].plot(t_dry, self.dry_audio, lw=0.8, color="tab:blue")
        axes[0, 0].set_title("Dry Audio (Input)")
        axes[0, 0].set_xlabel("Time (s)")
        axes[0, 0].set_ylabel("Amplitude")
        axes[0, 0].grid(True, alpha=0.3)

        axes[0, 1].plot(t_ir, self._ir_processed, lw=0.8, color="tab:orange")
        axes[0, 1].set_title("Processed Impulse Response")
        axes[0, 1].set_xlabel("Time (s)")
        axes[0, 1].set_ylabel("Amplitude")
        axes[0, 1].grid(True, alpha=0.3)

        axes[1, 0].plot(t_wet, self._wet_audio, lw=0.8, color="tab:green")
        axes[1, 0].set_title("Wet Audio (Output)")
        axes[1, 0].set_xlabel("Time (s)")
        axes[1, 0].set_ylabel("Amplitude")
        axes[1, 0].grid(True, alpha=0.3)

        axes[1, 1].specgram(self._wet_audio, Fs=self.sample_rate, cmap="viridis")
        axes[1, 1].set_title("Wet Audio Spectrogram")
        axes[1, 1].set_xlabel("Time (s)")
        axes[1, 1].set_ylabel("Frequency (Hz)")

        plt.tight_layout()
        plt.show()

def deconvolve_source(recorded, source_signal, reg=1e-4):
    """
    Estimate the room impulse response by deconvolving the source wavelet.

    Uses Wiener / regularised spectral division:

        H(f) = Y(f) S*(f) / (|S(f)|² + reg · max|S(f)|²)

    Parameters
    ----------
    recorded : np.ndarray
        Listener recording at the simulation sample rate.
    source_signal : np.ndarray
        Source excitation signal at the same sample rate.
    reg : float, default 1e-4
        Regularisation factor to prevent division by near-zero.

    Returns
    -------
    h : np.ndarray
        Estimated room impulse response, same length as ``recorded``.
    """
    recorded = np.asarray(recorded, dtype=float)
    source_signal = np.asarray(source_signal, dtype=float)

    n_fft = int(2 ** np.ceil(np.log2(len(recorded) + len(source_signal) - 1)))

    Y = np.fft.rfft(recorded, n=n_fft)
    S = np.fft.rfft(source_signal, n=n_fft)

    denom = np.abs(S) ** 2
    eps = reg * (np.max(denom) + 1e-12)

    H = Y * np.conj(S) / (denom + eps)
    h = np.fft.irfft(H, n=n_fft)

    return h[:len(recorded)]