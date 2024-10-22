from tkinter import filedialog

from clat.eyecal.params import EyeCalibrationParameters
from clat.util.connection import Connection

from src.startup import context


def main():
    current_conn = context.ga_config.connection()

    #Open a GUI window to select a file
    filename = filedialog.askopenfilename(initialdir = context.eyecal_dir, title ="Select file")

    #Read the file as one big string
    with open(filename, 'r') as f:
        lines = f.readlines()

    string = ""
    for line in lines:
        string += line

    EyeCalibrationParameters.deserialize(string).write_params(current_conn)




if __name__ == '__main__':
    main()