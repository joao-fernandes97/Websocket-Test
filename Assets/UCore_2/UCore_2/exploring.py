import csv
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from statistics import mean
import scipy
import numpy as np
import neurokit2 as nk
import pandas as pd
import scipy.integrate as si
from numpy import nanmean
from hrvanalysis import get_frequency_domain_features


# Open the file and gets all the measures
def openfiles(file):
    with open(file) as my_file:
        testsite_array = my_file.readlines()
        delete = [0, 1, 2]
        date = testsite_array[1].split('"date": ')[1].split(', ')[0].replace('"', '')
        for _ in delete:
            testsite_array = np.delete(testsite_array, 0, axis=0)
        lista = []
        for element in range(len(testsite_array)):
            t = testsite_array[element].split('\t')
            lista.append(t[:-1])
        return lista, date


# Transform a csv file into a list of lists and gets the type of stimulation
def csv_to_listOflists(file_path, text):
    with open(file_path) as file_obj:
        reader_obj = csv.reader(file_obj)
        for row in reader_obj:
            if text in row:
                return row[16]


# Associates time values with the list of measures
def associate_times(date, sample_rate, lista):
    mili = 1 / sample_rate
    current_mili = mili
    date = date.replace('"', '')
    time = '00:00:00.00'
    dates_final = date + " " + time
    formato = '%Y-%m-%d %H:%M:%S.%f'
    datetime_object = datetime.strptime(dates_final, formato)
    for element in range(len(lista)):
        result = datetime_object + timedelta(seconds=current_mili)
        lista[element].append(result)
        current_mili += mili
    return lista


# Associates to each image a marker with the start time and the end time of each image shown
def markers(markersfile, file):
    count = 0
    images = []
    final_images = []
    with open(markersfile) as my_file:
        array = my_file.readlines()
    for element in range(len(array)):
        if array[element].find("Base line start") != -1:
            count += 1
        if file == '07' and count == 1:
            images.append(array[element])
        if count >= 2:
            images.append(array[element])
    for element in range(0, len(images) - 1, 2):
        img_id = images[element].split('\t')[1].split('_')[0]
        img_start = images[element].split('\t')[0]
        img_end = images[element + 1].split('\t')[0]
        final_images.append((img_id, img_start, img_end))
    return final_images


# Instead of having the time values in float transforms the values to dateTime and adds 3 seconds to each because of the reaction time per participant
# to a certain image can delay 3 seconds
def markers_timers(final_images, date):
    formato = '%Y-%m-%d %H:%M:%S'
    updated = []
    for i in range(len(final_images)):
        dates_start = date + " " + final_images[i][1]
        dates_final = date + " " + final_images[i][2]
        datetime_start = datetime.strptime(dates_start, formato) + timedelta(seconds=3)
        datetime_final = datetime.strptime(dates_final, formato) + timedelta(seconds=3)
        updated.append((final_images[i][0], datetime_start, datetime_final))
    return updated


# Compares timestamps and associates images
def associate_images(updated, lista):
    new_list = []
    for element in range(len(lista)):
        counter = 0
        for index in range(len(updated)):
            if updated[index][1] <= lista[element][6] <= updated[index][2]:
                new_list.append((lista[element], updated[index][0]))
                counter += 1
        if counter == 0:
            new_list.append((lista[element], 'NOIMAGE'))
    return new_list


def peaks_each_image_ECG(final_images, up, frequency):
    ecg_features = pd.DataFrame()
    for img in range(len(final_images)):
        y = []
        for element in range(len(up)):
            if final_images[img][0] == up[element][1]:
                y.append(up[element][0][3])
        # Transforms values to float
        y = [float(y1) for y1 in y]
        # Gets HF and LF values
        frequency_domain_features = get_frequency_domain_features(y)
        # Z-score
        y = scipy.stats.zscore(y)
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
        image = pd.DataFrame([np.array([final_images[img][0]])], columns=['Img_name'])
        concat_df = pd.concat((image, hr_features, hrv_time_features, hrv_freq_features, mean_f, rmssd, hf, lf), axis=1)
        ecg_features = pd.concat((ecg_features, concat_df), axis=0)
    return ecg_features


