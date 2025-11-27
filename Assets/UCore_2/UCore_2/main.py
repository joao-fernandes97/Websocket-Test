import exploring
import prediction


#  If the input was prediction then we run the prediction script, if it's exploring then we remove some files because with them neurokit will crash
# and return an error, and then we run the exploring script
def predicting_or_exploring(prediction_or_exploring, files, csv_file, signal, sample_rate, frequency):
    #files.remove("14")
    #files.remove("15")
    #files.remove("17")
    #files.remove("19")
    #files.remove("32")
    if prediction_or_exploring == 'prediction':
        # signal.remove("RESPIRATION")
        prediction.main_pred(files, csv_file, signal, sample_rate, frequency)
    elif prediction_or_exploring == 'exploring':
        for i in range(len(signal)):
            exploring.main_exp(files, csv_file, signal[i], sample_rate, frequency)
    else:
        print('Please insert only prediction or exploring')
        v = input()
        predicting_or_exploring(v, files, csv_file, signal, sample_rate, frequency)


# Waits until the user inputs a value and then runs the previous function
def main(files, csv_file, signal, sample_rate, frequency):
    print("Please choose between prediction and exploring")
    input_value = input()
    predicting_or_exploring(input_value, files, csv_file, signal, sample_rate, frequency)


# Participant ID, file containing the stimulation associated with each participant, types of signals that we will work on, sampling rate and desired frequency
main(["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"],
     "bimboola_data.csv", ['ECG',
                           'EDA', 'RESPIRATION']
     , 1000, 500)
