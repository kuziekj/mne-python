"""
.. _tut-fnirs-processing:

Preprocessing optical imaging data from the Imagent hardware/boxy software
================================================================

This tutorial covers how to convert optical imaging data from raw measurements
to relative oxyhaemoglobin (HbO) and deoxyhaemoglobin (HbR) concentration.
Phase data from the recording is also processed and plotted in several ways.

 .. contents:: Page contents
    :local:
    :depth: 2

 Here we will work with the :ref:`fNIRS motor data <fnirs-motor-dataset>`.
"""
# sphinx_gallery_thumbnail_number = 1

import os
import numpy as np
import matplotlib.pyplot as plt
from itertools import compress
import re as re

import mne

# get our data
boxy_data_folder = mne.datasets.boxy_example.data_path()
boxy_raw_dir = os.path.join(boxy_data_folder, 'Participant-1')

# load AC and Phase data
raw_intensity_ac = mne.io.read_raw_boxy(boxy_raw_dir, 'AC',
                                        verbose=True).load_data()

raw_intensity_ph = mne.io.read_raw_boxy(boxy_raw_dir, 'Ph',
                                        verbose=True).load_data()

# get channel indices for our two montages
mtg_a = [raw_intensity_ac.ch_names[i_index] for i_index, i_label
         in enumerate(raw_intensity_ac.info['ch_names'])
         if re.search(r'S[1-5]_', i_label)]

mtg_b = [raw_intensity_ac.ch_names[i_index] for i_index, i_label
         in enumerate(raw_intensity_ac.info['ch_names'])
         if re.search(r'S([6-9]|10)_', i_label)]

# plot the raw data for each data type
# AC
scalings = dict(fnirs_raw=2e2, fnirs_ph=4e3, fnirs_od=2,
                hbo=2e-3, hbr=2e-3)

raw_intensity_ac.plot(n_channels=10, duration=20, scalings=scalings,
                      show_scrollbars=True)

# Phase
raw_intensity_ph.plot(n_channels=10, duration=20, scalings=scalings,
                      show_scrollbars=True)

# ###############################################################################
# # View location of sensors over brain surface
# # -------------------------------------------
# #
# # Here we validate that the location of sources-detector pairs and channels
# # are in the expected locations. Sources are bright red dots, detectors are
# # dark red dots, with source-detector pairs connected by white lines.

subjects_dir = os.path.dirname(mne.datasets.fetch_fsaverage())

# plot both montages together
fig = mne.viz.create_3d_figure(size=(800, 600), bgcolor='white')
fig = mne.viz.plot_alignment(raw_intensity_ac.info,
                             show_axes=True,
                             subject='fsaverage',
                             trans='fsaverage',
                             surfaces=['head-dense', 'brain'],
                             fnirs=['sources', 'detectors', 'pairs'],
                             mri_fiducials=True,
                             dig=True,
                             subjects_dir=subjects_dir,
                             fig=fig)
mne.viz.set_3d_view(figure=fig, azimuth=20, elevation=55, distance=0.6)

# ###############################################################################
# # Selecting channels appropriate for detecting neural responses
# # -------------------------------------------------------------
# #
# # First we remove channels that are too close together (short channels) to
# # detect a neural response (less than 3 cm distance between optodes).
# # These short channels can be seen in the figure above.
# # To achieve this we pick all the channels not considered to be short.

picks = mne.pick_types(raw_intensity_ac.info, meg=False, fnirs=True, stim=True)

dists = mne.preprocessing.nirs.source_detector_distances(
    raw_intensity_ac.info, picks=picks)

raw_intensity_ac.pick(picks[dists < 0.03])

# ###############################################################################
# # Converting from raw intensity to optical density
# # ------------------------------------------------
# #
# # The raw intensity values are then converted to optical density.
# # We will only do this for either DC or AC data since they are measures of
# # light intensity.

raw_od = mne.preprocessing.nirs.optical_density(raw_intensity_ac)

raw_od.plot(n_channels=len(raw_od.ch_names),
            duration=500, show_scrollbars=False, scalings=scalings)