# Calculates the variance between the mean FC value of the baseline and the mean FC value of a each image
def variance_fc_baseline(val):
    variance_df = pd.DataFrame()
    for col in range(1, len(val.columns), 1):
        baseline = float(val.iloc[0,col])
        name = 'Variance_' + val.columns[col]
        for row in range(1, len(val), 1):
            #CHECK
            v = baseline - float(val.iloc[row,col])
            variance = pd.DataFrame([np.array(v)], columns=[name])
            images = pd.DataFrame([val.iloc[row,0]], columns=['Img_name'])
            concat_df = pd.concat([images, variance], axis=1)
            variance_df = pd.concat((variance_df, concat_df), axis=0)
    variance_df = variance_df.apply(lambda x: pd.Series(x.dropna().values))
    variance_df = variance_df.dropna()
    return variance_df


# Combine different pandas datasets, if the full_variance is empty then it's equal to the variance_df , else we then add the values of variance_df to full variance
def combining_pandas(variance_df, full_variance):
    if len(full_variance) == 0:
        full_variance = variance_df
    else:
        for row in range(len(variance_df)):
            full_variance.loc[len(full_variance)] = variance_df.iloc[row]
    return full_variance


# Calculate mean of each value with the same image name
def associate_pandas(variance_full, img_array):
    mean_df = pd.DataFrame(columns=variance_full.columns)
    for i in range(len(img_array)):
        if img_array[i] != "Base line start":
            values = variance_full[variance_full['Img_name'] == img_array[i]]
            array_of_values = [img_array[i]]
            v = values.mean(numeric_only=True).values
            for j in range(len(v)):
                array_of_values.append(v[j])
            mean_df.loc[len(mean_df)] = array_of_values
    return mean_df


# Extracts features of eda
def eda_features_extraction(cleaned):
    mean_EDA = np.mean(cleaned)
    median_EDA = np.median(cleaned)
    sd_EDA = np.std(cleaned)
    mad_EDA = nk.mad(cleaned)
    diff_1st = np.diff(cleaned)
    meanFD_EDA = np.mean(diff_1st)
    sdFD_EDA = np.std(diff_1st)
    eda_features = {'EDA_Mean': [mean_EDA],
                    'EDA_Median': [median_EDA],
                    'EDA_SD': [sd_EDA],
                    'EDA_MAD': [mad_EDA],
                    'EDA_MFD': [meanFD_EDA],
                    'EDA_SDFD': [sdFD_EDA]
                    }
    return pd.DataFrame.from_dict(eda_features)


# Extracts tonic features of eda
def tonic_features_extraction(eda_SCL):
    mean_SCL = np.mean(eda_SCL)
    median_SCL = np.median(eda_SCL)
    sd_SCL = np.std(eda_SCL)
    mad_SCL = nk.mad(eda_SCL)
    auc_SCL = si.simpson(eda_SCL, dx=1, axis=- 1)

    scl_features = {'SCL_Mean': [mean_SCL],
                    'SCL_SD': [sd_SCL],
                    'SCL_MAD': [mad_SCL],
                    'SCL_Median': [median_SCL],
                    'SCL_AUC': [auc_SCL]
                    }

    return pd.DataFrame.from_dict(scl_features)


# Extracts phasic features of eda
def phasic_features_extraction(eda_SCR, info_peaks):
    mean_SCR = np.mean(eda_SCR)
    sd_SCR = np.std(eda_SCR)
    mad_SCR = nk.mad(eda_SCR)
    auc_SCR = si.simpson(eda_SCR, dx=1, axis=- 1)
    peaks = info_peaks['SCR_Peaks']
    rise_times = info_peaks['SCR_RiseTime']
    recovery_times = info_peaks['SCR_RecoveryTime']
    scr_amplitude = info_peaks['SCR_Amplitude']
    NP = np.shape(peaks)[0]
    if NP != 0:
        meanRET = np.nanmean(rise_times)
        meanRIT = np.nanmean(recovery_times)
        maxRA = np.nanmax(scr_amplitude)
    else:
        meanRET = 0
        meanRIT = 0
        maxRA = 0
        print('Warning! No SCR peaks detected inside window range...')
    scr_features = {'SCR_Mean': [mean_SCR],
                    'SCR_SD': [sd_SCR],
                    'SCR_MAD': [mad_SCR],
                    'SCR_AUC': [auc_SCR],
                    'NP': [NP],
                    'RET_Mean': [meanRET],
                    'RIT_Mean': [meanRIT],
                    'RA_Max': [maxRA]
                    }

    return pd.DataFrame.from_dict(scr_features)


