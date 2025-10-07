import os
from datetime import date

from dotenv import load_dotenv
from garminconnect import Garmin


# not needed now but in case Garmin changes the structure again
def _get_summary_data(raw_summary):
    if isinstance(raw_summary, dict):
        if isinstance(raw_summary.get("summary"), dict):
            return raw_summary["summary"]
        return raw_summary
    return {}


def _seconds_to_hours(seconds):
    if not seconds:
        return None
    return round(seconds / 3600, 2)


class DailyStats:
    def __init__(self, raw_summary):
        data = _get_summary_data(raw_summary)
        # Stress data sometimes lives under stressDetails, grab it if available.
        stress_details = {}
        if isinstance(raw_summary, dict) and isinstance(raw_summary.get("stressDetails"), dict):
            stress_details = raw_summary["stressDetails"]

        # Distance shows up in different keys depending on device.
        distance_meters = data.get("totalDistanceMeters") or data.get("distanceInMeters")
        sleep_seconds = data.get("sleepingSeconds")

        self.steps = data.get("totalSteps") or data.get("steps")
        self.resting_hr = data.get("restingHeartRate")
        self.min_hr = data.get("minHeartRate")
        self.max_hr = data.get("maxHeartRate")
        self.avg_resting_hr_7d = data.get("lastSevenDaysAvgRestingHeartRate")
        self.stress_avg = data.get("averageStressLevel") or stress_details.get("averageStressLevel")
        self.distance_km = round(distance_meters / 1000, 2) if distance_meters else None
        self.body_battery_high = data.get("bodyBatteryHighestValue")
        self.body_battery_low = data.get("bodyBatteryLowestValue")
        # Active calories sometimes live under the wellness prefixed key.
        self.active_kcal = data.get("activeKilocalories") or data.get("wellnessActiveKilocalories")
        self.total_kcal = data.get("totalKilocalories")
        self.sleep_hours = _seconds_to_hours(sleep_seconds)

    def print_report(self):
        print("Daily overview:")
        items = [
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
            ("Sleep hours", self.sleep_hours),
        ]

        for label, value in items:
            if value is None:
                print(f"  {label}: not available")
            else:
                print(f"  {label}: {value}")


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

    def print_report(self):
        print("Recent activities by type:")
        for activity_type in sorted(self.by_type.keys()):
            print(f"  {activity_type}:")
            for record in self.by_type[activity_type]:
                data = record.as_dict()

                start = data.get("start") or "unknown start"

                distance = data.get("distance_km")
                if distance is None:
                    distance_text = "distance n/a"
                else:
                    distance_text = f"{distance:.2f} km"

                duration = data.get("duration_hours")
                if duration is None:
                    duration_text = "duration n/a"
                else:
                    duration_text = f"{duration:.2f} h"

                avg_hr = data.get("avg_hr")
                avg_hr_text = f"avg HR {avg_hr}" if avg_hr is not None else "avg HR n/a"

                max_hr = data.get("max_hr")
                max_hr_text = f"max HR {max_hr}" if max_hr is not None else "max HR n/a"

                calories = data.get("calories")
                calories_text = (
                    f"calories {calories}" if calories is not None else "calories n/a"
                )

                elevation = data.get("elevation_gain")
                elevation_text = (
                    f"elev gain {elevation} m" if elevation is not None else "elev gain n/a"
                )

                parts = [
                    start,
                    distance_text,
                    duration_text,
                    avg_hr_text,
                    max_hr_text,
                    calories_text,
                    elevation_text,
                ]
                print("    " + " - ".join(parts))


def main() -> None:
    load_dotenv()

    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")

    api = Garmin(email, password)
    api.login()

    activities = api.get_activities(0, 5)

    today_str = date.today().isoformat()
    today_summary = api.get_user_summary(today_str)
    stats = DailyStats(today_summary)
    activity_overview = ActivityOverview(activities)

    full_name = api.get_full_name()

    if full_name:
        print(full_name)
    stats.print_report()
    print()
    activity_overview.print_report()


if __name__ == "__main__":
    main()
