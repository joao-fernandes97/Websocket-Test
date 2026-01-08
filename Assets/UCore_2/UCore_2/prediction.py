import numpy as np
import pandas as pd

import exploring
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC


# Decision tree classifier
def decisionTree(X_train, X_test, y_train, y_test):
    clf = DecisionTreeClassifier()
    clf = clf.fit(X_train, y_train.values.ravel())
    y_pred = clf.predict(X_test)
    print("Accuracy:", accuracy_score(y_test, y_pred))
    print("Confusion Matrix:", confusion_matrix(y_test, y_pred))


# K neighbors classifier
def kneighbors(X_train, X_test, y_train, y_test):
    knn = KNeighborsClassifier()
    knn.fit(X_train, y_train.values.ravel())
    y_pred = knn.predict(X_test)
    print("Accuracy:", accuracy_score(y_test, y_pred))
    print("Confusion Matrix:", confusion_matrix(y_test, y_pred))


# SVC classifier
def svc(X_train, X_test, y_train, y_test):
    svc1 = SVC()
    svc1.fit(X_train, y_train.values.ravel())
    y_pred = svc1.predict(X_test)
    print("Accuracy:", accuracy_score(y_test, y_pred))
    print("Confusion Matrix:", confusion_matrix(y_test, y_pred))


# Logistic regression
def logisticRegression(X_train, X_test, y_train, y_test):
    lr = LogisticRegression(random_state=0, max_iter=5000)
    lr.fit(X_train, y_train.values.ravel())
    y_pred = lr.predict(X_test)
    print("Accuracy:", accuracy_score(y_test, y_pred))
    print("Confusion Matrix:", confusion_matrix(y_test, y_pred))


# Random forest
def randomForest(X_train, X_test, y_train, y_test):
    rfc = RandomForestClassifier()
    rfc.fit(X_train, y_train.values.ravel())
    y_pred = rfc.predict(X_test)
    print("Accuracy:", accuracy_score(y_test, y_pred))
    print("Confusion Matrix:", confusion_matrix(y_test, y_pred))


def combine_Dataframes(eda, ecg, rsp):
    # return pd.concat([eda, ecg.loc[:, ecg.columns != 'Img_name']], axis=1)
    return pd.concat([eda, ecg.loc[:, ecg.columns != 'Img_name'], rsp.loc[:, rsp.columns != 'Img_name']], axis=1)


def add_stimulation(full):
    features = pd.DataFrame()
    # stimulation = 0
    for i in range(len(full['Img_name'])):
        s = full.iloc[i]['Img_name']
        if str(s)[0] == "7":
            stimulation = 1
        else:
            stimulation = 0
        sti = pd.DataFrame([np.array(stimulation)], columns=['Stimulation'])
        concat_df = pd.concat((full, sti), axis=1)
        features = pd.concat((features, concat_df), axis=0)
    features = features.apply(lambda x: pd.Series(x.dropna().values))
    features = features.dropna()
    return features


def prediction(df):
    X = df.iloc[:, :-1]
    y = df.iloc[:, -1:]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)
    # Machine learning methods
    print("Logisitic Regression")
    logisticRegression(X_train, X_test, y_train, y_test)
    print("Decision Tree")
    decisionTree(X_train, X_test, y_train, y_test)
    print("Random Forest")
    randomForest(X_train, X_test, y_train, y_test)
    print("SVC")
    svc(X_train, X_test, y_train, y_test)
    print("Kneighbors")
    kneighbors(X_train, X_test, y_train, y_test)


def main_pred(filename, csv_file, signal, sample_rate, frequency):
    img_array = []
    eda_full = pd.DataFrame()
    ecg_full = pd.DataFrame()
    rsp_full = pd.DataFrame()
    for i in range(len(signal)):
        for element in range(len(filename)):
            stimulation = exploring.csv_to_listOflists(csv_file, "DBY" + filename[element])
            lista, date = exploring.openfiles('sub-DBY' + filename[element] + '_ses-S001_task-Default_run-001_eeg.txt')
            lista = exploring.associate_times(date, sample_rate, lista)
            print(filename[element])
            final_images = exploring.markers(
                'sub-DBY' + filename[element] + '_ses-S001_task-Default_run-001_eegMARKERS.txt',
                filename[element])
            if element == 0 or element == 1:
                img_array = exploring.getImages(img_array, final_images)
            updated = exploring.markers_timers(final_images, date)
            up = exploring.associate_images(updated, lista)
            if signal[i] == 'EDA':
                eda = exploring.peaks_each_image_EDA(final_images, up, frequency)
                eda_full = exploring.combining_pandas(eda, eda_full)
            if signal[i] == 'ECG':
                ecg = exploring.peaks_each_image_ECG(final_images, up, frequency)
                ecg = exploring.variance_fc_baseline(ecg)
                ecg_full = exploring.combining_pandas(ecg, ecg_full)
            if signal[i] == 'RESPIRATION':
                rsp = exploring.peaks_each_image_RESPIRATION(final_images, up, frequency)
                rsp_full = exploring.combining_pandas(rsp, rsp_full)
        # if signal[i] == 'EDA':
        # eda_full = exploring.associate_pandas(eda_full, img_array)
        # if signal[i] == 'ECG':
        # ecg_full = exploring.associate_pandas(ecg_full, img_array)
        # if signal[i] == 'RESPIRATION':
        #    rsp_full = exploring.associate_pandas(rsp_full, img_array)
    pd.set_option('display.max_rows', None)
    eda_full = eda_full.reset_index()
    ecg_full = ecg_full.reset_index()
    rsp_full = rsp_full.reset_index()
    eda_full.drop('index', axis=1)
    full = combine_Dataframes(eda_full, ecg_full, rsp_full)
    df = add_stimulation(full)
    df = df.drop('index', axis=1)
    df = df.drop('Img_name', axis=1)
    print(df)
    prediction(df)
    # img_eda, img_ecg, img_rsp = panda_with_stimulation(img_array, up)
    # pred_eda.append(img_eda)
    # pred_ecg.append(img_ecg)
    # pred_rsp.append(img_rsp)
    # prediction_function(filename, img_array, pred_eda, pred_ecg, pred_rsp)
