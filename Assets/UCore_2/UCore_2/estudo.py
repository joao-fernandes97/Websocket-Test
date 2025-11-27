from datetime import datetime, timedelta
from statistics import mean

import numpy as np
import pandas as pd
import scipy
import neurokit2 as nk
from hrvanalysis import get_frequency_domain_features
from matplotlib import pyplot as plt
from numpy import nanmean

from exploring import openfiles, associate_times, markers, associate_images, markers_timers, peaks_each_image_ECG, \
    peaks_each_image_EDA, peaks_each_image_RESPIRATION, plotting_for_pandas, rsp_statistical_features, \
    tonic_features_extraction, phasic_features_extraction, csv_to_listOflists


def markers_study(markersfile, file):
    counter = 0
    c = 0
    images = []
    final_images = []
    with open(markersfile) as my_file:
        array = my_file.readlines()
    for element in range(len(array)):
        if counter >= len(array) - 2 or array[element].find("Base line start") != - 1 or array[element].find(
                "Base Line Ended") != -1:
            images.append(array[element])
        counter += 1
    if file == '07':
        images.insert(0, '0:00:00\tBase line start\t\n')
    print(images)
    for element in range(0, len(images) - 1, 2):
        img_id = images[element].split('\t')[1]
        if img_id == "Base line start" and c == 0:
            img_id = images[element].split('\t')[1] + "1"
            c += 1
        elif img_id == "Base line start" and c == 1:
            img_id = images[element].split('\t')[1] + "2"
        else:
            img_id = images[element].split('\t')[1]
        img_start = images[element].split('\t')[0]
        img_end = images[element + 1].split('\t')[0]
        final_images.append((img_id, img_start, img_end))
    return final_images


def peaks_each_image_ECG_study(final_images, up, frequency):
    ecg_features = pd.DataFrame()
    for img in range(len(final_images)):
        y = []
        for element in range(len(up)):
            if final_images[img][0] == up[element][1]:
                y.append(up[element][0][3])
        # Transforms values to float
        y = [float(y1) for y1 in y]
        frequency_domain_features = get_frequency_domain_features(y)
        # Neurokit function to clean the raw data
        cleaned = nk.ecg_clean(y, sampling_rate=frequency, method="neurokit")
        # Calculates the rate
        info = nk.ecg_findpeaks(cleaned, sampling_rate=frequency, method="neurokit")
        # Compute Instantaneous HR Mean and STD
        ibi = np.diff(info["ECG_R_Peaks"]) / frequency
        HR = 1 / ibi
        hr_features = pd.DataFrame([np.array([np.mean(HR), np.std(HR)])], columns=['HR_Mean', 'HR_SD'])
        # Compute Time-domain features
        hrv_time_features = nk.hrv_time(info["ECG_R_Peaks"], frequency)
        hrv_time_features.drop(
            columns=['HRV_SDANN1', 'HRV_SDNNI1', 'HRV_SDANN2', 'HRV_SDNNI2', 'HRV_SDANN5', 'HRV_SDNNI5'], axis=1,
            inplace=True)
        # Compute Frequency-domain features (NO sliding window applied)
        hrv_freq_features = nk.hrv_frequency(info["ECG_R_Peaks"], frequency)
        hrv_freq_features.drop(
            columns=['HRV_ULF', 'HRV_VLF', 'HRV_VHF', 'HRV_LF', 'HRV_HF', 'HRV_LFHF', 'HRV_LFn', 'HRV_HFn', 'HRV_LnHF'],
            axis=1, inplace=True)
        rate = nk.signal_rate(peaks=info["ECG_R_Peaks"], desired_length=len(y), interpolation_method="monotone_cubic")
        # noinspection PyTypeChecker
        hr_value = nk.hrv_time(info["ECG_R_Peaks"], sampling_rate=frequency)
        v = str(hr_value["HRV_MeanNN"])
        # Mean of RMSSD indice
        # noinspection PyTypeChecker
        mean_f = pd.DataFrame([np.array([np.mean(rate)])], columns=['Mean_Rate'])
        lf = pd.DataFrame([np.array([frequency_domain_features["lf"]])], columns=['LF'])
        hf = pd.DataFrame([np.array([frequency_domain_features["hf"]])], columns=['HF'])
        rmssd = pd.DataFrame([np.array([v.split("  ")[2].split("\n")[0]])], columns=['RMSSD'])
        image = pd.DataFrame([np.array([final_images[img][0]])], columns=['VarianceType_ParticipantNumber'])
        concat_df = pd.concat((image, hr_features, hrv_time_features, hrv_freq_features, mean_f, rmssd, hf, lf),
                              axis=1)
        ecg_features = pd.concat((ecg_features, concat_df), axis=0)
    return ecg_features