# ###############################################################################
# # Evaluating the quality of the data
# # ----------------------------------
# #
# # At this stage we can quantify the quality of the coupling
# # between the scalp and the optodes using the scalp coupling index. This
# # method looks for the presence of a prominent synchronous signal in the
# # frequency range of cardiac signals across both photodetected signals.
# #
# # In this example the data is clean and the coupling is good for all
# # channels, so we will not mark any channels as bad based on the scalp
# # coupling index.

sci = mne.preprocessing.nirs.scalp_coupling_index(raw_od)

fig, ax = plt.subplots()
ax.hist(sci)
ax.set(xlabel='Scalp Coupling Index', ylabel='Count', xlim=[0, 1])

# ###############################################################################
# # In this example we will mark all channels with a SCI less than 0.5 as bad
# # (this dataset is quite clean, so no channels are marked as bad).

raw_od.info['bads'] = list(compress(raw_od.ch_names, sci < 0.5))

# ###############################################################################
# # At this stage it is appropriate to inspect your data
# # (for instructions on how to use the interactive data visualisation tool
# # see :ref:`tut-visualize-raw`)
# # to ensure that channels with poor scalp coupling have been removed.
# # If your data contains lots of artifacts you may decide to apply
# # artifact reduction techniques as described in :ref:`ex-fnirs-artifacts`.


# ###############################################################################
# # Converting from optical density to haemoglobin
# # ----------------------------------------------
# #
# # Next we convert the optical density data to haemoglobin concentration using
# # the modified Beer-Lambert law.

raw_haemo = mne.preprocessing.nirs.beer_lambert_law(raw_od)

raw_haemo.plot(n_channels=len(raw_haemo.ch_names), duration=500,
               show_scrollbars=False, scalings=scalings)

# ###############################################################################
# # Removing heart rate from signal
# # -------------------------------
# #
# # The haemodynamic response has frequency content predominantly below 0.5 Hz.
# # An increase in activity around 1 Hz can be seen in the data that is due to
# # the person's heart beat and is unwanted. So we use a low pass filter to
# # remove this. A high pass filter is also included to remove slow drifts
# # in the data.

fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(15, 6))

fig = raw_haemo.plot_psd(average=True, ax=axes)
fig.suptitle('Before filtering', weight='bold', size='x-large')
fig.subplots_adjust(top=0.88)

raw_haemo = raw_haemo.filter(0.05, 0.7, h_trans_bandwidth=0.2,
                             l_trans_bandwidth=0.02)

fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(15, 6))
fig = raw_haemo.plot_psd(average=True, ax=axes)
fig.suptitle('After filtering', weight='bold', size='x-large')
fig.subplots_adjust(top=0.88)

# ###############################################################################
# # Extract epochs
# # --------------
# #
# # Now that the signal has been converted to relative haemoglobin
# # concentration, and the unwanted heart rate component has been removed,
# # we can extract epochs related to each of the experimental conditions.
# #
# # First we extract the events of interest and visualise them to
# # ensure they are correct.

# # Since our events and timings for this data set are the same
# # across montages, we are going to find events for each montage separately
# # and combine them later

# All events
all_events = mne.find_events(raw_intensity_ac, stim_channel=['Markers a',
                                                             'Markers b'])

all_event_dict = {'Event_1': 1,
                  'Event_2': 2,
                  'Block 1 End': 1000,
                  'Block 2 End': 2000}

fig = mne.viz.plot_events(all_events)
fig.subplots_adjust(right=0.7)  # make room for the legend

raw_intensity_ac.plot(events=all_events, start=0, duration=10, color='gray',
                      event_color={1: 'r', 2: 'b', 1000: 'k', 2000: 'k'},
                      scalings=scalings)

# ###############################################################################
# # Next we define the range of our epochs, the rejection criteria,
# # baseline correction, and extract the epochs. We visualise the log of which
# # epochs were dropped.

# # We will make epochs from the ac-derived heamo data and the phase data
# # separately.

reject_criteria = None
tmin_ph, tmax_ph = -0.2, 2
tmin_ac, tmax_ac = -2, 10

all_haemo_epochs = mne.Epochs(raw_haemo, all_events,
                              event_id=all_event_dict, tmin=tmin_ac,
                              tmax=tmax_ac, reject=reject_criteria,
                              reject_by_annotation=False, proj=True,
                              baseline=(None, 0), preload=True, detrend=None,
                              verbose=True, event_repeated='drop')
