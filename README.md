# Acoustics FDTD Lab

A Python-based **finite-difference time-domain (FDTD)** laboratory for studying acoustic wave propagation, room impulse responses, boundary absorption, source directivity, and basic auralization workflows.

The project is centered on the **2D acoustic wave equation**, with applications in room acoustics, numerical acoustics, acoustic measurement simulation, and spatial audio prototyping. The underlying architecture is intentionally general: the same solver interface can also be used for other PDEs, such as the **heat diffusion equation**.

---

## Overview

`Acoustics FDTD Lab` provides a modular framework for simulating wave propagation in discretized physical domains. It allows users to define domains, sources, listeners, boundary conditions, and obstacles, then observe how acoustic fields evolve over time.

The project currently supports experiments such as:

- acoustic wave propagation in 2D rooms,
- impulse-response extraction from virtual microphones,
- reflective, absorptive, and partially absorptive boundary conditions,
- source directivity experiments,
- multi-source configurations,
- double-slit diffraction experiments,
- obstacle-based propagation studies,
- simple heat-diffusion simulations using the same PDE-solving interface.

The long-term goal is to build a small **virtual acoustics laboratory** that connects numerical wave simulation, acoustic measurement, room impulse responses, and listening-based auralization.

---

## Motivation

Acoustics is fundamentally the study of mechanical waves propagating through media. Many important acoustic phenomena — reflection, diffraction, interference, reverberation, absorption, and room response — can be studied numerically by solving wave equations over space and time.

This project was developed as a computational exploration of those ideas. It combines:

- partial differential equations,
- finite-difference numerical methods,
- acoustic wave propagation,
- signal processing,
- room impulse response analysis,
- virtual microphones and simulated measurements.

Rather than being only a visualization tool, the project is designed as a research-oriented sandbox for testing how physical modeling can be connected to acoustic and audio applications.

---

## Main Features

### Acoustic Wave Simulation

The core solver implements an FDTD scheme for the acoustic wave equation:

```math
\frac{\partial^2 p}{\partial t^2} = c^2 \nabla^2 p
```

where \(p\) is the acoustic pressure field and \(c\) is the speed of sound.

The solver can be used to simulate:

- free-field propagation,
- room reflections,
- obstacle scattering,
- diffraction,
- interference,
- source radiation patterns,
- time-domain pressure fields.

---

### General PDE Solver Interface

Although the main focus is acoustics, the architecture is not restricted to the wave equation.

The project includes a general `PDESolver` abstraction responsible for shared simulation logic such as:

- time stepping,
- interaction with the computational domain,
- source updates,
- listener recording,
- simulation state management.

This makes it possible to implement different PDE solvers using a common interface. For example, the project also includes a solver for the **heat equation**:

```math
\frac{\partial u}{\partial t} = \kappa \nabla^2 u
```

This demonstrates that the framework can be extended beyond acoustics while preserving the same domain and simulation abstractions.

---

### Modular Domain Architecture

The domain system is built around a flexible hierarchy.

#### `BaseDomain`

`BaseDomain` defines the general structure shared by computational domains. It handles core responsibilities such as:

- spatial discretization,
- grid resolution,
- coordinate conversion,
- domain geometry,
- boundary representation,
- obstacle masks.

The goal of `BaseDomain` is to make the numerical solvers independent from implementation details of a specific spatial dimension.

#### `Domain2D`

`Domain2D` specializes the base domain for two-dimensional simulations. It supports:

- rectangular 2D grids,
- configurable physical size,
- user-defined spatial resolution,
- obstacle masks,
- source and listener placement,
- room-like simulation setups,
- propagation studies in complex geometries.

This separation makes it easier to extend the project with additional domain types, geometries, or higher-dimensional simulations in the future.

---

## Available Experiments

### 1. Source Simulation

The simulator supports different acoustic source types.

Current source configurations include:

- **Ricker wavelet sources**  
  Useful as impulse-like, band-limited excitations for room impulse response estimation.

- **Point harmonic sources**  
  Sinusoidal sources for steady-state or narrowband propagation experiments.

- **Multiple-source combinations**  
  Several sources can be combined to create more complex radiation patterns.

Examples of multi-source configurations include:

- idealized dipoles,
- line sources,
- simplified loudspeaker cabinet configurations,
- source arrays.

These experiments are useful for observing how source geometry affects the resulting acoustic field.

---

### 2. Virtual Listeners / Microphones

Listeners can be placed inside the domain to record the acoustic pressure signal over time.

This allows the simulation to produce not only field visualizations, but also time-domain signals similar to what would be captured by microphones.

Possible uses:

- extracting received waveforms,
- measuring propagation delay,
- estimating impulse responses,
- comparing microphone positions,
- studying direct and reflected sound,
- analyzing source-listener distance effects.

---

### 3. Room Impulse Responses

By using an impulse-like source, such as a Ricker wavelet, and recording the pressure at one or more listeners, the simulator can estimate room impulse responses under different boundary conditions.

Supported wall conditions include:

- **fully reflective boundaries**,
- **fully absorptive boundaries**,
- **partially absorptive / partially reflective boundaries**.

