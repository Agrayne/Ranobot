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

def generate_graph(vol_rel_dates_jp, vol_rel_dates_en, predict, title, latest_vol_jp, latest_vol_en):

    title = title if len(title)<90 else title[:90]+"....."

    dates_jp = vol_rel_dates_jp.values()
    total_months_jp = months_between_vols(min(dates_jp), max(dates_jp)) + 1
    interval = set_xaxis_interval(total_months_jp)

    jp_vols, jp_dates = zip(*[(vol, dates) for vol, dates in vol_rel_dates_jp.items()])

    gaps_bw_months_jp = [months_between_vols(jp_dates[i], jp_dates[i+1]) for i in range(len(jp_dates) - 1)]
    avg_gap_months_jp = sum(gaps_bw_months_jp) / len(gaps_bw_months_jp)

    en_plot = False
    en_predict = False
    avg_gap_months_en = 0
    if vol_rel_dates_en:
        en_plot = True
        en_vols, en_dates = zip(*[(vol, dates) for vol, dates in vol_rel_dates_en.items()])
        if len(vol_rel_dates_en) > 1:
            en_predict = True
            gaps_bw_months_en = [months_between_vols(en_dates[i], en_dates[i+1]) for i in range(len(en_dates) - 1)]
            avg_gap_months_en = sum(gaps_bw_months_en) / len(gaps_bw_months_en)

    # Had to do this because titles weren't being displayed properly
    ### Need to remember to remove this from the git repo
    font_path_regular = "./fonts/NotoSansCJK-Regular.ttc"
    jp_font_regular = font_manager.FontProperties(fname=font_path_regular)
    font_path_bold = "./fonts/NotoSansCJK-Bold.ttc"
    jp_font_bold = font_manager.FontProperties(fname=font_path_bold)
    #### Remove the above before running if you are self-hosting ####

    plt.style.use('dark_background')
    fig_width =  min(30, max(16, len(jp_vols) * 0.4))
    fig, ax = plt.subplots(figsize=(fig_width, 6))
    fig.patch.set_facecolor('#1e1e1e')  # dark gray background for the figure
    ax.set_facecolor('#1e1e1e')         # dark gray background for the plot area
    ax.yaxis.grid(True, color='white', linestyle='-', alpha=0.3)
    ax.xaxis.grid(False)
    ax.plot(jp_dates, jp_vols, label="JP", color="#6c5ce7", marker="o")
    if en_plot:
        ax.plot(en_dates, en_vols, label="EN", color="#50ac00", marker="o")
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
        if en_predict:
            gaps_en = [(en_dates[i+1] - en_dates[i]).days for i in range(len(en_dates) - 1)]
            avg_gap_en = sum(gaps_en) / len(gaps_en)
            predicted_date_en = en_dates[-1] + timedelta(days=avg_gap_en)
            if predicted_date_en < datetime.today().date():
                predicted_date_en = datetime.today().date()
            predicted_vol_en = en_vols[-1]+1
            ax.plot([en_dates[-1], predicted_date_en], [en_vols[-1], predicted_vol_en],
                linestyle='dotted', color='#50ac00', label='Predicted Next Vol EN')
            plt.scatter(predicted_date_en, predicted_vol_en, edgecolors='gray', facecolors='none')
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
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.25), ncols=4, frameon=False)
    fig.text(0.05, 0.1, f'‣ Average Monthly Gap —— JP: {avg_gap_months_jp:.2f} | EN: {avg_gap_months_en:.2f}',
            ha='left', va='bottom', fontsize=10)
    fig.text(0.05, 0.05, f'- Latest Release ——  JP:    {latest_vol_jp}   |   EN:  {latest_vol_en}',
            ha='left', va='bottom', fontsize=10, fontproperties=jp_font_regular)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=300)
    buf.seek(0)
    plt.close(fig)

    return buf