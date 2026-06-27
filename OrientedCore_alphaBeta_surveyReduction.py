#!/usr/bin/env python3
"""
Oriented Core Survey Reduction: Alpha/Beta/Gamma to Dip/Dip Direction/Trend/Plunge.
Written By: Geoff Burtner (c) 2026

----------------------------------------------------------------------
LICENSE: GNU AGPLv3
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
----------------------------------------------------------------------

Converts alpha / beta / gamma core-logging angles (plus the hole's trend and
plunge) into geographic structural orientations:
    - plane   -> dip and dip azimuth
    - lineation (needs gamma) -> trend and plunge

Conventions
-----------

This project assumes that the orientation line is the BOTTOM OF HOLE. Use of other conventions 
are discouraged. To use this calculator with top-of-hole or other conventions, the beta value will 
need corrected accordingly.

alpha   : acute angle between the core axis and the plane (0-90 deg).
beta    : measured CLOCKWISE looking DOWN-HOLE, from the bottom-of-hole (BOH)
          reference line to the LOWER point of the elliptical intersection
          (0-360 deg).
gamma   : measured around the plane, same sense, from that lower ellipse point
          to the lineation (0-360 deg). Optional - omit for a plane only.
trend   : hole azimuth, 0-360 deg from north.
incl    : hole inclination from horizontal (industry / drillhole-log standard):
          NEGATIVE = below horizontal (downward hole), POSITIVE = above
          horizontal (upward / raise hole), 0 = horizontal. Valid range -90 to 90.
          A hole shot at "-60" is 60 deg below horizontal (a normal down-hole).

Input validation
-----------------
alpha, beta, gamma, trend and inclination are each checked against their
expected range (alpha 0-90, beta/gamma 0-359, trend 0-359, inclination
-90 to 90). Values outside that range print a WARNING but are still used in
the calculation - the maths is valid for any angle, the warning is just a
data-entry sanity check.

If your tool measures beta or gamma counter-clockwise, pass beta_cw=False
and/or gamma_cw=False (or negate the angle yourself).

Usage
-----
Interactive:      OrientedCore_alphaBeta_surveyReduction.py
Single, one line: OrientedCore_alphaBeta_surveyReduction.py --alpha 30 --beta 45 --gamma 20 \
                                           --trend 30 --incl -60
Batch a CSV:      OrientedCore_alphaBeta_surveyReduction.py --csv input.csv --out results.csv

CSV batch mode - full instructions
-----------------------------------
1. Build a CSV (plain text, comma-separated - export from Excel with "Save As >
   CSV") with one row per measurement and a header row using these column
   names:

       id, alpha, beta, gamma, trend, incl

   - id     optional. Any text/number to identify the interval (e.g. an
            interval ID or depth). Carried through to the output unchanged.
   - alpha  required. 0-90.
   - beta   required. 0-359.
   - gamma  optional. 0-359, or leave the cell BLANK for a plane-only row
            (no lineation). Do not write 0 unless gamma is genuinely 0.
   - trend  required. Hole trend/azimuth, 0-359.
   - incl   required. Hole inclination, industry convention: NEGATIVE = down,
            POSITIVE = up (a hole shot at "-60" is 60 deg below horizontal).
            The column may also be named 'inclination' or (legacy) 'plunge' -
            all three are read the same way (negative-down).

   Example file (save as input.csv):

       id,alpha,beta,gamma,trend,incl
       HOLE1-12.4m,30,45,20,30,-60
       HOLE1-13.1m,45,90,,30,-60
       HOLE1-14.8m,12,310,,210,-72

   Row 2 above has no gamma - it produces a dip/dip-azimuth only, with the
   lineation columns left blank in the output.

2. Run it:

        OrientedCore_alphaBeta_surveyReduction.py --csv input.csv --out results.csv

   Leave off --out to print the results straight to the terminal instead of
   writing a file:

        OrientedCore_alphaBeta_surveyReduction.py --csv input.csv

3. The output CSV has one row per input row, with these added columns:

       dip, dip_azimuth, lin_trend, lin_plunge, warnings

   lin_trend/lin_plunge are blank for rows with no gamma. The warnings column
   lists anything outside the expected range (e.g. "alpha=95.0 is outside the
   expected 0-90 deg range") - the row is still calculated, the warning is
   just a data-entry flag, the same as the spreadsheet's Warnings column.
   Per-row warnings are also printed to the terminal as the file is processed.

4. Open results.csv in Excel (or any spreadsheet program) to review.
"""

import argparse
import csv
import math
import sys


def _unit_from_trend_plunge(trend_deg, plunge_deg):
    """Down-hole core-axis unit vector in ENU (East, North, Up)."""
    t, p = math.radians(trend_deg), math.radians(plunge_deg)
    return (math.cos(p) * math.sin(t),
            math.cos(p) * math.cos(t),
            -math.sin(p))


