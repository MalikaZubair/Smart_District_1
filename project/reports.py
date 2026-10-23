import asyncio
import csv
from datetime import datetime
from pathlib import Path

from config import settings
from decorators import timed
from exceptions import ReportError
from logger_setup import get_logger
from services import PortalService

logger = get_logger()


class ReportGenerator:
    def __init__(self, service: PortalService):
        self.service = service

    async def _write_csv(self, name: str, stamp: str, header, rows) -> Path:
        path = settings.report_dir / f"{name}_{stamp}.csv"

        def _write():
            settings.report_dir.mkdir(parents=True, exist_ok=True)
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                writer.writerows(rows)

        try:
            await asyncio.to_thread(_write)
        except OSError as exc:
            raise ReportError(f"Could not write {path.name}",
                              context={"error": str(exc)}) from exc
        return path

    async def summary(self, stamp: str) -> Path:
        svc = self.service
        rows = [(s.student_id, s.name, s.department, s.semester, s.average,
                 svc.status(s), svc.student_fine(s))
                for s in svc.students.values()]
        return await self._write_csv(
            "summary", stamp,
            ("id", "name", "department", "semester", "average", "status", "total_fine"),
            rows)

    async def failed(self, stamp: str) -> Path:
        svc = self.service
        rows = [(s.student_id, s.name, s.average, ";".join(svc.failed_subjects(s)))
                for s in svc.failed_students()]
        return await self._write_csv(
            "failed_students", stamp, ("id", "name", "average", "failed_subjects"), rows)

    async def fines(self, stamp: str) -> Path:
        rows = [(s.student_id, s.name, l.book, l.due_date, l.return_date or "NOT RETURNED", f)
                for s, l, f in self.service.all_fines()]
        return await self._write_csv(
            "fines", stamp,
            ("id", "name", "book", "due_date", "return_date", "fine"), rows)

    @timed
    async def generate_all(self) -> list[Path]:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        paths = await asyncio.gather(
            self.summary(stamp), self.failed(stamp), self.fines(stamp))
        logger.info("Reports generated: %s", [p.name for p in paths])
        return list(paths)