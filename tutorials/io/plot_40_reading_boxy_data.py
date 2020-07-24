# -*- coding: utf-8 -*-
r"""
.. _tut-importing-boxy-data:

=========================================================
Importing data from BOXY software and ISS Imagent devices
=========================================================

MNE includes various functions and utilities for reading optical imaging
data and optode locations.

.. contents:: Page contents
   :local:
   :depth: 2


.. _import-nirx:

BOXY (directory)
================================

BOXY recordings can be read in using :func:`mne.io.read_raw_boxy`.
The BOXY software and Imagent devices store data in a single .txt file
containing DC, AC, and Phase information for each source and detector
combination. Recording settings, such as the number of sources/detectors, and
the sampling rate of the recording, are also saved at the beginning of this
file. MNE will extract the raw DC, AC, and Phase data, along with the recording
settings.

If you have multiple channels montages and/or multiple blocks of data per
participant, with each montage and block combination being a separate data
file, then all of the applicable files for a given participant can be loaded
and combined. The files should follow a specific naming structure, containing
the montage and block information. Below is an example of file names for a
single participant:

    anc071a.001 = montage A, block 1, for participant 071, experiment ANC

    anc071a.002 = montage A, block 1, for participant 071, experiment ANC

    anc071b.001 = montage B, block 2, for participant 071, experiment ANC

    anc071b.002 = montage B, block 2, for participant 071, experiment ANC

Note that the extension for these files is now the block number (001, 002)
rather than .txt, which is the default extension saved by the BOXY software.
These file names and extensions may need to be changed after a recording has
been saved in BOXY. These files all need to be in the same folder for their
data to be read and combined with MNE.

"""  # noqa:E501
