import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib import ticker, colors
from typing import Tuple, Union, List, Optional
import attr

DARK24 = [
    "#2E91E5",
    "#E15F99",
    "#1CA71C",
    "#FB0D0D",
    "#DA16FF",
    "#222A2A",
    "#B68100",
    "#750D86",
    "#EB663B",
    "#511CFB",
    "#00A08B",
    "#FB00D1",
    "#FC0080",
    "#B2828D",
    "#6C7C32",
    "#778AAE",
    "#862A16",
    "#A777F1",
    "#620042",
    "#1616A7",
    "#DA60CA",
    "#6C4516",
    "#0D2A63",
    "#AF0038",
]


# def output_animation(chart: Union[_BarChartRace,_LineChartRace]):
#     def wrap_function():
#         anim = chart.make_animation()
#         extension = chart.filename.split(".")[-1]
#         if extension == "gif":
#             anim.save(chart.filename, fps=chart.fps, writer="imagemagick")
#         else:
#             anim.save(chart.filename, fps=chart.fps)


@attr.s
class BaseChart:
    df: pd.DataFrame = attr.ib()
    use_index: bool = attr.ib()
    steps_per_period: int = attr.ib()
    period_length: int = attr.ib()
    figsize: Tuple[float, float] = attr.ib()
    title: str = attr.ib()
    fig: plt.Figure = attr.ib()

    def validate_params(self) -> None:
        if self.fig is not None and not isinstance(self.fig, plt.Figure):
            raise TypeError("`fig` must be a matplotlib Figure instance")

    def anim_func(self, frame):
        raise NotImplementedError("Animation function not yet implemented")

    def make_animation(self, frames, init_func) -> FuncAnimation:

        interval = self.period_length / self.steps_per_period
        return FuncAnimation(
            self.fig, self.anim_func, frames, init_func, interval=interval,
        )

    def get_data_cols(self) -> List[str]:
        data_cols = []
        for i, col in enumerate(self.df.columns):
            if col not in self.df.columns:
                raise Exception(
                    "Could not find '%s' in the columns of the provided DataFrame/Series. Please provide for the <y> parameter either a column name of the DataFrame/Series or an array of the same length."
                    % col
                )
            if np.issubdtype(self.df[col].dtype, np.number):
                data_cols.append(col)
        if not data_cols:
            raise Exception("No numeric data columns found for plotting.")
        
        data_cols = [str(col) for col in data_cols]

        return data_cols

    def get_colors(self, cmap):
        if isinstance(cmap, str):
            cmap = DARK24 if cmap == "dark24" else plt.cm.get_cmap(cmap)
        if isinstance(cmap, colors.Colormap):
            chart_colors = cmap(range(cmap.N)).tolist()
        elif isinstance(cmap, list):
            chart_colors = cmap
        elif hasattr(cmap, "tolist"):
            chart_colors = cmap.tolist()
        else:
            raise TypeError(
                "`cmap` must be a string name of a colormap, a matplotlib colormap instance"
                "or a list of colors"
            )

        return chart_colors