This makes it possible to study how wall behavior affects:

- early reflections,
- reverberation decay,
- direct-to-reverberant ratio,
- temporal structure of the received signal,
- room acoustic response.

These impulse responses can later be used for convolution-based auralization.

---

### 4. Directivity Experiments

Source directivity can be studied by placing a ring of virtual microphones around a source.

This makes it possible to estimate how the radiated field varies with angle.

Example experiments:

- compare monopole-like and dipole-like radiation,
- analyze interference between multiple sources,
- approximate radiation from idealized loudspeaker configurations,
- visualize polar response patterns.

A typical workflow is:

1. place a source at the center of the domain,
2. place listeners on a circular ring around it,
3. run the simulation,
4. extract peak amplitude or frequency response at each listener,
5. plot the resulting polar directivity pattern.

---

### 5. Double-Slit and Obstacle Experiments

The domain can include obstacle masks that block or modify wave propagation.

This enables classic wave-physics demonstrations such as:

- double-slit diffraction,
- scattering around barriers,
- interference patterns,
- shadow zones,
- reflection from internal obstacles.

These experiments are useful for connecting numerical acoustics to fundamental wave behavior.

---

### 6. Heat Diffusion

The same framework can also simulate heat diffusion using the heat equation solver.

This is included mainly to demonstrate the generality of the `PDESolver` abstraction.

Example uses:

- diffusion from an initial Gaussian distribution,
- boundary-condition experiments,
- comparison between wave-like and diffusive PDE behavior.

---

## Boundary Conditions

The project supports several types of boundary conditions.

### Dirichlet Boundaries

Fixed-value boundaries, for example:

```math
u = 0
```

These can be used to model constrained fields or idealized pressure-release boundaries.

---

### Neumann Boundaries

Zero-gradient boundaries:

```math
\frac{\partial u}{\partial n} = 0
```

In acoustic simulations, these behave like idealized rigid reflective walls.

---

### Robin Boundaries

Mixed boundary conditions of the form:

```math
a u + b \frac{\partial u}{\partial n} = g
```

These are used to approximate frequency-independent wall absorption or impedance-like boundary behavior.

In the context of room acoustics, Robin boundaries allow the simulation of partially reflective and partially absorptive walls.

---

## Project Structure

```text
src/
├── core/
│   ├── domain.py           # BaseDomain, Domain2D, grid and geometry logic
│   └── pdesolver.py        # General PDE solver interface and time-stepping structure
│
├── solvers/
│   ├── wave.py             # Acoustic wave equation FDTD solver
│   └── heat.py             # Heat diffusion finite-difference solver
│
├── components/
│   ├── sources.py          # Ricker, harmonic, point and composite source definitions
│   └── listeners.py        # Virtual microphones / pressure receivers
│
├── visualization/
│   └── animator.py         # Field visualization and animation utilities
│
└── utils/
    └── utils.py            # Helper functions and initial condition generators
```

The code is organized so that each part of the simulation has a clear responsibility:

| Module | Responsibility |
|---|---|
| `core/domain.py` | Spatial grids, coordinate conversion, domain masks, geometry |
| `core/pdesolver.py` | General simulation lifecycle and solver abstraction |
| `solvers/wave.py` | Acoustic wave propagation |
| `solvers/heat.py` | Heat diffusion |
| `components/sources.py` | Time-dependent source models |
| `components/listeners.py` | Virtual microphone recording |
| `visualization/animator.py` | Interactive visualizations |

---

## Example: 2D Acoustic Wave Simulation

```python
import numpy as np

from src.core.domain import Domain2D
from src.solvers.wave import Wave
from src.components.sources import RickerSource
from src.components.listeners import Listener
from src.visualization.animator import PhysicsAnimator

# 1. Create a 2D room
room = Domain2D(
    length=[10.0, 10.0],
    dx=0.05
)

# 2. Configure the acoustic wave solver
solver = Wave(
    domain=room,
    c=343.0,
    boundary_type="robin",
    alpha=0.2
)

# 3. Add an impulse-like source
source = RickerSource(
    pos=[5.0, 5.0],
    peak_freq=200,
    delay=0.05
)

solver.add_dynamic_source(source)

# 4. Add a virtual microphone
mic = Listener(pos=[7.0, 7.0])
solver.add_listener(mic)

# 5. Run and visualize
animator = PhysicsAnimator(
    solver=solver,
    total_time=0.1
)

animator.run()

fig = animator.create_animation(skip_frames=5)
fig.show()
```

---

## Example: Extracting a Room Impulse Response

```python
from src.core.domain import Domain2D
from src.solvers.wave import Wave
from src.components.sources import RickerSource
from src.components.listeners import Listener

room = Domain2D(
    length=[8.0, 5.0],
    dx=0.05
)

solver = Wave(
    domain=room,
    c=343.0,
    boundary_type="robin",
    alpha=0.3
)

source = RickerSource(
    pos=[2.0, 2.5],
    peak_freq=500,
    delay=0.02
)

listener = Listener(pos=[6.0, 2.5])

solver.add_dynamic_source(source)
solver.add_listener(listener)

solver.run(total_time=0.5)

impulse_response = listener.signal
```

