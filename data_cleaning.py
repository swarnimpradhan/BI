import pandas as pd

def convert_to_dataframe(items):

    data = []

    for item in items:

        row = {"Item Name": item["name"]}

        for col in item["column_values"]:

            column_title = col["column"]["title"]
            column_text = col["text"]

            row[column_title] = column_text

        data.append(row)

    df = pd.DataFrame(data)

    return df