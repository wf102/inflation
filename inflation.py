import yaml
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from io import StringIO

DIR = "data"
filename = "salary.yaml"
index = "CPI"

def get_inflation_df(index):
    """Get the inflation time series from the ONS website."""

    ons_codes = {
        "CPIH": "l522",
        "CPI": "d7bt",
        "RPI": "chaw"
    }

    if index not in ons_codes:
        raise ValueError(f'Index is not a valid inflation measure. Must be in {list(ons_codes.keys())}')

    # Consumer price inflation time series (MM23).
    url = (f"https://www.ons.gov.uk/generator?format=csv&uri=/economy/inflationandpriceindices/timeseries/{ons_codes[index]}/mm23")

    r = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    r.raise_for_status()

    df = pd.read_csv(StringIO(r.text), names=("date", "index"), skiprows=1)

    regex = r"^\d{4}\s[A-Za-z]{3}$"
    df = df[df["date"].str.match(regex)]

    df["date"] = pd.to_datetime(df["date"], format="%Y %b")
    df['index'] = pd.to_numeric(df['index'])

    return df.set_index("date")


# Get inflation data in data frame

df = get_inflation_df(index)
df["value"] = df.loc[df.index[-1], "index"] / df["index"]


# Get quantity data in data frame

with open(f"{DIR}/{filename}") as f:
    config = yaml.safe_load(f)

name = config["name"]
units = config.get("units", "")
values = config["values"]

df_quant = pd.DataFrame(values.items(), columns=["date", "quantity"])
df_quant["date"] = pd.to_datetime(df_quant["date"], format="%d-%m-%Y")

df_quant = df_quant.set_index("date")


# Join quantity data to inflation data (forward filling missing values)

df = df.join(df_quant).ffill()
# Calculate real value in today's money
df["quantity_real"] = df["quantity"] * df["value"]


# Generate plot

upper_range = 1.2 * df["quantity_real"].max()
n_lines = 40
units_string = f"({units})" if units else ""
first_date = df["quantity"].first_valid_index()
plot_dir = "plots"

plt.rc('font', size=12)

fig, ax = plt.subplots(figsize=(12, 8))

for i in np.arange(0, upper_range, upper_range/n_lines):
    ax.plot(df.index, i * df["value"], color="gainsboro", linewidth=1.0)

ax.plot(df.index, df["quantity"], color="grey", label="Nominal")
ax.plot(df.index, df["quantity_real"], color="black", label="Real")

ax.set_title(f"{name.capitalize()} (index: {index})", loc="left")
ax.set_xlim(first_date - pd.DateOffset(months=6), df.index[-1])
ax.set_ylim(0, upper_range)

ax.set_xlabel("Date")
ax.set_ylabel(f"{name.capitalize()} {units_string}")

ax.legend(loc="upper left")
ax.grid(alpha=0.5)

fig.savefig(f"{plot_dir}/plt_{name.lower().replace(' ','_')}_{index}.png", bbox_inches="tight")