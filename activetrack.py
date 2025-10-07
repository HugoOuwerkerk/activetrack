import os
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from garminconnect import Garmin


# not realy needed now but in case Garmin changes the structure again
def _get_summary_data(raw_summary):
    if isinstance(raw_summary, dict):
        if isinstance(raw_summary.get("summary"), dict):
            return raw_summary["summary"]
        return raw_summary
    return {}
    
class DailyStats:
    def __init__(self, raw_summary):
        data = _get_summary_data(raw_summary)
        # Stress data sometimes under stressDetails, just in case get it from there
        stress_details = {}
        if isinstance(raw_summary, dict) and isinstance(raw_summary.get("stressDetails"), dict):
            stress_details = raw_summary["stressDetails"]

        # Distance shows up in different keys depending on device so to be save getting both
        distance_meters = data.get("totalDistanceMeters") or data.get("distanceInMeters")

        self.steps = data.get("totalSteps") or data.get("steps")
        self.resting_hr = data.get("restingHeartRate")
        self.min_hr = data.get("minHeartRate")
        self.max_hr = data.get("maxHeartRate")
        self.avg_resting_hr_7d = data.get("lastSevenDaysAvgRestingHeartRate")
        self.stress_avg = data.get("averageStressLevel") or stress_details.get("averageStressLevel")
        self.distance_km = round(distance_meters / 1000, 2) if distance_meters else None
        self.body_battery_high = data.get("bodyBatteryHighestValue")
        self.body_battery_low = data.get("bodyBatteryLowestValue")
        # same as distance, activeKcal or wellnessActiveKilocalories
        self.active_kcal = data.get("activeKilocalories") or data.get("wellnessActiveKilocalories")
        self.total_kcal = data.get("totalKilocalories")
        self._metrics = [
            ("Steps", self.steps),
            ("Resting heart rate", self.resting_hr),
            ("Min heart rate", self.min_hr),
            ("Max heart rate", self.max_hr),
            ("7-day avg resting heart rate", self.avg_resting_hr_7d),
            ("Average stress level", self.stress_avg),
            ("Total distance (km)", self.distance_km),
            ("Body battery high", self.body_battery_high),
            ("Body battery low", self.body_battery_low),
            ("Active kilocalories", self.active_kcal),
            ("Total kilocalories", self.total_kcal),
        ]

    def as_pairs(self) -> List[Tuple[str, Optional[Any]]]:
        return list(self._metrics)


def _get_activity_type(activity):
    # Activity type details sit under activityType -> typeKey, so unwrap carefully.
    if isinstance(activity, dict):
        activity_type = activity.get("activityType")
        if isinstance(activity_type, dict):
            return activity_type.get("typeKey")
    return None


def _to_km(distance_meters):
    if not distance_meters:
        return None
    return round(distance_meters / 1000, 2)


def _to_hours(seconds):
    if not seconds:
        return None
    return round(seconds / 3600, 2)


class ActivityRecord:
    def __init__(self, activity):
        self.raw = activity if isinstance(activity, dict) else {}
        self.type = _get_activity_type(self.raw)
        self.start = self.raw.get("startTimeLocal") or self.raw.get("startTimeGMT")
        self.distance_km = _to_km(self.raw.get("distance"))
        self.duration_hours = _to_hours(self.raw.get("duration"))
        self.avg_hr = self.raw.get("averageHR") or self.raw.get("averageHeartRate")
        self.max_hr = self.raw.get("maxHR") or self.raw.get("maxHeartRate")
        self.calories = self.raw.get("calories")
        self.elevation_gain = self.raw.get("elevationGain")

    def as_dict(self):
        return {
            "type": self.type,
            "start": self.start,
            "distance_km": self.distance_km,
            "duration_hours": self.duration_hours,
            "avg_hr": self.avg_hr,
            "max_hr": self.max_hr,
            "calories": self.calories,
            "elevation_gain": self.elevation_gain,
        }


class ActivityOverview:
    def __init__(self, activities):
        self.by_type = {}
        if isinstance(activities, list):
            for item in activities:
                record = ActivityRecord(item)
                activity_type = record.type or "unknown"
                self.by_type.setdefault(activity_type, []).append(record)

    def grouped(self) -> Dict[str, List[Dict[str, Any]]]:
        grouped = {}
        for activity_type, records in self.by_type.items():
            grouped[activity_type] = [record.as_dict() for record in records]
        return dict(sorted(grouped.items()))


def _ensure_credentials(email: Optional[str], password: Optional[str]) -> None:
    if not email or not password:
        raise RuntimeError("GARMIN_EMAIL and GARMIN_PASSWORD must be set in environment")


def fetch_overview(target_date: Optional[date | str] = None, activity_limit: int = 5) -> Dict[str, Any]:
    load_dotenv()

    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")
    _ensure_credentials(email, password)

    api = Garmin(email, password)
    api.login()

    try:
        if target_date is None:
            day_str = date.today().isoformat()
        elif isinstance(target_date, date):
            day_str = target_date.isoformat()
        else:
            day_str = target_date

        today_summary = api.get_user_summary(day_str)
        activities = api.get_activities(0, activity_limit)
        stats = DailyStats(today_summary)
        activity_overview = ActivityOverview(activities)
        full_name = api.get_full_name() or "Unknown"

        return {
            "full_name": full_name,
            "daily_metrics": stats.as_pairs(),
            "activity_groups": activity_overview.grouped(),
        }
    finally:
        try:
            api.logout()
        except Exception:
            pass


if __name__ == "__main__":
    main()
