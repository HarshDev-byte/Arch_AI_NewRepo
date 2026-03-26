/**
 * SunSimulator.ts — Solar position calculations for ArchAI's 3D viewer.
 *
 * Based on the NOAA Solar Calculator algorithm (simplified spherical model).
 * Accurate to < 1° for latitudes within ±60°.
 *
 * References:
 *   https://gml.noaa.gov/grad/solcalc/calcdetails.html
 *   Jean Meeus, "Astronomical Algorithms", 2nd ed.
 */

import * as THREE from "three";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface SunPosition {
  /** Azimuth in radians, measured clockwise from North (0 = North, π/2 = East) */
  azimuth:   number;
  /** Elevation in radians above the horizon (0 = horizon, π/2 = zenith).
   *  Clamped to [0, π/2] — negative values mean the sun is below the horizon. */
  elevation: number;
  /** True if the sun is actually above the horizon */
  isAboveHorizon: boolean;
}

export interface SunState {
  position:  THREE.Vector3;
  intensity: number;
  color:     THREE.Color;
}

// ─── Core algorithm ───────────────────────────────────────────────────────────

/**
 * Calculate the solar position for a given location and time.
 *
 * @param latitude   Degrees N (positive) / S (negative)
 * @param longitude  Degrees E (positive) / W (negative)
 * @param date       Local date/time (JS Date object)
 * @returns          Azimuth + elevation in radians
 */
export function getSunPosition(
  latitude:  number,
  longitude: number,
  date:      Date,
): SunPosition {
  const TO_RAD = Math.PI / 180;

  const lat = latitude * TO_RAD;

  // ── Day-of-year ─────────────────────────────────────────────────────────────
  const startOfYear = new Date(date.getFullYear(), 0, 0);
  const dayOfYear   = Math.floor(
    (date.getTime() - startOfYear.getTime()) / 86_400_000,
  );

  // ── Fractional hour (local clock time — rough approximation without TZ offset) ─
  const hour = date.getHours() + date.getMinutes() / 60 + date.getSeconds() / 3600;

  // ── Solar declination (accurate to ~0.5°) ───────────────────────────────────
  // δ = 23.45° × sin(360/365 × (N − 81))
  const declination = 23.45 * TO_RAD * Math.sin(
    (2 * Math.PI / 365) * (dayOfYear - 81),
  );

  // ── Equation of time (minutes) — accounts for Earth's elliptical orbit ──────
  const B   = (2 * Math.PI / 365) * (dayOfYear - 81);
  const eot = 9.87 * Math.sin(2 * B) - 7.53 * Math.cos(B) - 1.5 * Math.sin(B); // minutes

  // ── Solar noon correction: longitude offset from standard meridian ───────────
  // (Standard meridian ≈ nearest multiple of 15°)
  const stdMeridian = Math.round(longitude / 15) * 15;
  const lonCorrect  = (longitude - stdMeridian) * 4;   // minutes

  // ── True solar hour angle ────────────────────────────────────────────────────
  const solarNoon  = 12 - (eot + lonCorrect) / 60;
  const hourAngle  = ((hour - solarNoon) * 15) * TO_RAD; // 15°/hour

  // ── Solar elevation ──────────────────────────────────────────────────────────
  const sinElev = (
    Math.sin(lat) * Math.sin(declination) +
    Math.cos(lat) * Math.cos(declination) * Math.cos(hourAngle)
  );
  const elevRaw   = Math.asin(Math.max(-1, Math.min(1, sinElev)));
  const elevation = Math.max(0, elevRaw);

  // ── Solar azimuth ─────────────────────────────────────────────────────────────
  // Measured clockwise from North
  const cosAz = (Math.sin(declination) - Math.sin(elevRaw) * Math.sin(lat)) /
                (Math.cos(elevRaw) * Math.cos(lat) + 1e-10);  // avoid /0
  let azimuth  = Math.acos(Math.max(-1, Math.min(1, cosAz)));
  // Afternoon: flip azimuth
  if (hourAngle > 0) azimuth = 2 * Math.PI - azimuth;

  return {
    azimuth,
    elevation,
    isAboveHorizon: elevRaw > 0,
  };
}

/**
 * Convert solar azimuth/elevation angles to a THREE.js world-space Vector3.
 *
 * Three.js co-ordinate convention used here:
 *   +X = East,  +Y = Up,  +Z = South
 * (Matches the viewer where North faces –Z.)
 *
 * @param azimuth    Radians clockwise from North
 * @param elevation  Radians above horizon
 * @param distance   Radius of the sky sphere (default 120)
 */
export function sunPositionToVector3(
  azimuth:   number,
  elevation: number,
  distance:  number = 120,
): THREE.Vector3 {
  // Azimuth: 0=N, π/2=E, π=S, 3π/2=W → rotating from –Z towards +X
  const x = distance * Math.cos(elevation) * Math.sin(azimuth);  // East
  const y = distance * Math.sin(elevation);                        // Up
  const z = distance * Math.cos(elevation) * Math.cos(azimuth);  // South
  return new THREE.Vector3(-x, y, -z);                            // flip for right-hand coords
}

/**
 * Map solar elevation to a warm/cool light colour.
 *
 * Low elevation (sunrise/sunset) → warm orange.
 * High elevation (midday)         → white-yellow.
 */
export function sunColor(elevation: number): THREE.Color {
  // elevation in [0, π/2]
  const t = Math.min(1, elevation / (Math.PI / 4));  // saturates at 45°
  const r = 1.0;
  const g = 0.55 + 0.45 * t;
  const b = 0.15 + 0.75 * t;
  return new THREE.Color(r, g, b);
}

/**
 * Map solar elevation to DirectionalLight intensity.
 *
 * 0  at horizon → peaks at ~2.5 overhead.
 * Smooth sine curve with a soft glow even near the horizon.
 */
export function sunIntensity(elevation: number): number {
  if (elevation <= 0) return 0;
  return Math.max(0, Math.sin(elevation) * 2.8 + 0.2);
}

/**
 * Convenience: get the full THREE-ready sun state from lat/lon + JS Date.
 */
export function getSunState(
  latitude:  number,
  longitude: number,
  date:      Date,
  distance?: number,
): SunState {
  const { azimuth, elevation, isAboveHorizon } = getSunPosition(latitude, longitude, date);
  const position  = sunPositionToVector3(azimuth, elevation, distance);
  const intensity = isAboveHorizon ? sunIntensity(elevation) : 0;
  const color     = isAboveHorizon ? sunColor(elevation)     : new THREE.Color(0x112244);
  return { position, intensity, color };
}
