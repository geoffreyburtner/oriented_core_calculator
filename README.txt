================================================================================
 README
 Oriented core: alpha / beta / gamma  ->  dip / dip-azimuth / trend / plunge
================================================================================
Created by: Geoff Burtner (c) 2026

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).

This means you are free to use, modify, and distribute this software, but if you run a
modified version of it as a network service, you must make the source code of your
modified version available to the users of that service. See the [LICENSE.txt]
file for the full license text.

This software is provided "as is", without warranty of any kind, express or implied,
including but not limited to accuracy, merchantability, or fitness for a particular
purpose. Use at your own risk.


WHAT THIS SCRIPT DOES
----------------------
OrientedCore_alphaBeta_surveyReduction.py converts oriented-core logging angles (alpha, beta, optional
gamma) plus the drillhole's trend and inclination into geographic structural
orientations:

    - a plane               -> dip and dip azimuth
    - a lineation (gamma)   -> trend and plunge

It can be used one measurement at a time (interactively or via command-line
flags) or in batch over a CSV file of many measurements at once.


REQUIREMENTS
-------------
- Python 3.7 or later. No third-party packages are required (only the
  standard library: argparse, csv, math, sys).
- Check Python is installed: python --version or python3 --version


INPUT CONVENTIONS (read this before entering data)
----------------------------------------------------
Orientation line is assumed to be the BOTTOM OF HOLE. Other orientation line standards are discouraged. 
If you insist on using top-of-hole orientation lines, beta measurements must be inverted before using this tool.


  alpha   acute angle between the core axis and the plane.         0 - 90 deg

  beta    measured CLOCKWISE looking DOWN-HOLE, from the           0 - 359 deg
          bottom-of-hole (BOH) reference line to the LOWER
          point of the elliptical intersection.

  gamma   measured the same way, from that lower ellipse           0 - 359 deg
          point to the lineation. OPTIONAL - leave blank for       (optional)
          a plane-only measurement (no lineation).

  trend   hole trend / azimuth, from north.                        0 - 359 deg

  incl    hole inclination from horizontal. INDUSTRY STANDARD:    -90 to 90 deg
          NEGATIVE = below horizontal (a normal downward hole),
          POSITIVE = above horizontal (an upward / raise hole).
          A hole shot at "-60" is 60 degrees below horizontal.
          NOTE: Orientation tools are unreliable in near-vertical holes.
          This calculator will permit calculation for measurements in these holes,
          but the accuracy of the measurements is not guaranteed.

If your tool measures beta or gamma counter-clockwise looking down-hole
instead of clockwise, use the --beta-ccw / --gamma-ccw flags (command-line
mode) or pass beta_cw=False / gamma_cw=False if calling the function directly
from another Python script.

Any value entered outside its expected range above still gets calculated (the
underlying math works for any angle) but prints a WARNING flagging it as a
likely data-entry mistake worth double-checking.


HOW TO RUN IT - THREE MODES
-----------------------------

1) INTERACTIVE MODE (no arguments - good for a single one-off check)

       python OrientedCore_alphaBeta_surveyReduction.py

   It will prompt for each value in turn, print the result, then ask if you
   want to convert another. Type 'q' at that prompt to quit.

2) SINGLE MEASUREMENT, ONE LINE (good for scripting or quick lookups)

       python OrientedCore_alphaBeta_surveyReduction.py --alpha 30 --beta 45 --gamma 20 --trend 30 --incl -60

   --gamma is optional - omit it  for a plane-only result. Run
   "python OrientedCore_alphaBeta_surveyReduction.py -h" to see every available flag.

3) CSV BATCH MODE (good for many measurements at once - see full
   instructions below)

       python OrientedCore_alphaBeta_surveyReduction.py --csv input.csv --out results.csv


CSV BATCH MODE - FULL INSTRUCTIONS
-------------------------------------

Step 1 - Build the input CSV

  Create a plain-text, comma-separated file with a header row using these
  column names (case-sensitive):

       id, alpha, beta, gamma, trend, incl

  Column details:
    id      OPTIONAL. Any label - interval name, depth, sample number, etc.
            Carried straight through to the output unchanged.
    alpha   REQUIRED. 0 - 90.
    beta    REQUIRED. 0 - 359.
    gamma   OPTIONAL. 0 - 359, or leave the cell completely BLANK for a
            plane-only row (no lineation). Don't enter 0 unless gamma is
            genuinely zero - a blank and a zero are treated differently.
    trend   REQUIRED. Hole trend/azimuth, 0 - 359.
    incl    REQUIRED. Hole inclination, negative-down / positive-up (see
            conventions above). This column may also be named 'inclination'
            or (legacy) 'plunge' - all three are read the same negative-down
            way, so older files still work.

  The easiest way to build this is in Excel: lay out the same columns, then
  File > Save As > choose "CSV (Comma delimited)".

  Example file (blank templet also provided as input.csv):

       id,alpha,beta,gamma,trend,incl
       HOLE1-12.4m,30,45,20,30,-60
       HOLE1-13.1m,45,90,,30,-60
       HOLE1-14.8m,12,310,,210,-72

  Rows 2 and 3 above have a blank gamma, so they return a plane (dip / dip
  azimuth) only - no lineation.

Step 2 - Run the conversion

       python OrientedCore_alphaBeta_surveyReduction.py --csv input.csv --out results.csv

  Leave off "--out results.csv" to print the results straight to the screen
  instead of writing a file:

       python OrientedCore_alphaBeta_surveyReduction.py --csv input.csv

Step 3 - Read the output

  The output CSV has every input column plus:

       dip, dip_azimuth, lin_trend, lin_plunge, warnings

  lin_trend / lin_plunge are left blank for any row with no gamma.  For a 
  measurement with a gamma, dip and dip_azimuth is the attitude of the
  plane that the lineation was measured on. Warnings column lists anything 
  outside the expected input range for that row (e.g. "alpha=95.0 is outside 
  the expected 0-90 deg range") - the row is still calculated, the warning is 
  just a data-entry flag. Warnings are also printed to the terminal, tagged 
  with the row's id, as the file is processed. Warnings will also be given
  for any entry where the hole inclination is between 88-90 degrees as 
  core orientation tools are generally unreliable with near-vertical holes.
  Use these measurements at your own risk.

  Open results.csv in Excel or any spreadsheet program to review.


TROUBLESHOOTING
-----------------
- "python: command not found"          -> try "python3" instead of "python".
- A row is missing dip/azimuth output  -> check alpha, beta, trend and incl
                                           are all filled in for that row
                                           (these four are required).
- Lineation columns are blank          -> that row had no gamma value, which
                                           is expected behaviour, not an error.
- Unexpected dip/azimuth values        -> check the sign of incl. Downward
                                           holes are NEGATIVE in this script.
                                           A hole entered as +60 is treated as
                                           pointing UP, not down.
- A warning appears but the row still
  has a result                         -> warnings do not block calculation;
                                           they only flag a value outside its
                                           normal range for you to double-check
                                           against your source data.


RELATED FILES
---------------
  OrientedCore_alphaBeta_surveyReduction.py       - the script itself
  input.csv                                       - a ready-to-edit example input file
  

This is a geometry conversion tool only. It does not replace orientation QC, which still governs whether a given alpha/beta is
trustworthy in the first place.
================================================================================