# Extracts all features calling the previous mentioned functions and combines all the features in a panda
def peaks_each_image_EDA(final_images, up, frequency):
    features = pd.DataFrame()
    for img in range(1, len(final_images), 1):
        x = []
        y = []
        for element in range(len(up)):
            if final_images[img][0] == up[element][1]:
                x.append(up[element][0][6])
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
        image = pd.DataFrame([np.array([final_images[img][0]])], columns=['Img_name'])
        concat_df = pd.concat((image, tonic_features, phasic_features, mean_amplitude, number_of_peaks), axis=1)
        features = pd.concat((features, concat_df), axis=0)
    return features


# Extracts rsp statistical features
def rsp_statistical_features(values):
    means = np.mean(values)
    median = np.median(values)
    std = np.std(values)
    mad = nk.mad(values)
    percentile_80 = np.percentile(values, q=80, interpolation='nearest')

    return pd.DataFrame(data={'RSP_{}_Mean': [means],
                              'RSP_{}_Median': [median],
                              'RSP_{}_SD': [std],
                              'RSP_{}_MAD': [mad],
                              'RSP_{}_P80': [percentile_80]
                              })


# Extracts all features and combines it in a panda dataset
def peaks_each_image_RESPIRATION(final_images, up, frequency):
    rsp_features = pd.DataFrame()
    # zeros_per_image = []
    mean_high = []
    for img in range(1, len(final_images), 1):
        x = []
        y = []
        for element in range(len(up)):
            if final_images[img][0] == up[element][1]:
                x.append(up[element][0][6])
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
        image = pd.DataFrame([np.array([final_images[img][0]])], columns=['Img_name'])
        concat_df = pd.concat((image, rsp_frequency, number_of_peaks, zeros), axis=1)
        # Append row to existing dataframe
        rsp_features = pd.concat((rsp_features, concat_df), axis=0)
    return rsp_features


# Combines the values contained in two arrays
def combine(means, mean_fc):
    if len(mean_fc) == 0:
        mean_fc = means
    else:
        for i in range(len(means)):
            mean_fc.append((means[i][0], means[i][1]))
    return mean_fc


# Associates images to an array containing measurements
def associate(mean_fc, img_array):
    final_array = []
    for j in range(0, len(img_array)):
        if img_array[j] != "Base line start":
            array = []
            for i in range(len(mean_fc)):
                if img_array[j] == mean_fc[i][0]:
                    array.append(mean_fc[i][1])
            means = nanmean(array)
            final_array.append((img_array[j], means))
    return final_array


# Plots a whole panda dataset
def plotting_for_pandas(df):
    for col in range(1, len(df.columns), 1):
        measures = []
        img_name = []
        for row in range(len(df)):
            img_name.append(df.iloc[row][0])
            measures.append(df.iloc[row][col])
        plt.title("Ranking of " + df.columns[col])
        plt.xlabel("Image ID")
        plt.ylabel("Variation")
        for i in range(len(img_name)):
            if img_name[i][0] == '7':
                plt.bar(img_name[i], measures[i], color='forestgreen', width=0.4)
            else:
                plt.bar(img_name[i], measures[i], color='firebrick', width=0.4)
        plt.show()


# Creates a plot based on the input val
def plotting(n_l, val):
    measures = []
    img_name = []
    for element in range(len(n_l)):
        measures.append(n_l[element][1])
        img_name.append(n_l[element][0])
    plt.figure(figsize=(18, 8))
    if val == 0:
        plt.title("Ranking das variação do FC do sinal por imagem mostrada")
        plt.xlabel("ID da imagem")
        plt.ylabel("Variação")
    if val == 1:
        plt.title("Ranking das variação do RMSSD do sinal por imagem mostrada")
        plt.xlabel("ID da imagem")
        plt.ylabel("Variação")
    if val == 2:
        plt.title("Ranking das imagens por número de picos")
        plt.xlabel("ID da imagem")
        plt.ylabel("Nº médio de picos")
    if val == 3:
        plt.title("Ranking das imagens por amplitude média de picos SCR")
        plt.xlabel("ID da imagem")
        plt.ylabel("Nº médio de amplitude de picos")
    if val == 4:
        plt.title("Nº médio de zeros por imagem (RESPIRATION)")
        plt.xlabel("ID da imagem")
        plt.ylabel("Nº médio de zeros")
    if val == 5:
        plt.title("Ranking das imagens por altura de picos (RESPIRATION)")
        plt.xlabel("ID da imagem")
        plt.ylabel("Altura")
    if val == 6:
        plt.title("Nº médio de hf por imagem (ECG)")
        plt.xlabel("ID da imagem")
        plt.ylabel("HF")
    if val == 7:
        plt.title("Nº médio de lf por imagem (ECG)")
        plt.xlabel("ID da imagem")
        plt.ylabel("LF")
    for i in range(len(img_name)):
        if img_name[i][0] == '7':
            plt.bar(img_name[i], measures[i], color='forestgreen', width=0.4)
        else:
            plt.bar(img_name[i], measures[i], color='firebrick', width=0.4)
    plt.show()


