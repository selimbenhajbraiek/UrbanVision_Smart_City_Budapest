"""Public-transport route planner (A → B) on the scheduled BKK timetable.

Algorithm: Connection Scan Algorithm (CSA, Dibbelt et al. 2013), earliest-arrival variant.

1. Load the next 2.5 hours of the timetable as *connections*: one vehicle driving from one
   stop to the next, e.g. "trip X leaves Deák tér 08:00 and reaches Astoria 08:02".
2. Walk from A to every stop within 800 m.
3. Scan the connections ONCE, in departure order. A connection is usable if we are already
   on its trip, or if we can be at its departure stop in time. Whenever it brings us to a
   stop earlier than before, remember how, and try short walks (≤ 250 m) to nearby stops.
4. Best arrival at B = best arrival at a stop near B + the walk from that stop to B.
5. Follow the remembered steps backwards to get the legs of the journey.

Running the scan again from slightly later start times gives the next alternatives.
Internally all times are seconds after the requested moment.
"""

import bisect
import logging
import math
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from psycopg import Connection

from app.repositories import departures as departures_repo
from app.repositories import planner as repo
from app.repositories.departures import ServiceWindow
from app.schemas.planner import Journey, Leg, LegRoute, Place, PlanResponse
from app.services.schedule_time import seconds_since_service_start

logger = logging.getLogger(__name__)

WALK_SPEED_MPS = 1.3  # ≈ 4.7 km/h
WALK_DETOUR = 1.25  # streets are not straight lines
MAX_ACCESS_M = 800  # walk from A to a stop / from a stop to B
MAX_FOOTPATH_M = 250  # walk between two stops when changing
MAX_DIRECT_WALK_M = 2500  # offer "just walk" up to this distance
MIN_CHANGE_S = 60  # time to change between two vehicles at the same stop
SEARCH_WINDOW_MIN = 150
MAX_JOURNEYS = 3
INF = math.inf


def walk_seconds(meters: float) -> int:
    return math.ceil(meters * WALK_DETOUR / WALK_SPEED_MPS)


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres (haversine formula)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# Walking network: stops + footpaths. Cached until a new timetable is imported.
# ---------------------------------------------------------------------------


@dataclass
class StopInfo:
    stop_id: str
    name: str
    lat: float
    lon: float


@dataclass
class WalkNetwork:
    stops: dict[str, StopInfo]
    footpaths: dict[str, list[tuple[str, int, int]]]  # stop -> [(other stop, seconds, metres)]
    latest_schedule_second: int

    def stops_near(self, lat: float, lon: float, max_m: float) -> list[tuple[str, int, int]]:
        """(stop_id, walk seconds, metres) of the stops within `max_m` of a point."""
        dlat = max_m / 111_000
        dlon = max_m / (111_000 * math.cos(math.radians(lat)))
        near = []
        for s in self.stops.values():
            if abs(s.lat - lat) <= dlat and abs(s.lon - lon) <= dlon:  # cheap box first
                d = distance_m(lat, lon, s.lat, s.lon)
                if d <= max_m:
                    near.append((s.stop_id, walk_seconds(d), round(d)))
        return near


_network_lock = threading.Lock()
_network_cache: dict = {"key": None, "network": None}


def get_walk_network(conn: Connection) -> WalkNetwork:
    key = (conn.info.dbname, repo.latest_import(conn))
    with _network_lock:
        if _network_cache["key"] != key:
            stops = {row[0]: StopInfo(*row) for row in repo.boarding_stops(conn)}
            paths: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
            for a, b, meters in repo.footpaths(conn, MAX_FOOTPATH_M):
                paths[a].append((b, walk_seconds(meters), round(meters)))
            network = WalkNetwork(stops, dict(paths), repo.latest_schedule_second(conn))
            _network_cache.update(key=key, network=network)
            logger.info(
                "Route planner ready: %d stops, %d footpaths",
                len(stops),
                sum(len(p) for p in paths.values()),
            )
        return _network_cache["network"]


