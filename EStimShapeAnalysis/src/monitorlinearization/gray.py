import pandas as pd
from matplotlib import pyplot as plt

from clat.util.connection import Connection
from monitorlinearization.monlin import get_most_recent_pickle_path


def main():
    conn = Connection("allen_monitorlinearization_240228")
    # Load data
    pickle_path = get_most_recent_pickle_path("gray")
    df = pd.read_pickle(
        pickle_path)
    # filter for non NaN
    df = df[df['StimSpecId'].notna()]
    print(df.to_string())
    plot_candela_values(df)

    save_to_db(conn, df)


def save_to_db(conn, data):
    ## Save the data to the database
    # calculate average candela for repeats
    data['color'] = data.apply(lambda row: (row['Red'], row['Green'], row['Blue']), axis=1)
    avg_candela = data.groupby('color')['Candela'].mean().reset_index()

    for _, row in avg_candela.iterrows():
        red, green, blue = row['color']
        luminance = row['Candela']
        conn.execute("""
            INSERT INTO MonitorLin (red, green, blue, luminance)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE luminance = VALUES(luminance)
        """, (red, green, blue, luminance))


def plot_candela_values(df):
    target_luminance = 150

    plt.figure(figsize=(10, 6))
    df['Gray'] = (df['Red'] + df['Green'] + df['Blue']) / 3
    df = df.sort_values(by=['Gray'])
    print(df.to_string())
    averaged_df = df.groupby('Gray')['Candela'].mean().reset_index()
    x_data = averaged_df['Gray']
    y_data = averaged_df['Candela']
    plt.plot(x_data, y_data, marker='o', linestyle='-', color='blue', label='Candela Value')

    # #closest to 150
    closest = (averaged_df['Candela'] - target_luminance).abs().idxmin()
    print(averaged_df.iloc[closest])
    plt.show()


if __name__ == "__main__":
    main()
