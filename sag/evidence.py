"""Safe observation loading and named schema errors."""
from datetime import date
from math import isfinite
from pathlib import Path
import yaml


class MissingFieldError(ValueError):
    pass


class InvalidMeasurementError(ValueError):
    pass


class EmptyEvidenceError(ValueError):
    pass


def require_text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise MissingFieldError(f"{field} must be non-empty text")


def validate(data, *, allow_empty=False):
    if not isinstance(data, dict):
        raise MissingFieldError("observation must be a mapping")
    business = data.get("business")
    if not isinstance(business, dict):
        raise MissingFieldError("business must be a mapping")
    require_text(business.get("name"), "business.name")
    if not isinstance(business.get("fictional"), bool):
        raise MissingFieldError("business.fictional must be a boolean")
    require_text(data.get("observed_by"), "observed_by")
    observed_date = data.get("observed_date")
    if isinstance(observed_date, date):
        observed_date = observed_date.isoformat()
    require_text(observed_date, "observed_date")
    try:
        date.fromisoformat(observed_date)
    except ValueError as exc:
        raise MissingFieldError("observed_date must be an ISO calendar date") from exc
    data = dict(data, observed_date=observed_date)
    processes = data.get("processes")
    if not isinstance(processes, list):
        raise MissingFieldError("processes must be a list")
    if not processes and not allow_empty:
        raise EmptyEvidenceError("processes must not be empty")
    for process in processes:
        if not isinstance(process, dict):
            raise MissingFieldError("each process must be a mapping")
        for field in ("name", "description"):
            require_text(process.get(field), f"process.{field}")
        for field in ("steps", "tools_used", "pain_notes"):
            values = process.get(field)
            if not isinstance(values, list):
                raise MissingFieldError(f"{process['name']}.{field} must be a list")
            for value in values:
                require_text(value, f"{process['name']}.{field}")
        for field in ("measured_minutes_per_run", "runs_per_week"):
            if field in process:
                value = process[field]
                if (isinstance(value, bool) or not isinstance(value, (int, float))
                        or value < 0 or (isinstance(value, float) and not isfinite(value))):
                    raise InvalidMeasurementError(f"{process['name']}.{field} must be a finite non-negative number")
    return data


def load_evidence(path, *, allow_empty=False):
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise MissingFieldError(f"invalid YAML: {exc}") from exc
    return validate(data, allow_empty=allow_empty)