# Compares timestamps and associates images
def associate_images_study(updated, lista):
    new_list = []
    for element in range(len(lista)):
        counter = 0
        for index in range(len(updated)):
            if updated[index][1] <= lista[element][6] <= updated[index][2]:
                new_list.append((lista[element], updated[index][0]))
                counter += 1
    return new_list


def create_array(df, name):
    array = [name]
    df = df.drop("VarianceType_ParticipantNumber", axis=1)
    df = df.reset_index().drop("index", axis=1)
    for column in df.columns:
        array.append(float(df.iloc[1][column]) - float(df.iloc[0][column]))
    return array


def differences(df, user, stimulation):
    df = df.reset_index().drop("index", axis=1)
    new_df = df[:-1]
    new_df1 = df.iloc[1:]
    new_df2 = df.iloc[[0, -1]]
    array = create_array(new_df, 'Social_Economical' + "_" + user)
    print(array)
    array1 = create_array(new_df1, 'Showing_images' + "_" + user)
    print(array1)
    array2 = create_array(new_df2, 'Full_Experience' + "_" + user)
    print(array2)
    df.loc[len(df)] = array
    df.loc[len(df)] = array1
    df.loc[len(df)] = array2
    print(df)
    df = df.tail(3).reset_index().drop("index", axis=1)
    df['Stimulation'] = stimulation
    return df


def plotting_for_study(df, last_image):
    for col in range(1, len(df.columns), 1):
        measures = []
        types = []
        for row in range(len(df)):
            types.append(df.iloc[row][0])
            measures.append(df.iloc[row][col])
        plt.title("Variance for the feature :" + df.columns[col])
        plt.xlabel("Type of stimulation")
        plt.ylabel("Variation")
        for i in range(len(types)):
            if last_image[0] == '7':
                plt.bar(types[i], measures[i], color='forestgreen', width=0.4)
            else:
                plt.bar(types[i], measures[i], color='firebrick', width=0.4)
        plt.show()


# Extracts all features calling the previous mentioned functions and combines all the features in a panda
def peaks_each_image_EDA_study(final_images, up, frequency):
    features = pd.DataFrame()
    for img in range(len(final_images)):
        y = []
        for element in range(len(up)):
            if final_images[img][0] == up[element][1]:
                y.append(up[element][0][2])
        # Z-score and float transformation
        y = [float(y1) for y1 in y]
        y = scipy.stats.zscore(y)
        # Clean raw measurements
        cleaned = nk.eda_clean(y, sampling_rate=frequency, method="neurokit")
        # Phasic component extraction
        highpass = nk.eda_phasic(cleaned, sampling_rate=frequency, method='highpass')
        data = pd.concat([highpass.add_suffix('_Highpass')], axis=1)
        eda_SCR = data["EDA_Phasic_Highpass"].values
        eda_SCL = data["EDA_Tonic_Highpass"].values
        # Detect the peaks
        info, neurokit = nk.eda_peaks(eda_SCR, sampling_rate=frequency, method="neurokit")
        val = nanmean(neurokit["SCR_Amplitude"])
        tonic_features = tonic_features_extraction(eda_SCL)
        phasic_features = phasic_features_extraction(eda_SCR, neurokit)
        mean_amplitude = pd.DataFrame([np.array(val)], columns=['Mean_Amplitude'])
        number_of_peaks = pd.DataFrame([np.array(len(neurokit["SCR_Peaks"]))], columns=['Number_Of_Peaks'])
        image = pd.DataFrame([np.array([final_images[img][0]])], columns=['VarianceType_ParticipantNumber'])
        concat_df = pd.concat((image, tonic_features, phasic_features, mean_amplitude, number_of_peaks), axis=1)
        features = pd.concat((features, concat_df), axis=0)
    return features


