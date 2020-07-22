# Authors: Kyle Mathewson, Jonathan Kuziek <kuziekj@ualberta.ca>
#
# License: BSD (3-clause)

import glob as glob
import re as re

import numpy as np

from ..base import BaseRaw
from ..meas_info import create_info
from ...utils import logger, verbose, fill_doc


@fill_doc
def read_raw_boxy(fname, datatype='AC', multi_file=False,
                  preload=False, verbose=None):
    """Reader for a BOXY optical imaging recording.

    Parameters
    ----------
    fname : str
        Path to the BOXY data folder.
    datatype : str
        Type of data to return (AC, DC, or Ph).
    multi_file : bool
        If True, load multiple boxy files per participant. Expects files to be
        named a specific way, specifying block and montage. For example:
        1anc071a.001 = Montage A, Block 1; 1anc071b.002 = Montage B, Block 2
        If False, only load a single boxy file per participant. Name does not
        matter in this case, but file extension should be .txt.
    %(preload)s
    %(verbose)s

    Returns
    -------
    raw : instance of RawBOXY
        A Raw object containing BOXY data.

    See Also
    --------
    mne.io.Raw : Documentation of attribute and methods.
    """
    return RawBOXY(fname, datatype, multi_file, preload, verbose)


@fill_doc
class RawBOXY(BaseRaw):
    """Raw object from a BOXY optical imaging file.

    Parameters
    ----------
    fname : str
        Path to the BOXY data folder.
    datatype : str
        Type of data to return (AC, DC, or Ph).
    multi_file : bool
        If True, load multiple boxy files per participant. Expects files to be
        named a specific way, specifying block and montage. For example:
        1anc071a.001 = Montage A, Block 1; 1anc071b.002 = Montage B, Block 2
        If False, only load a single boxy file per participant. Name does not
        matter in this case, but file extension should be .txt.
    %(preload)s
    %(verbose)s

    See Also
    --------
    mne.io.Raw : Documentation of attribute and methods.
    """

    @verbose
    def __init__(self, fname, datatype='AC', multi_file=False, preload=False,
                 verbose=None):
        logger.info('Loading %s' % fname)

        # Check if required files exist and store names for later use.
        files = dict()
        if multi_file:
            key = '*.[000-999]*'
        else:
            key = '*.txt'
        print(fname)
        files[key] = [glob.glob('%s/*%s' % (fname, key))]

        # Make sure filenames are in order.
        files[key][0].sort()
        if len(files[key]) != 1:
            raise RuntimeError('Expect one %s file, got %d' %
                               (key, len(files[key]),))
        files[key] = files[key][0]

        # Determine which data type to return.
        if datatype in ['AC', 'DC', 'Ph']:
            data_types = [datatype]
        else:
            raise RuntimeError('Expect AC, DC, or Ph, got %s' % datatype)

        # If loading multiple files per participant,
        # determine how many blocks we have per montage.
        if multi_file:
            blk_names = list()
            mtg_names = list()
            mtgs = re.findall(r'\w\.\d+', str(files['*.[000-999]*']))
            [mtg_names.append(i_mtg[0]) for i_mtg in mtgs
                if i_mtg[0] not in mtg_names]
            for i_mtg in mtg_names:
                temp = list()
                [temp.append(ii_mtg[2:]) for ii_mtg in mtgs
                 if ii_mtg[0] == i_mtg]
                blk_names.append(temp)
        else:
            blk_names = [['001']]
            mtg_names = ['a']

        # Read header file and grab some info.
        detect_num = list()
        source_num = list()
        aux_num = list()
        ccf_ha = list()
        srate = list()
        start_line = list()
        end_line = list()
        filetype = ['parsed' for i_file in files[key]]
        for file_num, i_file in enumerate(files[key], 0):
            with open(i_file, 'r') as data:
                for line_num, i_line in enumerate(data, 1):
                    if '#DATA ENDS' in i_line:
                        # Data ends just before this.
                        end_line.append(line_num - 1)
                        break
                    if 'Detector Channels' in i_line:
                        detect_num.append(int(i_line.rsplit(' ')[0]))
                    elif 'External MUX Channels' in i_line:
                        source_num.append(int(i_line.rsplit(' ')[0]))
                    elif 'Auxiliary Channels' in i_line:
                        aux_num.append(int(i_line.rsplit(' ')[0]))
                    elif 'Waveform (CCF) Frequency (Hz)' in i_line:
                        ccf_ha.append(float(i_line.rsplit(' ')[0]))
                    elif 'Update Rate (Hz)' in i_line:
                        srate.append(float(i_line.rsplit(' ')[0]))
                    elif 'Updata Rate (Hz)' in i_line:
                        srate.append(float(i_line.rsplit(' ')[0]))
                    elif '#DATA BEGINS' in i_line:
                        # Data should start a couple lines later.
                        start_line.append(line_num + 2)
                    elif 'exmux' in i_line:
                        filetype[file_num] = 'non-parsed'

        # Label each channel in our data.
        # Data is organised by channels x timepoint, where the first
        # 'source_num' rows correspond to the first detector, the next
        # 'source_num' rows correspond to the second detector, and so on.
        boxy_labels = list()
        for mtg_num, i_mtg in enumerate(mtg_names, 0):
            for det_num in range(detect_num[::len(blk_names[0])][mtg_num]):
                for src_num in range(source_num[::len(blk_names[0])][mtg_num]):
                    boxy_labels.append('S' + str(src_num + 1) +
                                       '_D' + str(det_num + 1) +
                                       '_' + str(mtg_num + 1))

        # Determine channel types.
        if datatype == 'Ph':
            chan_type = 'fnirs_fd_phase'
        else:
            chan_type = 'fnirs_cw_amplitude'

        ch_types = ([chan_type for i_chan in boxy_labels])

        # Create info structure.
        info = create_info(boxy_labels, srate[0], ch_types=ch_types)

        raw_extras = {'source_num': source_num,
                      'detect_num': detect_num,
                      'start_line': start_line,
                      'end_line': end_line,
                      'filetype': filetype,
                      'files': files[key],
                      'montages': mtg_names,
                      'blocks': blk_names,
                      'data_types': data_types,
                      }

        # Check data start lines.
        if len(set(start_line)) == 1:
            print('Start lines the same!')
        else:
            print('Start lines different!')

        # Check data end lines.
        if len(set(end_line)) == 1:
            print('End lines the same!')
        else:
            print('End lines different!')

        # Make sure data lengths are the same.
        data_length = ([end_line[i_line] - start_line[i_line] for i_line,
                        line_num in enumerate(start_line)])

        if len(set(data_length)) == 1:
            print('Data sizes are the same!')
        else:
            print('Data sizes are different!')

        print('Start Line: ', start_line[0])
        print('End Line: ', end_line[0])
        print('Original Difference: ', end_line[0] - start_line[0])
        first_samps = start_line[0]
        print('New first_samps: ', first_samps)
        diff = end_line[0] - (start_line[0])

        # Number if rows in data file depends on data file type.
        if filetype[0] == 'non-parsed':
            last_samps = ((diff * len(blk_names[0])) // (source_num[0]))
        elif filetype[0] == 'parsed':
            last_samps = diff * len(blk_names[0])

        # First sample is technically sample 0, not the start line in the file.
        first_samps = 0

        print('New last_samps: ', last_samps)
        print('New Difference: ', last_samps - first_samps)

        super(RawBOXY, self).__init__(
            info, preload, filenames=[fname], first_samps=[first_samps],
            last_samps=[last_samps - 1],
            raw_extras=[raw_extras], verbose=verbose)

    def _read_segment_file(self, data, idx, fi, start, stop, cals, mult):
        """Read a segment of data from a file.

        Boxy file organises data in two ways, parsed or un-parsed.
        Regardless of type, output has (n_montages x n_sources x n_detectors
        + n_marker_channels) rows, and (n_timepoints x n_blocks) columns.
        """
        source_num = self._raw_extras[fi]['source_num']
        detect_num = self._raw_extras[fi]['detect_num']
        start_line = self._raw_extras[fi]['start_line']
        end_line = self._raw_extras[fi]['end_line']
        filetype = self._raw_extras[fi]['filetype']
        data_types = self._raw_extras[fi]['data_types']
        montages = self._raw_extras[fi]['montages']
        blocks = self._raw_extras[fi]['blocks']
        boxy_files = self._raw_extras[fi]['files']

        # Possible detector names.
        detectors = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K',
                     'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V',
                     'W', 'X', 'Y', 'Z']

        # Load our optical data.
        all_data = list()

        # Loop through montages.
        for i_mtg, mtg_name in enumerate(montages):
            all_blocks = list()

            # Loop through blocks.
            for i_blk, blk_name in enumerate(blocks[i_mtg]):
                file_num = i_blk + (i_mtg * len(blocks[i_mtg]))
                boxy_file = boxy_files[file_num]
                boxy_data = list()

                # Loop through our data.
                with open(boxy_file, 'r') as data_file:
                    for line_num, i_line in enumerate(data_file, 1):
                        if line_num == (start_line[i_blk] - 1):

                            # Grab column names.
                            col_names = np.asarray(
                                re.findall(r'\w+\-\w+|\w+\-\d+|\w+',
                                           i_line.rsplit(' ')[0]))
                        if (line_num > start_line[file_num] and
                                line_num <= end_line[file_num]):

                            # Grab actual data.
                            boxy_data.append(i_line.rsplit(' '))

                # Get number of sources.
                sources = np.arange(1, source_num[file_num] + 1, 1)

                # Grab the individual data points for each column.
                boxy_data = [re.findall(r'[-+]?\d*\.?\d+', i_row[0])
                             for i_row in boxy_data]

                # Make variable to store our data as an array
                # rather than list of strings.
                boxy_length = len(col_names)
                boxy_array = np.full((len(boxy_data), boxy_length), np.nan)
                for ii, i_data in enumerate(boxy_data):

                    # Need to make sure our rows are the same length.
                    # This is done by padding the shorter ones.
                    padding = boxy_length - len(i_data)
                    boxy_array[ii] = np.pad(np.asarray(i_data, dtype=float),
                                            (0, padding), mode='empty')

                # Grab data from the other columns that aren't AC, DC, or Ph.
                meta_data = dict()
                keys = ['time', 'record', 'group', 'exmux', 'step', 'mark',
                        'flag', 'aux1', 'digaux']
                for i_detect in detectors[0:detect_num[file_num]]:
                    keys.append('bias-' + i_detect)

                # Data that isn't in our boxy file will be an empty list.
                for key in keys:
                    meta_data[key] = (boxy_array[:,
                                      np.where(col_names == key)[0][0]] if
                                      key in col_names else list())

                # Make some empty variables to store our data.
                if filetype[file_num] == 'non-parsed':
                    data_ = np.zeros(((((detect_num[file_num] *
                                        source_num[file_num]) *
                                        len(data_types))),
                                      int(len(boxy_data) /
                                          source_num[file_num])))
                elif filetype[file_num] == 'parsed':
                    data_ = np.zeros(((((detect_num[file_num] *
                                         source_num[file_num]) *
                                        len(data_types))),
                                      int(len(boxy_data))))

                # Loop through data types.
                for i_data in data_types:

                    # Loop through detectors.
                    for i_detect in detectors[0:detect_num[file_num]]:

                        # Loop through sources.
                        for i_source in sources:

                            # Determine where to store our data.
                            index_loc = (detectors.index(i_detect) *
                                         source_num[file_num] +
                                         (i_source - 1) +
                                         (data_types.index(i_data) *
                                         (source_num[file_num] *
                                          detect_num[file_num])))

                            # Need to treat our filetypes differently.
                            if filetype[file_num] == 'non-parsed':

                                # Non-parsed saves timepoints in groups and
                                # this should account for that.
                                time_points = np.arange(
                                    i_source - 1,
                                    int(meta_data['record'][-1]) *
                                    source_num[file_num],
                                    source_num[file_num])

                                # Determine which channel to
                                # look for in boxy_array.
                                channel = np.where(col_names == i_detect +
                                                   '-' + i_data)[0][0]

                                # Save our data based on data type.
                                data_[index_loc, :] = boxy_array[time_points,
                                                                 channel]

                            elif filetype[file_num] == 'parsed':

                                # Which channel to look for in boxy_array.
                                channel = np.where(col_names == i_detect +
                                                   '-' + i_data +
                                                   str(i_source))[0][0]

                                # Save our data based on data type.
                                data_[index_loc, :] = boxy_array[:, channel]

                all_blocks.append(data_)

            all_data.extend(np.hstack(all_blocks))

        # Change data to array.
        all_data = np.asarray(all_data)

        print('Blank Data shape: ', data.shape)
        print('Input Data shape: ', all_data.shape)

        # Place our data into the data object in place.
        data[:] = all_data

        return data