def validate_inputs(alpha, beta, gamma, trend, inclination):
    """Return a list of warning strings for any value outside its expected
    range. Does not raise or block. The calculation is still valid for any
    angle, this is purely a data-entry sanity check. Inclination follows the
    industry convention: negative = down, positive = up."""
    warnings = []
    if not (0 <= alpha <= 90):
        warnings.append(f"alpha={alpha} is outside the expected 0-90 deg range")
    if not (0 <= beta < 360):
        warnings.append(f"beta={beta} is outside the expected 0-359 deg range")
    if gamma is not None and gamma != "":
        g = float(gamma)
        if not (0 <= g < 360):
            warnings.append(f"gamma={gamma} is outside the expected 0-359 deg range")
    if not (0 <= trend < 360):
        warnings.append(f"hole trend={trend} is outside the expected 0-359 deg range")
    if not (-90 <= inclination <= 90):
        warnings.append(
            f"hole inclination={inclination} is outside the expected -90 to 90 deg range")
    return warnings


def _print_warnings(warnings, label=None):
    if not warnings:
        return
    prefix = f"WARNING [{label}]: " if label else "WARNING: "
    for w in warnings:
        print(prefix + w, file=sys.stderr)


def abg_to_orientation(alpha, beta, gamma, trend, inclination,
                       beta_cw=True, gamma_cw=True):
    """
    Return a dict with dip, dip_azimuth and (if gamma given) trend, plunge.

    Parameters are in degrees. Gamma may be None to skip the lineation.
    Inclination uses the industry convention: NEGATIVE = down, POSITIVE = up.
    It is negated here to the internal positive-down value used by the
    (verified) vector maths below...because that was how I figured it out first and don't want to re-derive everything...
    """
    plunge = -inclination                # industry (-down) -> internal (+down)
    a = math.radians(alpha)
    b = math.radians(beta * (1 if beta_cw else -1))
    t = math.radians(trend)
    pp = math.radians(plunge)

    # Core-frame basis vectors in ENU
    aE, aN, aU = (math.cos(pp) * math.sin(t),
                  math.cos(pp) * math.cos(t),
                  -math.sin(pp))                      # down-hole axis = a_hat
    bE, bN, bU = (-math.sin(pp) * math.sin(t),
                  -math.sin(pp) * math.cos(t),
                  -math.cos(pp))                      # bottom-of-hole ref = b_hat
    cE = aN * bU - aU * bN                            # c = a x b
    cN = aU * bE - aE * bU
    cU = aE * bN - aN * bE

    if abs(plunge) >= 88.0:
        print("  WARNING: near-vertical hole - the BOH reference (beta datum) "
              "is poorly defined; results are unreliable.", file=sys.stderr)

    # Pole to the plane
    sa, ca, cb, sb = math.sin(a), math.cos(a), math.cos(b), math.sin(b)
    pE = -sa * aE + ca * cb * bE + ca * sb * cE
    pN = -sa * aN + ca * cb * bN + ca * sb * cN
    pU = -sa * aU + ca * cb * bU + ca * sb * cU
    if pU < 0:                                        # upper hemisphere
        pE, pN, pU = -pE, -pN, -pU

    dip = math.degrees(math.acos(max(-1.0, min(1.0, pU))))
    dip_azimuth = math.degrees(math.atan2(pE, pN)) % 360.0

    result = {"dip": dip, "dip_azimuth": dip_azimuth,
              "trend": None, "plunge": None}

    # Lineation
    if gamma is not None and gamma != "":
        g = math.radians(float(gamma) * (1 if gamma_cw else -1))
        g1E = ca * aE + sa * (cb * bE + sb * cE)
        g1N = ca * aN + sa * (cb * bN + sb * cN)
        g1U = ca * aU + sa * (cb * bU + sb * cU)
        g2E = -sb * bE + cb * cE
        g2N = -sb * bN + cb * cN
        g2U = -sb * bU + cb * cU
        LE = math.cos(g) * g1E + math.sin(g) * g2E
        LN = math.cos(g) * g1N + math.sin(g) * g2N
        LU = math.cos(g) * g1U + math.sin(g) * g2U
        if LU > 0:                                    # force to point down
            LE, LN, LU = -LE, -LN, -LU
        result["plunge"] = math.degrees(math.asin(max(-1.0, min(1.0, -LU))))
        result["trend"] = math.degrees(math.atan2(LE, LN)) % 360.0

    return result


def _fmt(r):
    s = (f"Dip {r['dip']:.1f} deg  toward azimuth {r['dip_azimuth']:.1f} deg "
         f"(dip/dip-dir = {r['dip']:.0f}/{r['dip_azimuth']:03.0f})")
    if r["trend"] is not None:
        s += (f"\nLineation: trend {r['trend']:.1f} deg, "
              f"plunge {r['plunge']:.1f} deg "
              f"(plunge->trend = {r['plunge']:.0f}->{r['trend']:03.0f})")
    return s