# ---------------------------------------------------------------------------
# Timetable slice → connections
# ---------------------------------------------------------------------------


@dataclass
class Timetable:
    # connection = (dep, arr, from_stop, to_stop, trip_key, index_in_trip, can_board, can_alight)
    connections: list[tuple]
    departures: list[int]  # departure time of each connection (for binary search)
    trips: dict[tuple, list[tuple]]  # trip_key -> [(seq, stop, arr, dep, pickup, drop_off)]


def build_timetable(rows: list[tuple]) -> Timetable:
    trips: dict[tuple, list[tuple]] = defaultdict(list)
    for service_date, trip_id, seq, stop_id, arr, dep, pickup, drop_off in rows:
        trips[(service_date, trip_id)].append((seq, stop_id, arr, dep, pickup, drop_off))
    connections = []
    for key, events in trips.items():
        events.sort()
        for i in range(len(events) - 1):
            a, b = events[i], events[i + 1]
            if b[2] >= a[3]:  # skip broken data (arrival before departure)
                connections.append((a[3], b[2], a[1], b[1], key, i, a[4] != 1, b[5] != 1))
    connections.sort(key=lambda c: (c[0], c[1]))
    return Timetable(connections, [c[0] for c in connections], dict(trips))


# ---------------------------------------------------------------------------
# Connection Scan
# ---------------------------------------------------------------------------


@dataclass
class ScanResult:
    arrival: float  # at B
    final_stop: str | None  # the stop from which we walk to B
    pointers: dict = field(default_factory=dict)  # stop -> how we reached it


def connection_scan(
    tt: Timetable,
    footpaths: dict[str, list[tuple[str, int, int]]],
    start: int,
    access: list[tuple[str, int, int]],
    egress: dict[str, int],
) -> ScanResult:
    best: dict[str, float] = {}  # earliest arrival at each stop
    ready: dict[str, float] = {}  # earliest moment we can board a vehicle there
    ptr: dict[
        str, tuple
    ] = {}  # ("access", s, m) | ("ride", board_idx, alight_idx) | ("walk", from, s, m)
    trip_entered: dict[tuple, int] = {}  # trip -> connection index where we got on
    target, target_stop = INF, None

    def reach(stop: str, t: float) -> None:
        nonlocal target, target_stop
        if stop in egress and t + egress[stop] < target:
            target, target_stop = t + egress[stop], stop

    for stop, seconds, meters in access:
        t = start + seconds
        if t < best.get(stop, INF):
            best[stop] = ready[stop] = t
            ptr[stop] = ("access", seconds, meters)
            reach(stop, t)

    conns = tt.connections
    for idx in range(bisect.bisect_left(tt.departures, start), len(conns)):
        dep, arr, from_stop, to_stop, trip, _, can_board, can_alight = conns[idx]
        if dep >= target:
            break  # nothing that leaves later can arrive earlier
        entered = trip_entered.get(trip)
        if entered is None:
            if not can_board or ready.get(from_stop, INF) > dep:
                continue
            trip_entered[trip] = entered = idx
        if not can_alight or arr >= best.get(to_stop, INF):
            continue
        best[to_stop] = arr
        ready[to_stop] = arr + MIN_CHANGE_S
        ptr[to_stop] = ("ride", entered, idx)
        reach(to_stop, arr)
        for other, seconds, meters in footpaths.get(to_stop, ()):
            t = arr + seconds
            if t < best.get(other, INF):
                best[other] = ready[other] = t
                ptr[other] = ("walk", to_stop, seconds, meters)
                reach(other, t)

    return ScanResult(target, target_stop, ptr)


def unwind(result: ScanResult, tt: Timetable) -> list[tuple]:
    """The steps from A to the last stop, in travel order: [(pointer, stop_reached), ...]."""
    steps, stop = [], result.final_stop
    for _ in range(64):  # guards against loops; real journeys have a handful of legs
        p = result.pointers[stop]
        steps.append((p, stop))
        if p[0] == "access":
            return list(reversed(steps))
        stop = p[1] if p[0] == "walk" else tt.connections[p[1]][2]
    raise RuntimeError("Could not rebuild the journey")


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------


