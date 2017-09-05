from time import strftime
import json
import thoipapy
from thoipapy import mtutiles as utils
import logging
import os
import pandas as pd
import platform
import psutil
import signal
import sys
import re

def tmd_positions_match_fasta(pathdict,set_,logging):
    fasta_file_loc=set_["input_fasta_file"]
    tmd_file_loc=set_["input_tmd_file"]
    fasta_text=""
    tmd_text=""
    with open(fasta_file_loc) as f:
        for line in f.readlines():
            if re.search("^>",line):
                next
            else:
                fasta_text=fasta_text+line.rstrip()
    with open(tmd_file_loc) as f1:
        for line in f1.readlines():
            if re.search("^>",line):
                next
            else:
                tmd_text=tmd_text+line.rstrip()
    tmd_length=len(tmd_text)
    tmd_start=fasta_text.find(tmd_text)+1
    tmd_end=tmd_start+tmd_length-1
    return tmd_start, tmd_end








def create_settingdict(excel_file_with_settings):
    sheetnames = ["run_settings", "file_locations", "variables"]
    set_ = {}
    for sheetname in sheetnames:
        # open excel file as pandas dataframe
        dfset = pd.read_excel(excel_file_with_settings, sheetname=sheetname)
        # exclude row with notes, set parameter as index
        dfset = dfset[["parameter", "value"]].dropna()
        dfset.set_index("parameter", inplace=True)
        # convert true-like strings to True, and false-like strings to False
        dfset.value = dfset.value.apply(utils.convert_truelike_to_bool, convert_nontrue=False)
        dfset.value = dfset.value.apply(utils.convert_falselike_to_bool)
        # convert to dictionary
        sheet_as_dict = dfset.to_dict()["value"]
        # join dictionaries together
        set_.update(sheet_as_dict)

    list_paths_to_normalise = ["protein_folder", "Train_proteins", "Experimental_proteins", "list_of_tmd_start_end", "homologous_folder",
                               "xml_file_folder", "filtered_homo_folder", "RF_features","feature_entropy","feature_pssm","feature_cumulative_coevolution","feature_relative_position","feature_lips_score","feature_physical_parameters","logging_file"]
    # normalise the paths for selected columns, so that they are appropriate for the operating system
    for path in list_paths_to_normalise:
        if path in set_:
            set_[path] = os.path.normpath(set_[path])
    return set_

def setup_keyboard_interrupt_and_error_logging(set_, list_number):
    ''' -------Setup keyboard interrupt----------
    '''
    # import arcgisscripting

    def ctrlc(sig, frame):
        raise KeyboardInterrupt("CTRL-C!")
    signal.signal(signal.SIGINT, ctrlc)
    '''+++++++++++++++LOGGING++++++++++++++++++'''
    date_string = strftime("%Y%m%d_%H_%M_%S")

    # designate the output logfile
    logfile = os.path.join(set_["logfile_dir"],'List%s_%s_logfile.log' % (list_number, date_string))

    # if multiprocessing is used, disable logging except for critical messages.
    if set_["use_multiprocessing"]:
        level_console = "CRITICAL"
        level_logfile = "CRITICAL"
    else:
        level_console = set_["logging_level_console"]
        level_logfile = set_["logging_level_logfile"]

    logging = thoipapy.common.setup_error_logging(logfile, level_console, level_logfile)
    return logging