The resulting signal can be analyzed as a simulated room impulse response.

Possible follow-up analyses include:

- plotting the time-domain response,
- estimating early reflection times,
- comparing different wall absorption coefficients,
- convolving the impulse response with dry audio,
- comparing responses at multiple listener locations.

---

## Example: Directivity Experiment

```python
import numpy as np

from src.components.listeners import Listener

source_position = np.array([5.0, 5.0])
radius = 2.0
n_mics = 36

listeners = []

for i in range(n_mics):
    theta = 2 * np.pi * i / n_mics

    pos = source_position + radius * np.array([
        np.cos(theta),
        np.sin(theta)
    ])

    mic = Listener(pos=pos.tolist())
    solver.add_listener(mic)
    listeners.append(mic)

solver.run(total_time=0.1)

directivity_values = [
    np.max(np.abs(mic.signal))
    for mic in listeners
]
```

The resulting values can be plotted as a polar directivity pattern.

---

## Example: Heat Diffusion

The same domain and solver structure can be used for a non-acoustic PDE.

```python
from src.core.domain import Domain2D
from src.solvers.heat import Heat
from src.utils import utils

domain = Domain2D(
    length=[10.0, 10.0],
    dx=0.05
)

initial_condition = utils.get_initial_gaussian(
    pos=[5.0, 5.0],
    sigma=1.0
)

solver = Heat(
    domain=domain,
    k=1.5,
    initial_u=initial_condition
)

solver.run(total_time=1.0)
```

This example demonstrates how the same `Domain2D` and `PDESolver` abstractions can support different physical models.

---

## Suggested Experiments

The following experiments are currently possible or natural extensions of the existing functionality.

### Room Acoustics

- Compare fully reflective, fully absorptive, and partially absorptive rooms.
- Measure how wall absorption affects reverberation decay.
- Study direct-to-reverberant ratio as a function of source-listener distance.
- Compare impulse responses at different microphone positions.

### Source Radiation

- Compare point sources, dipoles, line sources, and simplified loudspeaker cabinets.
- Estimate source directivity using circular microphone arrays.
- Study interference patterns produced by multiple coherent sources.

### Wave Phenomena

- Simulate diffraction through a double slit.
- Study scattering from internal obstacles.
- Observe standing waves in rectangular rooms.
- Investigate numerical dispersion at different grid resolutions.

### Auralization

- Convolve simulated impulse responses with dry audio.
- Compare perceived differences between room configurations.
- Generate simple stereo renderings using two nearby listeners.
- Use the simulator as a basis for future binaural or spatial-audio experiments.

### Numerical Analysis

- Study stability as a function of the Courant number.
- Compare arrival times with analytical propagation times.
- Validate early reflections against geometric-acoustics predictions.
- Analyze the effect of grid resolution on simulation accuracy.

---

## Roadmap

Planned or possible future improvements:

- [ ] Add documented impulse-response analysis utilities.
- [ ] Add convolution-based auralization examples.
- [ ] Add stereo rendering using two virtual microphones.
- [ ] Add directivity plotting utilities.
- [ ] Add example notebooks for canonical experiments.
- [ ] Add validation against analytical and image-source models.
- [ ] Add frequency-dependent wall absorption.
- [ ] Add source directivity models.
- [ ] Add simple GUI or web interface for interactive experiments.
- [ ] Add binaural rendering using HRTFs.
- [ ] Add Ambisonics-inspired spatial rendering experiments.

---

## Scientific Background

This project is based on classical numerical methods for solving PDEs, especially finite-difference methods applied to the acoustic wave equation.

Relevant topics include:

- acoustic wave propagation,
- finite-difference time-domain methods,
- Courant-Friedrichs-Lewy stability condition,
- room impulse responses,
- boundary conditions,
- diffraction and interference,
- acoustic absorption,
- signal convolution,
- auralization.

---

## Current Limitations

The simulator is intended as an educational and research-prototyping tool, not as a production-grade acoustic simulation package.

Current limitations include:

- simulations are currently focused on 1D/2D domains,
- boundary absorption is simplified,
- material behavior is frequency-independent,
- air absorption is not yet modeled,
- source directivity is approximated through source configurations,
- full binaural rendering is not yet implemented,
- numerical dispersion depends on grid resolution and time-step selection.

These limitations are intentional at the current stage and provide clear directions for future development.

---

## Why This Project Matters

This project aims to connect physical modeling and listening-oriented audio applications.

It is not only about visualizing waves. It is about building a bridge from:

```text
Wave equation
→ numerical simulation
→ room impulse response
→ acoustic analysis
→ auralization
→ spatial audio
```

This makes the project relevant to:

- numerical acoustics,
- room acoustics,
- architectural acoustics,
- audio signal processing,
- musical acoustics,
- spatial audio,
- computational sound design.

---

## License

This project is released for educational and research purposes.

Please see the repository license for details.

---

## Author

Developed by Gabriel Fiúza as part of an ongoing transition toward computational acoustics, audio signal processing, and music technology.
