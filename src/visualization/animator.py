from typing import Optional, List, Any
import numpy as np
import plotly.graph_objects as go

from src.core.pdesolver import PDESolver


class PhysicsAnimator:
    """
    Interactive visualization for 1D and 2D FDTD simulations.
    
    Runs the physics loop and generates Plotly animations with
    automatic axis scaling and listener markers.
    
    Parameters
    ----------
    solver : PDESolver
        Configured solver instance (Heat or Wave).
    total_time : float
        Total simulation duration in seconds.
    
    Attributes
    ----------
    solver : PDESolver
        Reference to the PDE solver.
    total_time : float
        Simulation duration.
    history : list of np.ndarray
        Stored field snapshots.
    time_steps : list of float
        Corresponding time values.
    x_axis : np.ndarray
        X-coordinate array for plotting.
    y_axis : np.ndarray or None
        Y-coordinate array (2D only).
    """

    def __init__(self, solver: PDESolver, total_time: float) -> None:
        self.solver = solver
        self.total_time = total_time
        
        self.history: List[np.ndarray] = []
        self.time_steps: List[float] = []
        
        if self.solver.domain.ndim == 1:
            self.x_axis = np.linspace(0, self.solver.domain.L[0], self.solver.domain.N[0])
            self.y_axis: Optional[np.ndarray] = None
        
        elif self.solver.domain.ndim == 2:
            self.x_axis = np.linspace(0, self.solver.domain.L[0], self.solver.domain.N[0])
            self.y_axis = np.linspace(0, self.solver.domain.L[1], self.solver.domain.N[1])

    def run(self) -> None:
        """
        Execute the simulation and store field history.
        
        Advances the solver for the specified duration, storing
        snapshots at each time step with boundary points masked as NaN.
        """
        t = 0.0
        steps = int(self.total_time / self.solver.dt)
        
        print(f"Simulating {self.total_time}s of physics ({steps} steps) in {self.solver.domain.ndim}D...")
        
        for _ in range(steps):
            self.solver.step()
            
            u_curr = np.array(self.solver.u_curr)
            u_curr[~self.solver.domain.mask] = np.nan
            self.history.append(u_curr)
            self.time_steps.append(t)
            t += self.solver.dt
            
        print("Simulation complete.")

    def create_animation(
        self,
        skip_frames: int = 10,
        skip_spatial: int = 5,
        filename: Optional[str] = None
    ) -> Optional[go.Figure]:
        """
        Generate an interactive Plotly animation.
        
        Parameters
        ----------
        skip_frames : int, default=10
            Temporal subsampling factor.
        skip_spatial : int, default=5
            Spatial subsampling factor for 2D plots.
        filename : str, optional
            If provided, saves the animation as an HTML file.
        
        Returns
        -------
        go.Figure or None
            Plotly figure with animation controls, or None if no data.
        """
        if not self.history:
            print("No data! Run .run() first.")
            return None

        display_data = self.history[::skip_frames]
        s_slice = slice(None, None, skip_spatial)
        
        stack = np.array(display_data)
        global_min = np.nanmin(stack)
        global_max = np.nanmax(stack)
        
        if global_max == global_min:
            global_max += 1.0
            global_min -= 1.0
            print("Warning: Simulation appears to be flat (min == max).")
        else:
            print(f"Dynamic Scale Found: [{global_min:.2e}, {global_max:.2e}]")

        padding = (global_max - global_min) * 0.1
        z_limits = [global_min - padding, global_max + padding]

        listeners = getattr(self.solver.domain, 'listeners', [])
        has_listeners = len(listeners) > 0

        frames: List[go.Frame] = []
        initial_data: List[Any] = []
        layout_settings: go.Layout

        print(f'Animating {len(display_data)} frames (Spatial stride: {skip_spatial})...')

        def process(frame: np.ndarray) -> np.ndarray:
            if self.solver.domain.ndim == 1:
                return frame[s_slice]
            return frame.T[s_slice, s_slice]

        if self.solver.domain.ndim == 1:
            x_plot_1d = self.x_axis[s_slice]
            initial_data.append(go.Scatter(
                x=x_plot_1d, y=process(display_data[0]), mode="lines", name="Wave",
                line=dict(color='royalblue', width=2)
            ))
            
            if has_listeners:
                l_x = [l.pos[0] for l in listeners]
                l_y = [display_data[0][l.grid_idx] for l in listeners]
                initial_data.append(go.Scatter(
                    x=l_x, y=l_y, mode="markers", name="Listener",
                    marker=dict(color='red', size=12, symbol='x')
                ))
            
            layout_settings = go.Layout(
                title=f"1D Simulation (Range: {global_min:.2e} to {global_max:.2e})",
                xaxis=dict(title="Position (m)", range=[0, self.solver.domain.L[0]]),
                yaxis=dict(title="Amplitude", range=z_limits),
                template="plotly_white"
            )

            for i, raw_frame in enumerate(display_data):
                frame_data = [go.Scatter(x=x_plot_1d, y=process(raw_frame))]
                if has_listeners:
                    l_y_new = [raw_frame[l.grid_idx] for l in listeners]
                    frame_data.append(go.Scatter(x=l_x, y=l_y_new))
                frames.append(go.Frame(data=frame_data, name=f"f{i}"))

        elif self.solver.domain.ndim == 2:
            x_plot = self.x_axis[s_slice]
            y_plot = self.y_axis[s_slice]

            initial_data.append(go.Surface(
                x=x_plot, y=y_plot, z=process(display_data[0]),
                colorscale='viridis',
                cmin=global_min, cmax=global_max,
                name="Wave"
            ))
            
            if has_listeners:
                l_x = [l.pos[0] for l in listeners]
                l_y = [l.pos[1] for l in listeners]
                l_z = [display_data[0][l.grid_idx] for l in listeners]
                
                initial_data.append(go.Scatter3d(
                    x=l_x, y=l_y, z=l_z, mode="markers", name="Listener",
                    marker=dict(color='red', size=5, symbol='circle')
                ))

            # Calculate aspect ratio from domain dimensions
            aspect_x = self.solver.domain.L[0]
            aspect_y = self.solver.domain.L[1]
            aspect_norm = min(aspect_x, aspect_y)
            aspect_ratio = dict(
                x=aspect_x / aspect_norm,
                y=aspect_y / aspect_norm,
                z=0.7
            )
            
            layout_settings = go.Layout(
                title=f"2D Simulation (Range: {global_min:.2e} to {global_max:.2e})",
                scene=dict(
                    xaxis=dict(title='X'),
                    yaxis=dict(title='Y'),
                    zaxis=dict(title='Amplitude', range=z_limits),
                    aspectratio=aspect_ratio
                ),
                template="plotly_white"
            )

            for i, raw_frame in enumerate(display_data):
                frame_data = [go.Surface(z=process(raw_frame))]
                if has_listeners:
                    l_z_new = [raw_frame[l.grid_idx] for l in listeners]
                    l_x = [l.pos[0] for l in listeners]
                    l_y = [l.pos[1] for l in listeners]
                    frame_data.append(go.Scatter3d(x=l_x, y=l_y, z=l_z_new))
                frames.append(go.Frame(data=frame_data, name=f"f{i}"))

        updatemenus = [dict(
            type="buttons", showactive=False,
            x=0.1, y=0, xanchor="right", yanchor="top", pad=dict(t=0, r=10),
            buttons=[
                dict(label="▶ Play", method="animate",
                     args=[None, dict(frame=dict(duration=20, redraw=True), fromcurrent=True)]),
                dict(label="|| Pause", method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate", transition=dict(duration=0))]),
                dict(label="⟲ Restart", method="animate",
                     args=[["f0"], dict(frame=dict(duration=0, redraw=True), mode="immediate", transition=dict(duration=0))])
            ]
        )]

        layout_settings.updatemenus = updatemenus
        fig = go.Figure(data=initial_data, layout=layout_settings)
        fig.frames = frames

        if filename:
            fig.write_html(filename)
            print(f"Animation saved to {filename}")
        
        return fig

    def save_gif(self, filename: str = "animation.gif", skip_frames: int = 10, fps: int = 20, dpi: int = 100) -> None:
        """
        Save the simulation history as a GIF file.

        Parameters
        ----------
        filename : str
            Output path, e.g. 'assets/img/wave.gif'.
        skip_frames : int, default=10
            Temporal subsampling factor.
        fps : int, default=20
            Frames per second in the output GIF.
        dpi : int, default=100
            Output resolution.
        """
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation

        frames = self.history[::skip_frames]
        times = self.time_steps[::skip_frames]

        vmax = np.nanpercentile(np.abs(frames), 99) or 1.0

        domain = self.solver.domain
        sources = getattr(domain, 'sources', [])
        listeners = getattr(domain, 'listeners', [])

        fig, ax = plt.subplots(figsize=(6, 5))
        im = ax.imshow(
            frames[0].T, origin='lower', aspect='equal',
            cmap='RdBu_r', vmin=-vmax, vmax=vmax,
            extent=[0, domain.L[0], 0, domain.L[1]]
        )
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")
        title = ax.set_title(f"t = {times[0]:.3f} s")
        plt.colorbar(im, ax=ax, label="Pressure")

        for src in sources:
            ax.plot(src.pos[0], src.pos[1], marker='*', color='yellow',
                    markersize=10, markeredgecolor='black', markeredgewidth=0.5,
                    linestyle='None', label='Source', zorder=5)

        for lst in listeners:
            ax.plot(lst.pos[0], lst.pos[1], marker='v', color='cyan',
                    markersize=7, markeredgecolor='black', markeredgewidth=0.5,
                    linestyle='None', label='Listener', zorder=5)

        if sources or listeners:
            handles, labels = ax.get_legend_handles_labels()
            by_label = dict(zip(labels, handles))
            ax.legend(by_label.values(), by_label.keys(), loc='upper right', fontsize=7)

        def update(i):
            im.set_data(frames[i].T)
            title.set_text(f"t = {times[i]:.3f} s")
            return [im, title]

        anim = animation.FuncAnimation(fig, update, frames=len(frames), interval=1000 // fps, blit=True)
        anim.save(filename, writer="pillow", fps=fps, dpi=dpi)
        plt.close(fig)
        print(f"GIF saved to {filename}")

    def reset(self) -> None:
        """
        Clear simulation history and reset for a fresh run.
        
        Clears stored snapshots and time steps, allowing you to call
        run() again without accumulating frames. Note: This does NOT
        reset the solver's internal state (u_curr, u_prev).
        """
        self.history.clear()
        self.time_steps.clear()
        print("Animation history cleared. You can call run() again.")