def setup_error_logging(logfile, level_console="DEBUG", level_logfile="DEBUG"):
    """ Sets up error logging, and logs a number of system settings.

    Parameters:
    -----------
    logfile : str
        Path to output logfile. If size exceeds limit set below in JSON settings, path.1, path.2 etc will be created.
    level_console : str
        Logging level for printing to console. DEBUG, WARNING or CRITICAL
    level_logfile : str
        Logging level for printing to logfile. DEBUG, WARNING or CRITICAL
    """
    # load the log settings in json format
    logsettings = json.dumps({
        "handlers": {
            "console": {
                "formatter": "brief",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "level": "DEBUG"
            },
            "file": {
                "maxBytes": 10000000,
                "formatter": "precise",
                "backupCount": 3,
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "filename": "logfile.txt"
            }
        },
        "version": 1,
        "root": {
            "handlers": [
                "console",
                "file"
            ],
            "propagate": "no",
            "level": "DEBUG"
        },
        "formatters": {
            "simple": {
                "format": "format=%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "precise": {
                "format": "%(asctime)s %(name)-15s %(levelname)-8s %(message)s"
            },
            "brief": {
                "format": "%(levelname)-8s: %(name)-15s: %(message)s"
            }
        }
    }, skipkeys=True, sort_keys=True, indent=4, separators=(',', ': '))

    config=json.loads(logsettings)
    # add user parameters to the logging settings (logfile, and logging levels)
    config['handlers']['file']['filename'] = logfile
    config['handlers']['console']['level'] = level_console
    config['handlers']['file']['level'] = level_logfile

    #create a blank logging file
    with open(logfile, 'w') as f:
        pass

    #clear any previous logging handlers that might have been previously run in the console
    logging.getLogger('').handlers = []
    #load the logging settings from the modified json string
    logging.config.dictConfig(config)
    # collect a number of system settings that could be useful for troubleshooting
    system_settings_dict = {}
    system_settings_dict["system description"] = platform.uname()
    system_settings_dict["system"] = platform.system()
    system_settings_dict["architecture"] = platform.architecture()
    system_settings_dict["network_name"] = platform.node()
    system_settings_dict["release"] = platform.release()
    system_settings_dict["version"] = platform.version()
    system_settings_dict["machine"] = platform.machine()
    system_settings_dict["processor"] = platform.processor()
    system_settings_dict["python_version"] = platform.python_version()
    system_settings_dict["python_build"] = platform.python_build()
    system_settings_dict["python_compiler"] = platform.python_compiler()
    system_settings_dict["argv"] = sys.argv
    system_settings_dict["dirname(argv[0])"] = os.path.abspath(os.path.expanduser(os.path.dirname(sys.argv[0])))
    system_settings_dict["pwd"] = os.path.abspath(os.path.expanduser(os.path.curdir))
    system_settings_dict["total_ram"] = "{:0.2f} GB".format(psutil.virtual_memory()[0] / 1000000000)
    system_settings_dict["available_ram"] = "{:0.2f} GB ({}% used)".format(psutil.virtual_memory()[1] / 1000000000, psutil.virtual_memory()[2])
    # log the system settings
    logging.warning(system_settings_dict)
    #test error message reporting
    #logging.warning('LOGGING TEST:')
    #try:
    #    open('/path/to/does/not/exist', 'rb')
    #except (SystemExit, KeyboardInterrupt):
    #    raise
    #except Exception:
    #    logging.error('Failed to open file', exc_info=True)
    logging.warning('LOGGING SETUP IS SUCCESSFUL (logging levels: console={}, logfile={}). \n'.format(level_console, level_logfile))
    return logging

def create_pathdict(base_filename_summaries):
    pathdict = {}
    pathdict["base_filename_summaries"] = base_filename_summaries
    # currently the protein list summary (each row is a protein, from uniprot etc) is a csv file
    pathdict["list_summary_csv"] = '%s_summary.csv' % base_filename_summaries
    # for SIMAP or BLAST downloads, gives a list of accessions that failed
    pathdict["failed_downloads_txt"] = '%s_failed_downloads.txt' % base_filename_summaries
    # add the base path for the sub-sequences (SE01, SE02, etc) added by the user
    pathdict["list_user_subseqs_csv"] = '%s_user_subseqs.csv' % base_filename_summaries
    pathdict["list_user_subseqs_xlsx"] = '%s_user_subseqs.xlsx' % base_filename_summaries

    pathdict["dfout01_uniprotcsv"] = '%s_uniprot.csv' % base_filename_summaries
    pathdict["dfout02_uniprotTcsv"] = '%s_uniprotT.csv' % base_filename_summaries
    pathdict["dfout03_uniprotxlsx"] = '%s_uniprot.xlsx' % base_filename_summaries
    pathdict["dfout04_uniprotcsv_incl_paths"] = '%s_uniprot_incl_paths.csv' % base_filename_summaries
    #pathdict["dfout05_simapcsv"] = '%s_simap.csv' % base_filename_summaries
    pathdict["dfout06_simapxlsx"] = '%s_simap.xlsx' % base_filename_summaries
    pathdict["dfout07_simapnonred"] = '%s_simapnonred.csv' % base_filename_summaries
    pathdict["dfout08_simap_AAIMON"] = '%s_simap_AAIMON.csv' % base_filename_summaries
    pathdict["dfout09_simap_AAIMON_02"] = '%s_simap_AAIMON_02.csv' % base_filename_summaries
    pathdict["dfout10_uniprot_gaps"] = '%s_gap_densities.csv' % base_filename_summaries
    pathdict["dfout11_gap_test_out_png"] = '%s_gap_test_out.png' % base_filename_summaries
    pathdict["dfout12"] = 0
    pathdict["dfout13"] = 0
    pathdict["csv_file_with_histogram_data"] = '%s_histogram.csv' % base_filename_summaries
    pathdict["csv_file_with_histogram_data_normalised"] = '%s_histogram_normalised.csv' % base_filename_summaries
    pathdict["csv_file_with_histogram_data_normalised_redundant_removed"] = '%s_histogram_normalised_redundant_removed.csv' % base_filename_summaries
    pathdict["csv_file_with_md5_for_each_query_sequence"] = '%s_query_md5_checksums.csv' % base_filename_summaries
    pathdict["csv_av_cons_ratio_all_proteins"] = '%s_cons_ratios_nonred_av.csv' % base_filename_summaries
    pathdict["csv_std_cons_ratio_all_proteins"] = '%s_cons_ratios_nonred_std.csv' % base_filename_summaries
    pathdict["create_graph_of_gap_density_png"] = '%s_create_graph_of_gap_density.png' % base_filename_summaries
    return pathdict