all_haemo_epochs.plot_drop_log()

all_phase_epochs = mne.Epochs(raw_intensity_ph, all_events,
                              event_id=all_event_dict, tmin=tmin_ph,
                              tmax=tmax_ph, reject=None,
                              reject_by_annotation=False, proj=False,
                              baseline=(-0.2, 0), preload=True,
                              detrend=None, verbose=True,
                              event_repeated='drop')
all_phase_epochs.plot_drop_log()

# plot epochs
fig = all_haemo_epochs.plot(scalings=scalings)
fig = all_phase_epochs.plot(scalings=scalings)

# ###############################################################################
# # View consistency of responses across trials
# # -------------------------------------------
# #
# # Now we can view the haemodynamic response for our different events.

# Haemo plots
vmin_ac = -60
vmax_ac = 60

all_haemo_epochs['Event_1'].plot_image(combine='mean', vmin=vmin_ac,
                                       vmax=vmax_ac, ts_args=dict(
                                           ylim=dict(hbo=[vmin_ac, vmax_ac],
                                                     hbr=[vmin_ac, vmax_ac])),
                                       title='Haemo Event 1')

all_haemo_epochs['Event_2'].plot_image(combine='mean', vmin=vmin_ac,
                                       vmax=vmax_ac, ts_args=dict(
                                           ylim=dict(hbo=[vmin_ac, vmax_ac],
                                                     hbr=[vmin_ac, vmax_ac])),
                                       title='Haemo Event 2')

# Phase
vmin_ph = -180
vmax_ph = 180

all_phase_epochs['Event_1'].plot_image(combine='mean', vmin=vmin_ph,
                                       vmax=vmax_ph, title='Phase Event 1')

all_phase_epochs['Event_2'].plot_image(combine='mean', vmin=vmin_ph,
                                       vmax=vmax_ph, title='Phase Event 2')

# ###############################################################################
# # View consistency of responses across channels
# # ---------------------------------------------
# #
# # Similarly we can view how consistent the response is across the optode
# # pairs that we selected. All the channels in this data are located over the
# # motor cortex, and all channels show a similar pattern in the data.

# Haemo
evoked_event_1_ac = all_haemo_epochs['Event_1'].average()
evoked_event_2_ac = all_haemo_epochs['Event_2'].average()

fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(15, 6))
clim = dict(hbo=[-30, 30], hbr=[-30, 30])

evoked_event_1_ac.plot_image(axes=axes[:, 0],
                             titles=dict(hbo='HBO_Event_1', hbr='HBR_Event_1'),
                             clim=clim)
evoked_event_2_ac.plot_image(axes=axes[:, 1],
                             titles=dict(hbo='HBO_Event_2', hbr='HBR_Event_2'),
                             clim=clim)

# Phase
evoked_event_1_ph = all_phase_epochs['Event_1'].average()
evoked_event_2_ph = all_phase_epochs['Event_2'].average()

fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(15, 6))
clim = dict(fnirs_ph=[-180, 180])

evoked_event_1_ph.plot_image(axes=axes[0], titles='Event_1', clim=clim)
evoked_event_2_ph.plot_image(axes=axes[1], titles='Event_2', clim=clim)

# ###############################################################################
# # Plot standard haemodynamic response image
# # ----------------------------------
# #
# # Plot both the HbO and HbR on the same figure to illustrate the relation
# # between the two signals.

# # We can also plot a similar figure for phase data.

# Haemo
fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(15, 6))

evoked_dict_ac = {'Event_1': evoked_event_1_ac, 'Event_2': evoked_event_2_ac}

color_dict = {'Event_1': 'r', 'Event_2': 'b'}

mne.viz.plot_compare_evokeds(evoked_dict_ac, combine="mean", ci=0.95,
                             colors=color_dict, axes=axes.tolist())

# Phase
evoked_dict_ph = {'Event_1': evoked_event_1_ph, 'Event_2': evoked_event_2_ph}

color_dict = {'Event_1': 'r', 'Event_2': 'b'}

