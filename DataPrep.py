import timeimport pandas as pdimport importlibimport tensorflow as tfimport randomimport DataRefreshimport DataRefreshimport torchimport osimport numpy as np#import plaidmlimport numpy as npfrom sklearn import preprocessingimportlib.reload(DataRefresh)def StockFilter(frame, tickercol = None):    import pandas as pd    singles = list(dict.fromkeys(frame[tickercol]))    filtered = pd.DataFrame(index=frame[frame[tickercol] == singles[0]].index)    for ticker in singles:        for col in filtered.columns.values:            filtered[ticker + " " + col] = frame[frame[tickercol] == ticker][col]    filtered.dropna(inplace = True, axis = 1)    return filtereddef Scaler(frame):    import numpy as np    for col in frame.columns.values:        if col.endswith('AMOUNT'):            frame[col] = preprocessing.scale(frame[col].values)        else:            frame[col] = frame[col].pct_change()            frame = frame.replace([np.inf, -np.inf], np.nan)            frame.dropna(inplace=True)            frame[col] = preprocessing.scale(frame[col].values)    frame.dropna(inplace=True)    return framedef Tensify(dataframe, p, Y = True):    if Y:        if p.sell_threshold == None and len(p.TargetTickers) == 1:            variables = (tf.constant(dataframe[dataframe.columns.values[:-1]].values), tf.constant(dataframe[dataframe.columns.values[-1]].values))        else:            variables = (tf.constant(dataframe[dataframe.columns.values[:-p.LabelCount]].values), tf.constant(dataframe[dataframe.columns.values[-p.LabelCount:]].values))    else:        variables = (tf.constant(dataframe.values))    tensor = tf.data.Dataset.from_tensor_slices(variables)    tensor = tensor.window(p.hindsight,1,1,True)    if Y:        if p.sell_threshold == None and len(p.TargetTickers) == 1:            tensor = tensor.flat_map(lambda x,y: tf.data.Dataset.zip((x.batch(p.hindsight), y.batch(1))))        else:            tensor = tensor.flat_map(lambda x,y: tf.data.Dataset.zip((x.batch(p.hindsight), y)))    else:        tensor = tensor.flat_map(lambda x: tf.data.Dataset.zip(x.batch(p.hindsight)))    return tensordef BalanceTensor(tensor, npos, p):    if p.sell_threshold != None and len(p.TargetTickers) == 1:        positive = tensor.filter(lambda x,y: tf.math.equal(y[-1],0))        negative = tensor.filter(lambda x,y: tf.math.equal(y[-1],1))    else:        positive = tensor.filter(lambda x,y: tf.math.equal(y[-1],0))        negative = tensor.filter(lambda x,y: tf.math.equal(y[-1],1))    negative = negative.shuffle(20000)    negative = negative.take(npos)    tensor = positive.concatenate(negative)    tensor = tensor.shuffle(20000)    return tensordef DataPreparation(p):    DFrame = pd.read_csv('Data/Processed.csv', index_col = 'time', parse_dates=True)    for ticker in p.TargetTickers:        DFrame['target'] = DFrame[ticker + ' ' + p.y_name].shift(periods=-p.foresight) / DFrame[ticker + ' ' + p.y_name]        DFrame[ticker +' long'] = (DFrame['target'] > 1 + p.buy_threshold).astype(int)        if p.sell_threshold != None:            DFrame[ticker +' short'] = (DFrame['target'] < 1 - p.sell_threshold).astype(int)        DFrame = DFrame.drop(['target'], axis = 1)    DFrame['none'] = (DFrame[DFrame.columns.values[-(p.LabelCount-1):]].sum(axis = 1) == 0).astype(int)    TargetPrice = pd.DataFrame(index = DFrame.index)    Price = pd.DataFrame(index = DFrame.index)    for TargetTicker in p.TargetTickers:        TargetPriceTemp = pd.DataFrame(DFrame[TargetTicker + ' ' + p.y_name].shift(periods=-p.foresight)).copy()        TargetPriceTemp.columns.values[0] = TargetTicker + ' TargetPrice'        TargetPrice = TargetPrice.merge(TargetPriceTemp, how='inner', left_index=True, right_index=True)        PriceTemp = pd.DataFrame(DFrame[TargetTicker + ' ' + p.y_name]).copy()        PriceTemp.columns.values[0] = TargetTicker + ' Price'        Price = Price.merge(PriceTemp, how='inner', left_index=True, right_index=True)    TargetPrice.dropna(inplace=True)    Price.dropna(inplace=True)    # ScaledFeatures = Scaler(DFrame[DFrame.columns.values[:-p.LabelCount]])    ScaledFeatures = DFrame[DFrame.columns.values[:-p.LabelCount]]    Labels = DFrame[DFrame.columns.values[-p.LabelCount:]]    DFrame = ScaledFeatures.merge(Labels, how='inner', left_index=True, right_index=True)    DFrame.dropna(inplace=True)    testlength = int(p.TestProportion*len(DFrame))    test = DFrame.iloc[-testlength:]    DFrame = DFrame.iloc[:-testlength]    tensor = Tensify(DFrame, p)    if p.sell_threshold == None and len(p.TargetTickers) == 1:        tensor = BalanceTensor(tensor, sum(DFrame[p.TargetTickers[0] + ' long']), p)    else:        tensor = BalanceTensor(tensor, len(DFrame)-sum(DFrame['none']), p)    tensor = tensor.batch(p.Batch_size).prefetch(1)    test = test.merge(Price, how ='inner', left_index=True, right_index=True)    test = test.merge(TargetPrice, how ='inner', left_index=True, right_index=True)    TestTensor = Tensify(test[test.columns.values[:-(p.LabelCount+len(p.TargetTickers)*2)]], p, Y = False)    TestTensor = TestTensor.batch(p.Batch_size).prefetch(1)    test = test.iloc[:-p.hindsight+1]    print(len(DFrame) - sum(DFrame['none']))    del DFrame    return tensor, TestTensor, test