@dataclass
class Point:
    lat: float
    lon: float
    name: str


def search_windows(at: datetime, tz: ZoneInfo, latest_second: int) -> list[ServiceWindow]:
    """Yesterday's late trips (GTFS times > 24:00), today's, and tomorrow's if we pass midnight."""
    windows = []
    for day_offset in (-1, 0, 1):
        service_date = at.date() + timedelta(days=day_offset)
        begin = seconds_since_service_start(at, service_date, tz)
        end = begin + SEARCH_WINDOW_MIN * 60
        if end > 0 and begin <= latest_second:  # skip windows no trip can fall into
            windows.append(ServiceWindow(service_date, begin, end))
    return windows


def plan(
    conn: Connection, origin: Point, destination: Point, at: datetime, tz: ZoneInfo
) -> PlanResponse:
    net = get_walk_network(conn)
    access = net.stops_near(origin.lat, origin.lon, MAX_ACCESS_M)
    egress_list = net.stops_near(destination.lat, destination.lon, MAX_ACCESS_M)
    egress = {stop: seconds for stop, seconds, _ in egress_list}
    egress_m = {stop: meters for stop, _, meters in egress_list}

    found: list[tuple[list[tuple], ScanResult]] = []
    tt = None
    if access and egress:
        windows = search_windows(at, tz, net.latest_schedule_second)
        tt = build_timetable(repo.timetable_slice(conn, windows)) if windows else None
    if tt is not None:
        seen: set[tuple] = set()
        start = 0
        for _ in range(MAX_JOURNEYS):
            result = connection_scan(tt, net.footpaths, start, access, egress)
            if result.final_stop is None:
                break
            steps = unwind(result, tt)
            rides = [p for p, _ in steps if p[0] == "ride"]
            if not rides:
                break  # walking is best: the walking option is added below
            signature = tuple(tt.connections[p[1]][4] for p in rides)
            if signature not in seen:
                seen.add(signature)
                found.append((steps, result))
            # next alternative: leave a minute after this journey leaves
            start = tt.connections[rides[0][1]][0] - steps[0][0][1] + 60

    origin_place = Place(name=origin.name, latitude=origin.lat, longitude=origin.lon)
    dest_place = Place(name=destination.name, latitude=destination.lat, longitude=destination.lon)
    trip_ids = sorted(
        {tt.connections[p[1]][4][1] for steps, _ in found for p, _ in steps if p[0] == "ride"}
    )
    builder = _JourneyBuilder(
        net, tt, at, origin_place, dest_place, egress, egress_m, repo.trip_details(conn, trip_ids)
    )
    journeys = [builder.build(steps, result) for steps, result in found]

    direct_m = distance_m(origin.lat, origin.lon, destination.lat, destination.lon)
    if direct_m <= MAX_DIRECT_WALK_M:
        journeys.append(builder.walk_only(direct_m))
    journeys.sort(key=lambda j: (j.arrival, j.transfers))

    schedule_available = departures_repo.has_service_on(conn, at.date())
    notice = None
    if not schedule_available:
        notice = (
            f"The imported timetable does not cover {at.date().isoformat()}. "
            "Import a newer BKK GTFS feed to plan trips."
        )
    elif not access:
        notice = "No public-transport stop within 800 m of the start."
    elif not egress:
        notice = "No public-transport stop within 800 m of the destination."
    elif not found:
        notice = (
            "No public-transport connection found in the next "
            f"{SEARCH_WINDOW_MIN // 60} h {SEARCH_WINDOW_MIN % 60} min."
        )

    return PlanResponse(
        origin=origin_place,
        destination=dest_place,
        requested_at=at,
        schedule_available=schedule_available,
        notice=notice,
        journeys=journeys,
    )