mne.viz.plot_compare_evokeds(evoked_dict_ph, combine="mean", ci=0.95,
                             colors=color_dict, title='Phase')

# ###############################################################################
# # View topographic representation of activity
# # -------------------------------------------
# #
# # Next we view how the topographic activity changes throughout the
# # haemodynamic and phase response.

# Haemo
times = np.arange(0.0, 10.0, 2.0)
topomap_args = dict(extrapolate='local')

fig = evoked_event_1_ac.plot_joint(times=times, topomap_args=topomap_args)
fig = evoked_event_2_ac.plot_joint(times=times, topomap_args=topomap_args)

# Phase
times = np.arange(0.0, 2.0, 0.5)
topomap_args = dict(extrapolate='local')

fig = evoked_event_1_ph.plot_joint(times=times, topomap_args=topomap_args,
                                   title='Event 1 Phase')
fig = evoked_event_2_ph.plot_joint(times=times, topomap_args=topomap_args,
                                   title='Event 2 Phase')

# ###############################################################################
# # Compare Events 1 and 2
# # ---------------------------------------
# #
# # We generate topo maps for events 1 and 2 to view the location of activity.
# # First we visualise the HbO activity.

# Haemo
fig, axes = plt.subplots(nrows=2, ncols=3, figsize=(9, 5),
                         gridspec_kw=dict(width_ratios=[1, 1, 0.1]))

topomap_args = dict(extrapolate='local', size=3, res=256, sensors='k.')
times = 1.0

all_haemo_epochs['Event_1'].average(picks='hbo').plot_topomap(times=times,
                                                              axes=axes[0, 0],
                                                              colorbar=False,
                                                              **topomap_args)

all_haemo_epochs['Event_2'].average(picks='hbo').plot_topomap(times=times,
                                                              axes=axes[0, 1:],
                                                              colorbar=True,
                                                              **topomap_args)

all_haemo_epochs['Event_1'].average(picks='hbr').plot_topomap(times=times,
                                                              axes=axes[1, 0],
                                                              colorbar=False,
                                                              **topomap_args)

all_haemo_epochs['Event_2'].average(picks='hbr').plot_topomap(times=times,
                                                              axes=axes[1, 1:],
                                                              colorbar=True,
                                                              **topomap_args)

for column, condition in enumerate(['Event 1', 'Event 2']):
    for row, chroma in enumerate(['HBO', 'HBR']):
        axes[row, column].set_title('{}: {}'.format(chroma, condition))
fig.tight_layout()


# Phase
fig, axes = plt.subplots(nrows=1, ncols=3, figsize=(9, 5),
                         gridspec_kw=dict(width_ratios=[1, 1, 0.1]))

topomap_args = dict(extrapolate='local', size=3, res=256, sensors='k.')
times = 1.0


all_phase_epochs['Event_1'].average().plot_topomap(times=times, axes=axes[0],
                                                   colorbar=False,
                                                   **topomap_args)

all_phase_epochs['Event_2'].average().plot_topomap(times=times, axes=axes[1:],
                                                   colorbar=True,
                                                   **topomap_args)

for column, condition in enumerate(['Event 1', 'Event 2']):
    axes[column].set_title('{}: {}'.format(chroma, condition))
fig.tight_layout()

# ###############################################################################
# # And we can plot the comparison at a single time point for two conditions.

# Haemo
fig, axes = plt.subplots(nrows=2, ncols=4, figsize=(9, 5),
                         gridspec_kw=dict(width_ratios=[1, 1, 1, 0.1]))
vmin, vmax, ts = -0.192, 0.992, 0.1
vmin = -5
vmax = 5

evoked_diff_ac = mne.combine_evoked([evoked_event_1_ac, -evoked_event_2_ac],
                                    weights='equal')

evoked_event_1_ac.plot_topomap(ch_type='hbo', times=ts, axes=axes[0, 0],
                               vmin=vmin, vmax=vmax,
                               colorbar=False, **topomap_args)

evoked_event_2_ac.plot_topomap(ch_type='hbo', times=ts, axes=axes[0, 1],
                               vmin=vmin, vmax=vmax,
                               colorbar=False, **topomap_args)

