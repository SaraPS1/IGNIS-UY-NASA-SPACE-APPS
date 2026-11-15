"""Regression tests: all 3D satellite views must agree with the shared UTC ephemeris."""
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ignis_orbits import (
    SKYFIELD_AVAILABLE, available_bundle, epoch_and_age, groundtrack_events,
    point_in_polygon, positions_at, satellite_from_tle, uruguay_polygon, utc,
)

# Fixed public SGP4 test element set: intentionally obsolete for today's tracking.
ISS_TLE = (
    "1 25544U 98067A   20029.54791435  .00001264  00000-0  29615-4 0  9993",
    "2 25544  51.6449  95.5519 0007417 155.8125 303.1367 15.49174143210616",
)
CATALOG = ({"catalog": "25544", "name": "ISS test fixture",
            "sensor": "TEST", "color": "#ffffff"},)
EPOCH = datetime(2020, 1, 29, 13, 9, tzinfo=timezone.utc)


class OrbitalSynchronizationTests(unittest.TestCase):
    def test_timezone_must_be_explicit(self):
        with self.assertRaises(ValueError):
            utc(datetime(2026, 1, 1))
        self.assertEqual(utc(EPOCH).tzinfo, timezone.utc)

    def test_country_polygon_and_exterior(self):
        poly = uruguay_polygon()
        self.assertGreater(len(poly), 10)
        self.assertTrue(point_in_polygon(-56.1, -33.0, poly))
        self.assertFalse(point_in_polygon(-120, 0, poly))

    def test_groundtrack_crossings_are_not_sensor_coverage(self):
        ring = ((-58, -35), (-53, -35), (-53, -30), (-58, -30), (-58, -35))
        values = [
            {"t": "2020-01-29T12:00:00Z", "lat": -32.0, "lon": -59.0},
            {"t": "2020-01-29T12:00:30Z", "lat": -32.0, "lon": -57.0},
            {"t": "2020-01-29T12:01:00Z", "lat": -32.0, "lon": -55.0},
            {"t": "2020-01-29T12:01:30Z", "lat": -32.0, "lon": -52.0},
        ]
        events = groundtrack_events(values, ring)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["start_utc"], values[1]["t"])
        self.assertEqual(events[0]["end_utc"], values[3]["t"])
        self.assertFalse(events[0]["swath_verified"])
        self.assertEqual(events[0]["event_type"], "subsatellite_groundtrack_crossing")

    @unittest.skipUnless(SKYFIELD_AVAILABLE, "Skyfield required")
    def test_sgp4_geodetic_position_is_finite_and_not_locked_to_uruguay(self):
        sat = satellite_from_tle(ISS_TLE, "ISS")
        epoch, age = epoch_and_age(sat, EPOCH)
        self.assertLess(age, .01)
        positions = positions_at(sat, [EPOCH, EPOCH + timedelta(seconds=60)])
        self.assertEqual(len(positions), 2)
        self.assertTrue(all(300 < p["alt_km"] < 500 for p in positions))
        self.assertTrue(all(-180 <= p["lon"] <= 180 for p in positions))
        self.assertNotEqual(positions[0]["lon"], positions[1]["lon"])
        self.assertTrue(any(not point_in_polygon(p["lon"], p["lat"], uruguay_polygon())
                            for p in positions))

    @unittest.skipUnless(SKYFIELD_AVAILABLE, "Skyfield required")
    def test_outdated_tle_never_produces_current_orbit(self):
        sources = {"25544": {"tle": list(ISS_TLE), "fetched_at": "2026-11-14T12:00:00Z"}}
        bundle = available_bundle(datetime(2026, 11, 14, tzinfo=timezone.utc),
                                  tle_sources=sources, catalog=CATALOG)
        sat = bundle["satellites"][0]
        self.assertEqual(sat["mode"], "unavailable")
        self.assertEqual(sat["track"], [])
        self.assertIsNone(sat["last_pass"])
        self.assertIn("too far", sat["status"])

    @unittest.skipUnless(SKYFIELD_AVAILABLE, "Skyfield required")
    def test_same_tle_and_timestamp_produce_identical_positions_across_views(self):
        sources = {"25544": {"tle": list(ISS_TLE), "fetched_at": "2020-01-29T13:00:00Z"}}
        one = available_bundle(EPOCH, tle_sources=sources, catalog=CATALOG)
        other = available_bundle(EPOCH, tle_sources=sources, catalog=CATALOG)
        a, b = one["satellites"][0], other["satellites"][0]
        self.assertEqual(a["current_position"], b["current_position"])
        self.assertEqual(a["track"], b["track"])
        self.assertEqual(one["reference_utc"], other["reference_utc"])

    def test_no_fake_pass_when_tle_unavailable(self):
        bundle = available_bundle(EPOCH, tle_sources={}, catalog=CATALOG)
        satellite = bundle["satellites"][0]
        self.assertEqual(satellite["mode"], "unavailable")
        self.assertIsNone(satellite["last_pass"])
        self.assertIsNone(satellite["next_pass"])


if __name__ == "__main__":
    unittest.main()