def _run_csv(path, out):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    fields = ["id", "alpha", "beta", "gamma", "trend", "incl",
              "dip", "dip_azimuth", "lin_trend", "lin_plunge", "warnings"]
    out_rows = []
    for row in rows:
        g = row.get("gamma", "")
        alpha, beta = float(row["alpha"]), float(row["beta"])
        trend = float(row["trend"])
        incl_raw = (row.get("incl") if row.get("incl") not in (None, "")
                    else row.get("inclination") if row.get("inclination") not in (None, "")
                    else row.get("plunge"))
        incl = float(incl_raw)
        gamma = g if g not in ("", None) else None
        row_id = row.get("id", "")
        w = validate_inputs(alpha, beta, gamma, trend, incl)
        _print_warnings(w, label=row_id or None)
        r = abg_to_orientation(alpha, beta, gamma, trend, incl)
        out_rows.append({
            "id": row_id,
            "alpha": row["alpha"], "beta": row["beta"], "gamma": g,
            "trend": row["trend"], "incl": incl,
            "dip": round(r["dip"], 2),
            "dip_azimuth": round(r["dip_azimuth"], 2),
            "lin_trend": "" if r["trend"] is None else round(r["trend"], 2),
            "lin_plunge": "" if r["plunge"] is None else round(r["plunge"], 2),
            "warnings": "; ".join(w),
        })
    target = open(out, "w", newline="") if out else sys.stdout
    writer = csv.DictWriter(target, fieldnames=fields)
    writer.writeheader()
    writer.writerows(out_rows)
    if out:
        target.close()
        print(f"Wrote {len(out_rows)} rows to {out}")


def _hold_open():
    """Keep the console window open after a non-interactive run (e.g. when the
    script was double-clicked rather than run from an already-open terminal)."""
    try:
        input("\nPress Enter to close...")
    except EOFError:
        pass  


def _ask(prompt, optional=False):
    while True:
        v = input(prompt).strip()
        if v == "" and optional:
            return None
        try:
            return float(v)
        except ValueError:
            print("  please enter a number" + (" (or blank)" if optional else ""))


def main():
    ap = argparse.ArgumentParser(
        description="Oriented core a/b/g -> orientation",
        epilog="CSV batch mode: python oriented_core.py --csv input.csv --out results.csv\n"
               "Full CSV instructions and column reference are in the module docstring -\n"
               "run: python -c \"import oriented_core; help(oriented_core)\"",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--alpha", type=float)
    ap.add_argument("--beta", type=float)
    ap.add_argument("--gamma", type=float)
    ap.add_argument("--trend", type=float)
    ap.add_argument("--incl", "--plunge", type=float, dest="incl",
                    help="hole inclination, deg, -90 to 90 (NEGATIVE down / POSITIVE up)")
    ap.add_argument("--beta-ccw", action="store_true",
                    help="beta measured counter-clockwise looking down-hole")
    ap.add_argument("--gamma-ccw", action="store_true",
                    help="gamma measured counter-clockwise looking down-hole")
    ap.add_argument("--csv", help="input CSV (alpha,beta,gamma,trend,incl[,id])")
    ap.add_argument("--out", help="output CSV path (with --csv)")
    args = ap.parse_args()

    if args.csv:
        _run_csv(args.csv, args.out)
        _hold_open()
        return

    if None not in (args.alpha, args.beta, args.trend, args.incl):
        _print_warnings(validate_inputs(args.alpha, args.beta, args.gamma,
                                        args.trend, args.incl))
        r = abg_to_orientation(args.alpha, args.beta, args.gamma,
                               args.trend, args.incl,
                               beta_cw=not args.beta_ccw,
                               gamma_cw=not args.gamma_ccw)
        print(_fmt(r))
        _hold_open()
        return

    # interactive mode
    print("Oriented core calculator (blank gamma = plane only)\n")
    alpha = _ask("  alpha (deg, 0-90): ")
    beta = _ask("  beta  (deg, 0-360): ")
    gamma = _ask("  gamma (deg, 0-360, optional): ", optional=True)
    trend = _ask("  hole trend (deg, 0-360): ")
    incl = _ask("  hole inclination (deg, -90 to 90, NEG down / POS up): ")
    _print_warnings(validate_inputs(alpha, beta, gamma, trend, incl))
    r = abg_to_orientation(alpha, beta, gamma, trend, incl)
    print("\n" + _fmt(r))

    # loop so the window stays open and to run more conversions
    while True:
        again = input("\nConvert another? (Enter = yes, 'q' = quit): ").strip().lower()
        if again == "q":
            break
        print()
        alpha = _ask("  alpha (deg, 0-90): ")
        beta = _ask("  beta  (deg, 0-360): ")
        gamma = _ask("  gamma (deg, 0-360, optional): ", optional=True)
        trend = _ask("  hole trend (deg, 0-360): ")
        incl = _ask("  hole inclination (deg, -90 to 90, NEG down / POS up): ")
        _print_warnings(validate_inputs(alpha, beta, gamma, trend, incl))
        r = abg_to_orientation(alpha, beta, gamma, trend, incl)
        print("\n" + _fmt(r))


if __name__ == "__main__":
    main()
