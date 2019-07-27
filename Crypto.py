import time

t = time.time()
import pandas as pd
import importlib
import TsDataProcessor
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, LSTM, BatchNormalization
from tensorflow.keras.callbacks import TensorBoard, ModelCheckpoint
import tensorflow as tf
import random
import os
import numpy as np
import plaidml

importlib.reload(TsDataProcessor)

#modifiable parameters
predict = "BTC"
epochs = 3
Batch_size = 512
ValPercent = 0.05
hindsight = 60
foresight = 4096
buy_threshold= 0.00
y_name = "close"
x_names = ["close", "volume", "low", "high", "open"]


cryptos = dict.fromkeys(["BTC", "ETH", "LTC"])

for i in cryptos:
    cryptos[i] = pd.read_csv("Data/" + i + "-USD.csv", names=['time', 'low', 'high', 'open', 'close', 'volume'],index_col = "time", parse_dates=True)
    cryptos[i] = cryptos[i][x_names] #only keep relevant columns
    cryptos[i].columns = i + " " + cryptos[i].columns.values #add crypto name to column headers for later when the datasets are combined

#the below lines calculate the return until the target date determined by "foresight" in the above parameters, and converts it to a 1 or 0 depending on whether
#or not it is above the buy threshold in the above parameters. Ex. if buy threshold is 0.05 then "target" will be one for a return of 5% or more
cryptos[predict]["target"] = cryptos[predict][predict + " " + y_name].shift(periods=-foresight) / cryptos[predict][predict + " " + y_name]
cryptos[predict]["target"] = (cryptos[predict]["target"] > 1 + buy_threshold).astype(int) #convert to
cryptos[predict].dropna(inplace=True)
print(cryptos[predict]["target"])
altcrypto = pd.DataFrame()

#this loop scales the data and puts the data of the non-target currencies together in a frame, for the TsDataProcessor function
for i in cryptos:
    cryptos[i] = TsDataProcessor.Scaler(cryptos[i], "target")
    if i != predict:
        altcrypto[cryptos[i].columns.values] = cryptos[i]

#Returns all the input frames together in one frame as "combined", and an array of training data. see TsDataProcessor for more
combined, sequential = TsDataProcessor.TsDataProcessor(cryptos[predict], altcrypto, target = "target", t=hindsight)

#separates the data into validation and training sets, Valpercent is the proportion of the total data used for validation
days = sorted(combined.index.values)
valprop = days[-int(ValPercent*len(days))]

random.shuffle(sequential)
mark = combined[(combined.index >= valprop)]


validation = sequential[:int(len(mark)/2)]
test = sequential[int(len(mark)/2):len(mark)]
train = sequential[len(mark):]


#the data is balanced so we have an equal number of buys and sells, otherwise the algorithm
# can get promising results just by never buying (always predicting 0), or always buying (always predicting 1) depending on the data
train = TsDataProcessor.Balance(train)
test = TsDataProcessor.Balance(test)
validation = TsDataProcessor.Balance(validation)

train_x, train_y = TsDataProcessor.split(train)
test_x, test_y = TsDataProcessor.split(test)
val_x, val_y = TsDataProcessor.split(validation)
# os.environ["KERAS_BACKEND"] = "plaidml.keras.backend"

Model = Sequential()
Model.add(LSTM(128, input_shape =(train_x.shape[1:]), activation = "tanh", return_sequences = True))
Model.add(Dropout(0.2))
Model.add(BatchNormalization())

Model.add(LSTM(128, input_shape =(train_x.shape[1:]), activation = "tanh", return_sequences = True))
Model.add(Dropout(0.1))
Model.add(BatchNormalization())

Model.add(LSTM(128, input_shape =(train_x.shape[1:]), activation = "tanh"))
Model.add(Dropout(0.2))
Model.add(BatchNormalization())

Model.add(Dense(32, activation="relu"))
Model.add(Dropout(0.2))

Model.add(Dense(2, activation="softmax"))

opt = tf.keras.optimizers.Adam(lr=0.001 , decay=1e-6)

Model.compile(loss="sparse_categorical_crossentropy",
              optimizer=opt,
              metrics=["accuracy"])

# NAME = f"{predict}-{hindsight}-SEQ-{foresight}-PRED-{int(time.time())}"
#
# tensorboard = TensorBoard(log_dir="logs/{}".format(NAME))
#
# filepath = "RNN_Final-{epoch:02d}-{val_acc:.3f}"  # unique file name that will include the epoch and the validation acc for that epoch
#
# checkpoint = ModelCheckpoint("models/{}.model".format(filepath, monitor='val_acc', verbose=1, save_best_only=True, mode='max')) # saves only the best ones




history = Model.fit(train_x, train_y, batch_size = Batch_size,epochs = epochs, validation_data=(val_x, val_y))

Model.evaluate(test_x,test_y)
