import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
import io
from datetime import datetime, date, timedelta
from matplotlib import font_manager


def set_xaxis_interval(gap): #using the gap between 1st vol and the latest
    if gap <= 12:
        interval = 1
    elif gap <= 24:
        interval = 2
    elif gap <= 48:
        interval = 3
    else:
        interval = 6
    return interval

def months_between_vols(d1, d2):
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)

def generate_graph(vol_rel_dates, predict, title, vol_title):

    jp_vols, jp_dates = zip(*[(vol, dates) for vol, dates in vol_rel_dates.items()])
    title = title if len(title)<90 else title[:90]+"....."

    dates = vol_rel_dates.values()
    total_months = months_between_vols(min(dates), max(dates)) + 1
    interval = set_xaxis_interval(total_months)

    gaps_in_months = [months_between_vols(jp_dates[i], jp_dates[i+1]) for i in range(len(jp_dates) - 1)]
    avg_gap_months = sum(gaps_in_months) / len(gaps_in_months)


    # Had to do this because titles weren't being displayed properly
    font_path_regular = "./fonts/NotoSansCJK-Regular.ttc"
    jp_font_regular = font_manager.FontProperties(fname=font_path_regular)
    font_path_bold = "./fonts/NotoSansCJK-Bold.ttc"
    jp_font_bold = font_manager.FontProperties(fname=font_path_bold)

    plt.style.use('dark_background')
    fig_width =  min(30, max(16, len(jp_vols) * 0.4))
    fig, ax = plt.subplots(figsize=(fig_width, 6))
    fig.patch.set_facecolor('#1e1e1e')  # dark gray background for the figure
    ax.set_facecolor('#1e1e1e')         # dark gray background for the plot area
    ax.yaxis.grid(True, color='white', linestyle='-', alpha=0.3)
    ax.xaxis.grid(False)  # turn off vertical grid lines
    ax.plot(jp_dates, jp_vols, label="JP", color="#6c5ce7", marker="o")
    if predict:
        gaps = [(jp_dates[i+1] - jp_dates[i]).days for i in range(len(jp_dates) - 1)]
        avg_gap = sum(gaps) / len(gaps)
        predicted_date = jp_dates[-1] + timedelta(days=avg_gap)
        if predicted_date < datetime.today().date():
            predicted_date = datetime.today().date()
        predicted_vol = jp_vols[-1]+1
        ax.plot([jp_dates[-1], predicted_date], [jp_vols[-1], predicted_vol],
            linestyle='dotted', color='#6c5ce7', label='Predicted Next Vol')
        plt.scatter(predicted_date, predicted_vol, edgecolors='gray', facecolors='none')
        ax.axvline(datetime.today(), color="red", linewidth=2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %y'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=interval))
    fig.autofmt_xdate(rotation=45)

    for spine in ['left', 'top', 'right']:
        ax.spines[spine].set_visible(False)
    ax.spines['bottom'].set_color('gray')

    ax.tick_params(axis='y', which='both', length=0, pad=10)
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))  # integer volume numbers only

    plt.subplots_adjust(
        left=0.07,
        right=0.98,
        top=0.93,
        bottom=0.32
    )

    ax.set_title(title, fontproperties=jp_font_bold, fontsize=14)
    ax.set_xlabel("Date Published", fontsize=12, labelpad=8)
    ax.set_ylabel("Volumes", fontsize=12, labelpad=6)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.25), ncols=3, frameon=False)
    fig.text(0.05, 0.1, f'‣ Average Monthly Gap —— JP: {avg_gap_months:.2f}',
            ha='left', va='bottom', fontsize=10)
    fig.text(0.05, 0.05, f'- Latest Release ——  JP:  {vol_title}',
            ha='left', va='bottom', fontsize=10, fontproperties=jp_font_regular)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=300)
    buf.seek(0)
    plt.close(fig)

    return buf