evoked_diff_ac.plot_topomap(ch_type='hbo', times=ts, axes=axes[0, 2:],
                            vmin=vmin, vmax=vmax,
                            colorbar=True, **topomap_args)

evoked_event_1_ac.plot_topomap(ch_type='hbr', times=ts, axes=axes[1, 0],
                               vmin=vmin, vmax=vmax,
                               colorbar=False, **topomap_args)

evoked_event_2_ac.plot_topomap(ch_type='hbr', times=ts, axes=axes[1, 1],
                               vmin=vmin, vmax=vmax,
                               colorbar=False, **topomap_args)

evoked_diff_ac.plot_topomap(ch_type='hbr', times=ts, axes=axes[1, 2:],
                            vmin=vmin, vmax=vmax,
                            colorbar=True, **topomap_args)

for column, condition in enumerate(['Event 1', 'Event 2', 'Difference']):
    for row, chroma in enumerate(['HBO', 'HBR']):
        axes[row, column].set_title('{}: {}'.format(chroma, condition))
fig.tight_layout()


# Phase
fig, axes = plt.subplots(nrows=1, ncols=4, figsize=(9, 5),
                         gridspec_kw=dict(width_ratios=[1, 1, 1, 0.1]))
vmin, vmax, ts = -0.192, 0.992, 0.1
vmin = -180
vmax = 180

evoked_event_1_ph.plot_topomap(times=ts, axes=axes[0], vmin=vmin, vmax=vmax,
                               colorbar=False, **topomap_args)

evoked_event_2_ph.plot_topomap(times=ts, axes=axes[1], vmin=vmin, vmax=vmax,
                               colorbar=False, **topomap_args)

evoked_diff_ph = mne.combine_evoked([evoked_event_1_ph, -evoked_event_2_ph],
                                    weights='equal')

evoked_diff_ph.plot_topomap(times=ts, axes=axes[2:], vmin=vmin, vmax=vmax,
                            colorbar=True, **topomap_args)

for column, condition in enumerate(['Event 1', 'Event 2', 'Difference']):
    axes[column].set_title('{}'.format(condition))
fig.tight_layout()

# #############################################################################
# # Lastly, we can also look at the individual waveforms to see what is
# # driving the topographic plot above.

# HBO
fig, axes = plt.subplots(nrows=1, ncols=1, figsize=(6, 4))
mne.viz.plot_evoked_topo(evoked_event_1_ac.copy().pick('hbo'),
                         color='b', axes=axes, legend=False)
mne.viz.plot_evoked_topo(evoked_event_2_ac.copy().pick('hbo'),
                         color='r', axes=axes, legend=False)

# Tidy the legend
leg_lines = [line for line in axes.lines if line.get_c() == 'b'][:1]
leg_lines.append([line for line in axes.lines if line.get_c() == 'r'][0])
fig.legend(leg_lines, ['HBO Event 1', 'HBO Event 2'], loc='lower right')


# HBR
fig, axes = plt.subplots(nrows=1, ncols=1, figsize=(6, 4))
mne.viz.plot_evoked_topo(evoked_event_1_ac.copy().pick('hbr'),
                         color='b', axes=axes, legend=False)
mne.viz.plot_evoked_topo(evoked_event_2_ac.copy().pick('hbr'),
                         color='r', axes=axes, legend=False)

# Tidy the legend
leg_lines = [line for line in axes.lines if line.get_c() == 'b'][:1]
leg_lines.append([line for line in axes.lines if line.get_c() == 'r'][0])
fig.legend(leg_lines, ['HBR Event 1', 'HBR Event 2'], loc='lower right')


# Phase
fig, axes = plt.subplots(nrows=1, ncols=1, figsize=(6, 4))
mne.viz.plot_evoked_topo(evoked_event_1_ph, color='b', axes=axes, legend=False)
mne.viz.plot_evoked_topo(evoked_event_2_ph, color='r', axes=axes, legend=False)

# Tidy the legend
leg_lines = [line for line in axes.lines if line.get_c() == 'b'][:1]
leg_lines.append([line for line in axes.lines if line.get_c() == 'r'][0])
fig.legend(leg_lines, ['Phase Event 1', 'Phase Event 2'], loc='lower right')
