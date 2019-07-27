def TsDataProcessor(Base, *other, target = None, t=10):
    import pandas as pd
    import numpy as np
    from collections import deque
    #first we create a list of all the entered arrays
    frames = list([Base])

    for i in other:
        frames.append(i)

    #then we make sure they are really arrays or dataframes, and convert series to frames to avoid errors in later steps
    for i in range(len(frames) - 1, -1, -1):
        if type(frames[i]) != pd.Series and type(frames[i]) != pd.DataFrame:
            print("Only data frames and series may be submitted as arguments for *other, not: " + str(type(frames[i])))
            if type(frames[i]) == pd.Series:
                frames[i] = frames[i].to_frame()

    #Use the main dataframe containing prediction targets as a base for the combined dataframe, and add the other frames
    dataset = frames[0]

    for i in range(1, len(frames)):
        dataset = pd.merge(dataset,frames[i], how='inner', left_index=True, right_index=True)

    dataset.dropna(inplace=True)

    # for i in range(0, 5):
    #     dataset["day" + str(i)] = (dataset.index.dayofweek == i).astype(int)

    #make sure the variable to be predicted is the last column, for later separation
    cols = list(dataset.columns)
    cols.remove(target)
    cols.append(target)
    dataset = dataset[cols]

    #create array to fill with samples. Deque has a maximum length equal to the desired number of past units to use for prediction
    #When an item is added to a full deque, the first item is removed, so the below loop creates a rolling time window used to populate the data for the nn
    sequential_data = []
    prev_days = deque(maxlen=t)

    for i in dataset.values:
        prev_days.append([n for n in i[:-1]])
        if len(prev_days) == t:
            sequential_data.append([np.array(prev_days), i[-1]])

    return dataset, sequential_data


def StockFilter(frame, tickercol = None):

    import pandas as pd

    singles = list(dict.fromkeys(frame[tickercol]))
    filtered = pd.DataFrame(index=frame[frame[tickercol] == singles[0]].index)

    for ticker in singles:
        for col in filtered.columns.values:
            filtered[ticker + " " + col] = frame[frame[tickercol] == ticker][col]

    #filtered.dropna(inplace = True, axis = 1)

def Scaler(frame, target):
    from sklearn import preprocessing

    for col in frame.columns.values:
        if col != target:
            # frame[col] = frame[col].pct_change()
            frame.dropna(inplace=True)
            frame[col] = preprocessing.scale(frame[col].values)

    frame.dropna(inplace=True)

    return frame

def Balance(data):

    import random

    buys = []
    sells = []

    for seq, target in data:
        if target == 1:
            buys.append([seq, target])
        else:
            sells.append([seq, target])

    random.shuffle(buys)
    random.shuffle(sells)

    lower = min(len(buys), len(sells))

    data = buys[:lower] + sells[:lower]

    random.shuffle(data)

    return data

def split(data):
    import numpy as np

    X = []
    Y = []

    for x, y in data:
        X.append(x)
        Y.append(y)

    return np.array(X), Y

