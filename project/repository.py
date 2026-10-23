import asyncio
import csv
import re
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path

from config import settings
from decorators import timed
from exceptions import DataLoadError, ValidationError
from logger_setup import get_logger
from models import Loan, Mark, Student

logger = get_logger()

ID_RE = re.compile(r"^[A-Z]{2}\d{3}$")
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")


def _student_id(row: dict) -> str:
    sid = (row.get("student_id") or "").strip().upper()
    if not ID_RE.match(sid):
        raise ValidationError("Invalid student_id", context={"value": sid})
    return sid


def _date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat((value or "").strip())
    except ValueError:
        raise ValidationError(f"Invalid {field_name} (use YYYY-MM-DD)",
                              context={"value": value}) from None


class BaseLoader(ABC):
    filename: str
    required_columns: tuple[str, ...]

    def __init__(self, data_dir: Path = settings.data_dir):
        self.path = Path(data_dir) / self.filename
        self.rejected: list[tuple[int, str]] = []

    def _read_sync(self) -> list[dict]:
        if not self.path.exists():
            raise DataLoadError(f"File not found: {self.path.name}",
                                context={"path": str(self.path)})
        with self.path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            missing = set(self.required_columns) - set(reader.fieldnames or [])
            if missing:
                raise DataLoadError(
                    f"{self.path.name} missing columns: {sorted(missing)}")
            return list(reader)

    @abstractmethod
    def parse_row(self, row: dict):
        """Row validate کر کے model object واپس کرے، ورنہ ValidationError۔"""

    @timed
    async def load(self) -> list:
        rows = await asyncio.to_thread(self._read_sync)  # blocking I/O thread میں
        good = []
        for line, row in enumerate(rows, start=2):
            try:
                good.append(self.parse_row(row))
            except ValidationError as exc:
                self.rejected.append((line, exc.message))
                logger.warning("%s line %d rejected: %s %s",
                               self.filename, line, exc.message, exc.context)
        logger.info("%s: %d loaded, %d rejected",
                    self.filename, len(good), len(self.rejected))
        return good


class StudentLoader(BaseLoader):
    filename = "students.csv"
    required_columns = ("student_id", "name", "email", "department", "semester")

    def parse_row(self, row: dict) -> Student:
        sid = _student_id(row)
        name = (row["name"] or "").strip()
        if len(name) < 2:
            raise ValidationError("Name too short", context={"id": sid})
        email = (row["email"] or "").strip()
        if not EMAIL_RE.match(email):
            raise ValidationError("Invalid email", context={"id": sid, "email": email})
        try:
            semester = int(row["semester"])
        except ValueError:
            raise ValidationError("Semester must be a number",
                                  context={"id": sid}) from None
        if not 1 <= semester <= 8:
            raise ValidationError("Semester must be 1-8", context={"id": sid})
        return Student(sid, name, email, row["department"].strip(), semester)


class MarksLoader(BaseLoader):
    filename = "marks.csv"
    required_columns = ("student_id", "subject", "marks")

    def parse_row(self, row: dict) -> Mark:
        sid = _student_id(row)
        subject = (row["subject"] or "").strip()
        if not subject:
            raise ValidationError("Empty subject", context={"id": sid})
        try:
            marks = float(row["marks"])
        except ValueError:
            raise ValidationError("Marks must be numeric",
                                  context={"id": sid, "value": row["marks"]}) from None
        if not 0 <= marks <= 100:
            raise ValidationError("Marks must be 0-100",
                                  context={"id": sid, "value": marks})
        return Mark(sid, subject, marks)


class LoanLoader(BaseLoader):
    filename = "loans.csv"
    required_columns = ("student_id", "book", "due_date", "return_date")

    def parse_row(self, row: dict) -> Loan:
        sid = _student_id(row)
        due = _date(row["due_date"], "due_date")
        returned = _date(row["return_date"], "return_date") if (
            row["return_date"] or "").strip() else None
        return Loan(sid, row["book"].strip(), due, returned)