# Extracts all features and combines it in a panda dataset
def peaks_each_image_RESPIRATION_study(final_images, up, frequency):
    rsp_features = pd.DataFrame()
    # zeros_per_image = []
    mean_high = []
    for img in range(len(final_images)):
        y = []
        for element in range(len(up)):
            if final_images[img][0] == up[element][1]:
                y.append(up[element][0][4])
        # Transformation to float and Z-score
        y = [float(y1) for y1 in y]
        y = scipy.stats.zscore(y)
        # Cleans the rsp raw dataset
        rsp_cleaned = nk.rsp_clean(y, sampling_rate=frequency)
        # Finds the peaks correspondent to each image
        info = nk.signal_findpeaks(rsp_cleaned)
        # Calculates the where does the signal cross zero
        zeros = nk.signal_zerocrossings(rsp_cleaned)
        # Adds to an array the mean amplitude of the peak
        mean_high.append((final_images[img][0], mean(info["Height"])))
        # Adds to an array the number of times the signal crosses zero for that image
        rsp_frequency = rsp_statistical_features(rsp_cleaned)
        # noinspection PyTypeChecker
        zeros = pd.DataFrame([np.array(len(zeros))], columns=['Zeros'])
        number_of_peaks = pd.DataFrame([np.array(mean(info["Height"]))], columns=['Mean_Peak_High'])
        image = pd.DataFrame([np.array([final_images[img][0]])], columns=['VarianceType_ParticipantNumber'])
        concat_df = pd.concat((image, rsp_frequency, number_of_peaks, zeros), axis=1)
        # Append row to existing dataframe
        rsp_features = pd.concat((rsp_features, concat_df), axis=0)
    return rsp_features


def creating_csv(df, signal, writer):
    if signal == 'EDA':
        df.to_excel(writer, sheet_name='EDA', index=False)
    if signal == 'ECG':
        df.to_excel(writer, sheet_name='ECG', index=False)
    if signal == 'RESPIRATION':
        df.to_excel(writer, sheet_name='RESPIRATION', index=False)


def main_study(filename, csv_file, signals, sample_rate, frequency):
    filename.remove("15")
    ecg_df = pd.DataFrame()
    eda_df = pd.DataFrame()
    respiration_df = pd.DataFrame()
    writer = pd.ExcelWriter('demo.xlsx', engine='xlsxwriter')
    for signal in signals:
        for element in range(len(filename)):
            stimulation = csv_to_listOflists(csv_file, "DBY" + filename[element])
            lista, date = openfiles('sub-DBY' + filename[element] + '_ses-S001_task-Default_run-001_eeg.txt')
            lista = associate_times(date, sample_rate, lista)
            print(filename[element])
            final_images = markers_study(
                'sub-DBY' + filename[element] + '_ses-S001_task-Default_run-001_eegMARKERS.txt',
                filename[element])
            last_image = final_images[len(final_images) - 1][0].split("_")[0]
            updated = markers_timers(final_images, date)
            up = associate_images_study(updated, lista)
            if signal == 'ECG':
                features_extracted = peaks_each_image_ECG_study(final_images, up, frequency)
                df = differences(features_extracted, filename[element], stimulation)
                ecg_df = pd.concat([ecg_df, df])
            if signal == 'EDA':
                features_extracted = peaks_each_image_EDA_study(final_images, up, frequency)
                df = differences(features_extracted, filename[element], stimulation)
                eda_df = pd.concat([eda_df, df])
            if signal == 'RESPIRATION':
                features_extracted = peaks_each_image_RESPIRATION_study(final_images, up, frequency)
                df = differences(features_extracted, filename[element], stimulation)
                respiration_df = pd.concat([respiration_df, df])
        if signal == 'EDA':
            creating_csv(eda_df, signal, writer)
        if signal == 'ECG':
            creating_csv(ecg_df, signal, writer)
        if signal == 'RESPIRATION':
            creating_csv(respiration_df, signal, writer)
    writer.close()


main_study(
    ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19",
     "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38",
     "39", "46", "48"
     ],
    "bimboola_data.csv", ['EDA'], #, 'ECG', 'RESPIRATION'],
    1000, 500)
