# Project Plan

## Subject Area

- Tool for downloading and synchronizing YouTube playlists.
- Focuses on reliable batch downloading, format selection (audio and/or video), configurable quality and keeping local copies synced with playlist changes.
- Targets power users and archivists who need large-scale, repeatable playlist archiving and ongoing synchronization, with GUI interfaces.

## Problem

- Users and power-users who manage large or frequently changing YouTube playlists lack a dependable, configurable tool that:
  - correctly detects and downloads new videos while avoiding duplicates,
  - and can be configured easily via file or GUI for repeatable workflows.

## Users Definition

Individuals who need to download a large number of videos or audio files from a YouTube playlist and keep it updated

## Functionality Definition

- Can download:
  - Video only
  - Audio only
  - Both video and audio
- Can update the playlist (download only newly added videos)
- Can delete videos that are no longer in the playlist
- Has configuration for:
  - Quality
  - Download type (audio, video)
  - Save directory
  - Use of aria2c
  - aria2c-related settings
  - GUI settings

## GUI

- Has buttons for all features
- Allows adjusting all settings from the GUI
- Modern Design


## Platform

- Desktop application
- Optional:
  - Web App
  - Android App

## Languages

- Backend
  - Python
- Frontend
  - qt ?
  - Tkinter?