import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Figure style
sns.set_theme(style="whitegrid", context="talk")

data_file = "data/combined_stations_era5_CA_2019_2024_features.csv"

df = pd.read_csv(data_file)
print("Loaded dataset:", df.shape)

# Mark rows with fog/mist data available
df['has_fog_mist_data'] = df['fog_occurrence'].notna()

# Calculate monthly completeness
monthly_completeness = (
    df.groupby(['station', 'year_local', 'month_local'])
    .agg(
        hours_available=('has_fog_mist_data', 'size'),
        hours_with_data=('has_fog_mist_data', 'sum')
    )
    .reset_index()
)
monthly_completeness['completeness'] = (
    monthly_completeness['hours_with_data'] / monthly_completeness['hours_available']
)

# STRICT CRITERIA: Require exactly 12 months AND all ≥90% complete
monthly_completeness['month_ok'] = monthly_completeness['completeness'] >= 0.90

valid_years = (
    monthly_completeness.groupby(['station', 'year_local'])
    .agg(
        months_present=('month_local', 'count'),
        all_months_pass_90=('month_ok', 'all')
    )
    .reset_index()
)
valid_years['meets_strict_criteria'] = (
    (valid_years['months_present'] == 12) & 
    (valid_years['all_months_pass_90'])
)
valid_years = valid_years[valid_years['meets_strict_criteria']][['station', 'year_local']]

print(f"\nSTRICT CRITERIA APPLIED:")
print(f"Total station-years passing criteria: {len(valid_years)}")
print(f"Total stations passing criteria: {valid_years['station'].nunique()}")

# Filter original dataframe to only valid station-years
df = df.merge(valid_years, on=['station', 'year_local'], how='inner')

# Add fog flag to full valid dataframe
df["fog_flag"] = (df["fog_occurrence"] == "yes") | (df["mist_occurrence"] == "yes")

# ------------------------------
# Hourly fog frequency per year
fog_hour_year = (
    df.groupby(["year_local", "hour_local"])
    .agg(
        fog_count  =("fog_flag",         "sum"),
        total_hours=("has_fog_mist_data", "sum"),
    )
    .reset_index()
)
fog_hour_year["frequency"] = fog_hour_year["fog_count"] / fog_hour_year["total_hours"] * 100

# ------------------------------
# Monthly fog frequency per year
fog_month_year = (
    df.groupby(["year_local", "month_local"])
    .agg(
        fog_count  =("fog_flag",         "sum"),
        total_hours=("has_fog_mist_data", "sum"),
    )
    .reset_index()
)
fog_month_year["frequency"] = fog_month_year["fog_count"] / fog_month_year["total_hours"] * 100

# FINAL FIGURE: Hourly fog frequency per year + Monthly fog frequency per year

fig, axes = plt.subplots(2, 1, figsize=(12, 12))

# ----------------------------------------------------
# PANEL A — Hourly fog frequency per year
sns.lineplot(
    data=fog_hour_year,
    x="hour_local",
    y="frequency",
    hue="year_local",
    marker="o",
    linewidth=1.8,
    palette="colorblind",
    ax=axes[0]
)

axes[0].set_title("A. Fog Frequency by Hour of Day per Year", fontsize=18)
axes[0].set_xlabel("Hour of Day")
axes[0].set_ylabel("Fog Frequency (% of hours with fog)")
axes[0].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}%"))
axes[0].set_xticks(range(0,24))
axes[0].set_ylim(0, fog_hour_year["frequency"].max() * 1.15)
axes[0].legend(title="Year", bbox_to_anchor=(1.02, 1), loc="upper left")

# ----------------------------------------------------
# PANEL B — Monthly fog frequency per year
sns.lineplot(
    data=fog_month_year,
    x="month_local",
    y="frequency",
    hue="year_local",
    marker="o",
    linewidth=1.8,
    palette="colorblind",
    ax=axes[1]
)

axes[1].set_title("B. Fog Frequency by Month per Year", fontsize=18)
axes[1].set_xlabel("Month")
axes[1].set_ylabel("Fog Frequency (% of hours with fog)")
axes[1].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}%"))
axes[1].set_xticks(range(1, 13))
axes[1].set_xticklabels(["Jan","Feb","Mar","Apr","May","Jun",
                          "Jul","Aug","Sep","Oct","Nov","Dec"])
axes[1].set_ylim(0, fog_month_year["frequency"].max() * 1.15)
axes[1].legend(title="Year", bbox_to_anchor=(1.02, 1), loc="upper left")

# ----------------------------------------------------
plt.tight_layout()

fig.savefig(
    "figure_2.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()
plt.close()

print("✓ Saved: figure_2.png")
