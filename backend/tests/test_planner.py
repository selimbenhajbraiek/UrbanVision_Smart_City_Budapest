"""Route planner on the mini GTFS feed (service 'WD' runs on 2026-10-04..06).

Places used (see tests/fixtures/mini_gtfs/stops.txt):
  Deák metro platform 001001 (47.4981, 19.0546) — M2 08:00 / 08:10 to Blaha via Astoria
  Deák bus stop       002001 (47.4975, 19.0550) — 65 m away; bus 9 at 08:03 to Kálvin tér
  Blaha Lujza tér     001003 (47.4965, 19.0703)
  Kálvin tér          002002 (47.4895, 19.0620)
"""

import pytest

from app.services.planner import Timetable, build_timetable, connection_scan, unwind, walk_seconds

DEAK = "47.4981,19.0546"
BLAHA = "47.4965,19.0703"
KALVIN = "47.4895,19.0620"


def plan(client, **params):
    params.setdefault("date", "2026-10-05")
    params = {"from" if k == "from_" else k: v for k, v in params.items()}
    return client.get("/api/plan", params=params)


def transit_legs(journey):
    return [leg for leg in journey["legs"] if leg["kind"] == "transit"]


def test_direct_metro_and_next_alternative(client):
    body = plan(
        client, from_=DEAK, to=BLAHA, time="07:58", from_name="Deák", to_name="Blaha"
    ).json()
    assert body["data_status"] == "scheduled"
    assert body["notice"] is None
    assert body["origin"]["name"] == "Deák"
    first, second = body["journeys"][0], body["journeys"][1]
    leg = transit_legs(first)[0]
    assert leg["route"]["short_name"] == "M2"
    assert leg["trip_id"] == "M2_T1"
    assert leg["departure"] == "2026-10-05T08:00:00+02:00"
    assert leg["arrival"] == "2026-10-05T08:04:00+02:00"
    assert leg["stop_count"] == 2
    assert [s["name"] for s in leg["intermediate_stops"]] == ["Astoria"]
    assert leg["geometry"][0] == [19.0546, 47.4981]
    assert first["transfers"] == 0
    # the next metro is offered as an alternative
    assert transit_legs(second)[0]["trip_id"] == "M2_T2"


def test_walking_option_is_offered_for_short_trips(client):
    journeys = plan(client, from_=DEAK, to=BLAHA, time="07:58").json()["journeys"]
    walk_only = [j for j in journeys if not transit_legs(j)]
    assert len(walk_only) == 1
    assert walk_only[0]["legs"][0]["distance_m"] > 1000


def test_walks_to_a_nearby_stop_to_catch_the_bus(client):
    journey = plan(client, from_=DEAK, to=KALVIN, time="08:01").json()["journeys"][0]
    kinds = [leg["kind"] for leg in journey["legs"]]
    assert kinds[:2] == ["walk", "transit"]
    walk, bus = journey["legs"][0], journey["legs"][1]
    assert walk["end"]["stop_id"] == "002001"
    assert 50 < walk["distance_m"] < 80
    assert bus["route"]["short_name"] == "9"
    assert bus["arrival"] == "2026-10-05T08:15:00+02:00"
    assert bus["headsign"] == "Kálvin tér"


def test_after_midnight_uses_yesterdays_night_trip(client):
    body = plan(client, from_=DEAK, to=BLAHA, date="2026-10-06", time="00:15").json()
    leg = transit_legs(body["journeys"][0])[0]
    assert leg["trip_id"] == "M2_NIGHT"
    assert leg["departure"] == "2026-10-06T00:30:00+02:00"


def test_no_service_day_returns_notice_and_walking_only(client):
    body = plan(client, from_=DEAK, to=BLAHA, date="2027-01-01", time="08:00").json()
    assert body["schedule_available"] is False
    assert "does not cover" in body["notice"]
    assert all(not transit_legs(j) for j in body["journeys"])


def test_no_connection_late_in_the_evening(client):
    body = plan(client, from_=DEAK, to=BLAHA, time="20:00").json()
    assert "No public-transport connection" in body["notice"]


@pytest.mark.parametrize(
    "params",
    [
        {"from_": "not,a,point", "to": BLAHA},
        {"from_": "48.5,19.0", "to": BLAHA},  # outside Budapest
        {"from_": DEAK, "to": DEAK},  # same place
        {"from_": DEAK, "to": BLAHA, "time": "25:00"},
        {"from_": DEAK, "to": BLAHA, "time": "8am"},
    ],
)
def test_invalid_requests(client, params):
    assert plan(client, **params).status_code == 422


# --- the algorithm on its own, with a hand-made timetable -------------------


def make_timetable(rows) -> Timetable:
    return build_timetable(rows)


def test_scan_respects_change_time_and_no_pickup():
    d = "2026-10-05"
    rows = [
        # trip A: S1 -> S2 arriving at t=100
        (d, "A", 1, "S1", 0, 0, 0, 0),
        (d, "A", 2, "S2", 100, 100, 0, 0),
        # trip B leaves S2 at 130: too soon to change (needs 60 s)
        (d, "B", 1, "S2", 130, 130, 0, 0),
        (d, "B", 2, "S3", 200, 200, 0, 0),
        # trip C leaves S2 at 170 but does not pick up passengers there
        (d, "C", 1, "S2", 170, 170, 1, 0),
        (d, "C", 2, "S3", 210, 210, 0, 0),
        # trip D leaves S2 at 180: catchable
        (d, "D", 1, "S2", 180, 180, 0, 0),
        (d, "D", 2, "S3", 260, 260, 0, 0),
    ]
    tt = make_timetable(rows)
    result = connection_scan(tt, {}, 0, [("S1", 0, 0)], {"S3": 0})
    assert result.arrival == 260
    rides = [tt.connections[p[1]][4][1] for p, _ in unwind(result, tt) if p[0] == "ride"]
    assert rides == ["A", "D"]


def test_walk_seconds():
    assert walk_seconds(0) == 0
    assert 95 <= walk_seconds(100) <= 97  # 100 m ≈ 1.6 min with detour