@attr.s
class BarChart(BaseChart):
    orientation: str = attr.ib()
    sort: str = attr.ib()
    n_bars: int = attr.ib()
    label_bars: bool = attr.ib()
    cmap: Union[str, colors.Colormap, List[str]] = attr.ib()
    bar_label_size: Union[int, float] = attr.ib()
    tick_label_size: Union[int, float] = attr.ib()
    period_label_size: Union[int, float] = attr.ib()
    kwargs = attr.ib()

    def __attrs_post_init__(self):
        self.n_bars = self.n_bars or self.df.shape[1]
        self.df_values, self.df_rank = self.prepare_data()
        self.orig_index = self.df.index.astype("str")
        self.dpi = 144
        self.fps = 1000 / self.period_length * self.steps_per_period
        if self.fig is None:
            self.fig, self.ax = self.create_figure()
        self.x_label, self.y_label = self.get_label_position()
        self.bar_colors = self.get_colors(self.cmap)

    def validate_params(self):
        super().validate_params()

        if self.sort not in ("asc", "desc"):
            raise ValueError('`sort` must be "asc" or "desc"')

        if self.orientation not in ("h", "v"):
            raise ValueError('`orientation` must be "h" or "v"')

    def get_colors(self, cmap):
        bar_colors = super().get_colors(cmap)
        # bar_colors is now a list
        n = len(bar_colors)
        if self.df.shape[1] > n:
            bar_colors = bar_colors * (self.df.shape[1] // n + 1)
        return np.array(bar_colors[: self.df.shape[1]])

    def get_label_position(self):
        if self.orientation == "h":
            x_label = 0.6
            y_label = 0.25 if self.sort == "desc" else 0.8
        else:
            x_label = 0.7 if self.sort == "desc" else 0.1
            y_label = 0.8
        return x_label, y_label

    def prepare_data(self):
        df_values = self.df.reset_index(drop=True)
        df_values.index = df_values.index * self.steps_per_period
        df_rank = df_values.rank(axis=1, method="first", ascending=False).clip(
            upper=self.n_bars + 1
        )
        if (self.sort == "desc" and self.orientation == "h") or (
            self.sort == "asc" and self.orientation == "v"
        ):
            df_rank = self.n_bars + 1 - df_rank
        new_index = range(df_values.index.max() + 1)
        df_values = df_values.reindex(new_index).interpolate()
        df_rank = df_rank.reindex(new_index).interpolate()
        return df_values, df_rank

    def create_figure(self):
        fig = plt.Figure(figsize=self.figsize, dpi=self.dpi)
        limit = (0.2, self.n_bars + 0.8)
        rect = self.calculate_new_figsize(fig)
        ax = fig.add_axes(rect)
        if self.orientation == "h":
            ax.set_ylim(limit)
            ax.grid(True, axis="x", color="white")
            ax.xaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
        else:
            ax.set_xlim(limit)
            ax.grid(True, axis="y", color="white")
            ax.set_xticklabels(ax.get_xticklabels(), ha="right", rotation=30)
            ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))

        ax.set_axisbelow(True)
        ax.tick_params(length=0, labelsize=self.tick_label_size, pad=2)
        ax.set_facecolor(".9")
        ax.set_title(self.title)
        for spine in ax.spines.values():
            spine.set_visible(False)
        return fig, ax

    def calculate_new_figsize(self, real_fig):
        import io

        # df_values = self.prepare_data()
        fig = plt.Figure(tight_layout=True, figsize=self.figsize)
        ax = fig.add_subplot()
        fake_cols = [chr(i + 70) for i in range(self.df.shape[1])]

        max_val = self.df_values.max().max()
        if self.orientation == "h":
            ax.barh(fake_cols, [1] * self.df.shape[1])
            ax.tick_params(labelrotation=0, axis="y", labelsize=self.tick_label_size)
            ax.set_title(self.title)
            fig.canvas.print_figure(io.BytesIO())
            orig_pos = ax.get_position()
            ax.set_yticklabels(self.df.columns)
            ax.set_xticklabels([max_val] * len(ax.get_xticks()))
        else:
            ax.bar(fake_cols, [1] * self.df.shape[1])
            ax.tick_params(labelrotation=30, axis="x", labelsize=self.tick_label_size)
            ax.set_title(self.title)
            fig.canvas.print_figure(io.BytesIO())
            orig_pos = ax.get_position()
            ax.set_xticklabels(self.df.columns, ha="right")
            ax.set_yticklabels([max_val] * len(ax.get_yticks()))

        fig.canvas.print_figure(io.BytesIO(), format="png")
        new_pos = ax.get_position()

        coordx, prev_coordx = new_pos.x0, orig_pos.x0
        coordy, prev_coordy = new_pos.y0, orig_pos.y0
        old_w, old_h = self.figsize

        # if coordx > prev_coordx or coordy > prev_coordy:
        prev_w_inches = prev_coordx * old_w
        total_w_inches = coordx * old_w
        extra_w_inches = total_w_inches - prev_w_inches
        new_w_inches = extra_w_inches + old_w

        prev_h_inches = prev_coordy * old_h
        total_h_inches = coordy * old_h
        extra_h_inches = total_h_inches - prev_h_inches
        new_h_inches = extra_h_inches + old_h

        real_fig.set_size_inches(new_w_inches, new_h_inches)
        left = total_w_inches / new_w_inches
        bottom = total_h_inches / new_h_inches
        width = orig_pos.x1 - left
        height = orig_pos.y1 - bottom
        return [left, bottom, width, height]

    def plot_bars(self, i):
        bar_location = self.df_rank.iloc[i].values
        top_filt = (bar_location > 0) & (bar_location < self.n_bars + 1)
        bar_location = bar_location[top_filt]
        bar_length = self.df_values.iloc[i].values[top_filt]
        cols = self.df.columns[top_filt]
        colors = self.bar_colors[top_filt]
        if self.orientation == "h":
            self.ax.barh(
                bar_location,
                bar_length,
                ec="white",
                tick_label=cols,
                color=colors,
                **self.kwargs,
            )
            self.ax.set_xlim(self.ax.get_xlim()[0], bar_length.max() * 1.1)
        else:
            self.ax.bar(
                bar_location,
                bar_length,
                ec="white",
                tick_label=cols,
                color=colors,
                **self.kwargs,
            )
            self.ax.set_ylim(self.ax.get_ylim()[0], bar_length.max() * 1.16)

        if self.use_index:
            val = self.orig_index[i // self.steps_per_period]
            num_texts = len(self.ax.texts)
            if num_texts == 0:
                self.ax.text(
                    self.x_label,
                    self.y_label,
                    val,
                    transform=self.ax.transAxes,
                    fontsize=self.period_label_size,
                )
            else:
                self.ax.texts[0].set_text(val)

        if self.label_bars:
            for text in self.ax.texts[int(self.use_index) :]:
                text.remove()
            if self.orientation == "h":
                zipped = zip(bar_length, bar_location)
            else:
                zipped = zip(bar_location, bar_length)

            for x1, y1 in zipped:
                xtext, ytext = self.ax.transLimits.transform((x1, y1))
                if self.orientation == "h":
                    xtext += 0.01
                    text = f"{x1:,.0f}"
                    rotation = 0
                    ha = "left"
                    va = "center"
                else:
                    ytext += 0.015
                    text = f"{y1:,.0f}"
                    rotation = 90
                    ha = "center"
                    va = "bottom"
                xtext, ytext = self.ax.transLimits.inverted().transform((xtext, ytext))
                self.ax.text(
                    xtext,
                    ytext,
                    text,
                    ha=ha,
                    rotation=rotation,
                    fontsize=self.bar_label_size,
                    va=va,
                )

    def anim_func(self, i):
        for bar in self.ax.containers:
            bar.remove()
        self.plot_bars(i)

    def init_func(self):
        self.plot_bars(0)

    def get_frames(self):
        return range(len(self.df_values))

    def make_animation(self, filename):

        anim = super().make_animation(self.get_frames(), self.init_func)

        # if self.html:
        #     return anim.to_html5_video()

        extension = filename.split(".")[-1]
        if extension == "gif":
            anim.save(filename, fps=self.fps, writer="imagemagick")
        else:
            anim.save(filename, fps=self.fps)

@attr.s
class LineChart(BaseChart):
    line_width: int = attr.ib()
    _xdata: List = attr.ib(default=[])
    _ydata: List = attr.ib(default=[])
    
    def __attrs_post_init__(self):
        self.data_cols = self.get_data_cols()
        if self.fig is not None:
            self.fig, self.ax = self.fig, self.fig.axes[0]
            self.figsize = self.fig.get_size_inches()
            self.dpi = self.fig.dpi
        else:
            self.fig = plt.figure()
            self.ax = plt.axes()

    def plot_line(self, i):
        self.ax.set_xlim(self.series.index.min(), self.series.index.max())
        self.ax.set_ylim((self.series.min(), self.series.max()))
        self.xdata.append(self.series.index[i])
        self.ydata.append(self.series.iloc[i])
        self.ax.plot(self.xdata, self.ydata, self.line_width)
        # return self.line

    def anim_func(self, i):
        for line in self.ax.lines:
            line.remove()
        self.plot_line(i)

    def init_func(self) -> None:
        self.ax.plot([], [], self.line_width)

    def get_frames(self):
        return range(len(self.series))

    def make_animation(self):

        # self.line.set_data([],[])

        anim = super().make_animation(self.get_frames(), self.init_func)

        extension = self.filename.split(".")[-1]
        if extension == "gif":
            anim.save(self.filename, fps=self.fps, writer="imagemagick")
        else:
            anim.save(self.filename, fps=self.fps)



def animate_multiple_plots(filename: str, plots: List[Union[BarChart]]):
    """ Plot multiple animated plots

    Args:
        plots (List[Union[_BarChartRace,_LineChartRace]]): List of plots to animate
    """

    def update_all_graphs(frame):
        for plot in plots:
            plot.anim_func(frame)

    fig, axes = plt.subplots(len(plots))
    for num, plot in enumerate(plots):
        plot.ax = axes[num]

        plot.init_func()

    interval = plots[0].period_length / plots[0].steps_per_period
    anim = FuncAnimation(
        fig,
        update_all_graphs,
        min([max(plot.get_frames()) for plot in plots]),
        # plots[0].get_frames(),
        # init_func,
        interval=interval,
    )

    extension = filename.split(".")[-1]
    if extension == "gif":
        anim.save(filename, fps=plots[0].fps, writer="imagemagick")
    else:
        anim.save(filename, fps=plots[0].fps)

# if __name__ == "__main__":
#     # import pandas as pd
#     # df = pd.read_csv(
#     #     f"data/covid19.csv",
#     #     index_col="date",
#     #     parse_dates=["date"],
#     # )

#     # print(df.plot)