class _JourneyBuilder:
    """Turns the algorithm's steps into legs with names, times and map geometry."""

    def __init__(self, net, tt, at, origin, destination, egress, egress_m, trip_details):
        self.net, self.tt, self.at = net, tt, at
        self.origin, self.destination = origin, destination
        self.egress, self.egress_m, self.trip_details = egress, egress_m, trip_details

    def _time(self, rel: float) -> datetime:
        return self.at + timedelta(seconds=rel)

    def _place(self, stop_id: str) -> Place:
        s = self.net.stops[stop_id]
        return Place(name=s.name, latitude=s.lat, longitude=s.lon, stop_id=stop_id)

    def _walk(self, start: Place, end: Place, t0: float, seconds: int, meters: int) -> Leg:
        return Leg(
            kind="walk",
            start=start,
            end=end,
            departure=self._time(t0),
            arrival=self._time(t0 + seconds),
            duration_minutes=max(1, round(seconds / 60)),
            distance_m=meters,
            geometry=[(start.longitude, start.latitude), (end.longitude, end.latitude)],
        )

    def _ride(self, board: tuple, alight: tuple) -> Leg:
        events = self.tt.trips[board[4]][board[5] : alight[5] + 2]
        places = [self._place(e[1]) for e in events if e[1] in self.net.stops]
        info = self.trip_details[board[4][1]]
        accessible = info["wheelchair_accessible"]
        return Leg(
            kind="transit",
            start=places[0],
            end=places[-1],
            departure=self._time(board[0]),
            arrival=self._time(alight[1]),
            duration_minutes=max(1, round((alight[1] - board[0]) / 60)),
            route=LegRoute(
                route_id=info["route_id"],
                short_name=info["short_name"],
                mode=info["mode"],
                color=info["color"],
                text_color=info["text_color"],
            ),
            headsign=info["headsign"],
            trip_id=board[4][1],
            stop_count=len(events) - 1,
            intermediate_stops=places[1:-1],
            wheelchair_accessible=None if accessible in (None, 0) else accessible == 1,
            geometry=[(p.longitude, p.latitude) for p in places],
        )

    def build(self, steps: list[tuple], result: ScanResult) -> Journey:
        conns = self.tt.connections
        legs: list[Leg] = []
        clock = 0.0
        access_step = None
        for p, stop in steps:
            if p[0] == "access":
                access_step = (stop, p[1], p[2])
            elif p[0] == "walk":
                legs.append(self._walk(self._place(p[1]), self._place(stop), clock, p[2], p[3]))
                clock += p[2]
            else:
                board, alight = conns[p[1]], conns[p[2]]
                if access_step is not None:  # leave A just in time for the first vehicle
                    a_stop, a_sec, a_m = access_step
                    legs.append(
                        self._walk(self.origin, self._place(a_stop), board[0] - a_sec, a_sec, a_m)
                    )
                    access_step = None
                legs.append(self._ride(board, alight))
                clock = alight[1]
        last = result.final_stop
        legs.append(
            self._walk(
                self._place(last), self.destination, clock, self.egress[last], self.egress_m[last]
            )
        )
        return self._journey(legs)

    def walk_only(self, meters: float) -> Journey:
        leg = self._walk(self.origin, self.destination, 0, walk_seconds(meters), round(meters))
        return self._journey([leg])

    @staticmethod
    def _journey(legs: list[Leg]) -> Journey:
        # drop walks of a few metres (e.g. A was picked exactly at the stop)
        legs = [leg for leg in legs if leg.kind == "transit" or (leg.distance_m or 0) >= 20] or legs
        walks = [leg for leg in legs if leg.kind == "walk"]
        departure, arrival = legs[0].departure, legs[-1].arrival
        return Journey(
            departure=departure,
            arrival=arrival,
            duration_minutes=max(1, round((arrival - departure).total_seconds() / 60)),
            transfers=max(0, sum(leg.kind == "transit" for leg in legs) - 1),
            walking_minutes=sum(leg.duration_minutes for leg in walks),
            walking_m=sum(leg.distance_m or 0 for leg in walks),
            legs=legs,
        )
