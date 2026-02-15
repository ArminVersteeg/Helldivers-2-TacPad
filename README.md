# Helldivers 2 TacPad (Kivy)

A Helldivers 2-inspired stratagem input interface built with Python and
Kivy.

## Overview

This project recreates the in-game TacPad system where directional arrow
combinations are entered to trigger stratagems. It includes a boot
sequence, animated transitions, audio feedback, and inactivity handling.
Made for cosplay, using a Raspbery PI and a touchscreen panel.

## Features

-   Custom boot screen with loading bar and Helldivers music
-   Directional arrow input system
-   Stratagem recognition logic
-   Stratagem request display screen
-   Audio feedback

## Requirements

-   Python 3.10+
-   Kivy 2.3.0
-   Pygame

Install dependencies:

    pip install kivy pygame

## Running

From the project root directory:

    python main.py

## Project Structure

Helldivers 2 TacPad/
│
├── audio/
├── fonts/
├── images/
│   ├── arrows
│   ├── background
│   └── stratagems
│
├── main.py                # Main Python script.
├── stratagems.py          # List with all the Stratagems and arrow combinations.
└── README.md

## Disclaimer

This is a fan-made project inspired by Helldivers 2. Not affiliated with
Arrowhead Game Studios.