# Gets all the images presented in the dataset
def getImages(img_array, final_images):
    for i in range(len(final_images)):
        img_array.append(final_images[i][0])
    return img_array


# Shortens the measures according to the frequency, for example if the sampling rate is 1000 and the frequency is 500 then we calculate the mean between
# each two values and that is the final measure
def sampling_re(s_r, frequency, lista):
    means_rate = s_r / frequency
    if int(means_rate) != 1:
        signal = []
        first, second, eda, ecg, respiration, val, date = [], [], [], [], [], [], []
        counter = 0
        for element in range(0, len(lista)):
            if counter == means_rate:
                middleIndex = int((len(date) - 1) / 2)
                signal.append(
                    [mean(first), mean(second), mean(eda), mean(ecg), mean(respiration), mean(val), date[middleIndex]])
                first, second, eda, ecg, respiration, val, date = [], [], [], [], [], [], []
                counter = 0
            else:
                first.append(int(lista[element][0]))
                second.append(int(lista[element][1]))
                eda.append(float(lista[element][2]))
                ecg.append(float(lista[element][3]))
                respiration.append(float(lista[element][4]))
                val.append(int(lista[element][5]))
                date.append(lista[element][6])
            counter += 1
        print(signal)
        return signal
    else:
        return lista


def main_exp(filename, csv_file, signal, sample_rate, frequency):
    variance_full = pd.DataFrame()
    eda_full = pd.DataFrame()
    rsp_full = pd.DataFrame()
    # zeros = []
    img_array = []
    # mean_high = []
    for element in range(len(filename)):
        # stimulation = csv_to_listOflists(csv_file, "DBY" + filename[element])
        lista, date = openfiles('sub-DBY' + filename[element] + '_ses-S001_task-Default_run-001_eeg.txt')
        lista = associate_times(date, sample_rate, lista)
        lista = sampling_re(sample_rate, frequency, lista)
        final_images = markers('sub-DBY' + filename[element] + '_ses-S001_task-Default_run-001_eegMARKERS.txt',
                               filename[element])
        print(final_images)
        if element == 0 or element == 1:
            img_array = getImages(img_array, final_images)
        if signal == 'ECG':
            updated = markers_timers(final_images, date)
            up = associate_images(updated, lista)
            val = peaks_each_image_ECG(final_images, up, frequency)
            pd.set_option('display.max_columns', None)
            variance = variance_fc_baseline(val)
            variance_full = combining_pandas(variance, variance_full)
        if signal == 'EDA':
            updated = markers_timers(final_images, date)
            up = associate_images(updated, lista)
            features_extracted = peaks_each_image_EDA(final_images, up, frequency)
            eda_full = combining_pandas(features_extracted, eda_full)
        if signal == "RESPIRATION":
            updated = markers_timers(final_images, date)
            up = associate_images(updated, lista)
            features_p = peaks_each_image_RESPIRATION(final_images, up, frequency)
            rsp_full = combining_pandas(features_p, rsp_full)
    if signal == 'ECG':
        mean_df = associate_pandas(variance_full, img_array)
        plotting_for_pandas(mean_df)
    if signal == 'EDA':
        eda_df = associate_pandas(eda_full, img_array)
        plotting_for_pandas(eda_df)
    if signal == 'RESPIRATION':
        rsp_df = associate_pandas(rsp_full, img_array)
        plotting_for_pandas(rsp_df)
