import asyncio
from datetime import date

from config import settings
from decorators import timed
from exceptions import StudentNotFoundError
from logger_setup import get_logger
from models import Loan, Student
from repository import LoanLoader, MarksLoader, StudentLoader

logger = get_logger()


class PortalService:
    def __init__(self, students: dict[str, Student], rejected_rows: int):
        self.students = students
        self.rejected_rows = rejected_rows

    @classmethod
    @timed
    async def create(cls) -> "PortalService":
        loaders = (StudentLoader(), MarksLoader(), LoanLoader())
        # تینوں files ایک ساتھ concurrently load ہوتی ہیں
        students, marks, loans = await asyncio.gather(*(l.load() for l in loaders))

        registry: dict[str, Student] = {}
        for s in students:
            if s.student_id in registry:
                logger.warning("Duplicate student skipped: %s", s.student_id)
                continue
            registry[s.student_id] = s

        for m in marks:
            if m.student_id in registry:
                registry[m.student_id].marks.append(m)
            else:
                logger.warning("Orphan mark for unknown student %s", m.student_id)
        for loan in loans:
            if loan.student_id in registry:
                registry[loan.student_id].loans.append(loan)
            else:
                logger.warning("Orphan loan for unknown student %s", loan.student_id)

        rejected = sum(len(l.rejected) for l in loaders)
        return cls(registry, rejected)

    # ---------- lookups ----------
    def get(self, student_id: str) -> Student:
        student = self.students.get(student_id.strip().upper())
        if student is None:
            raise StudentNotFoundError(f"Student '{student_id}' not found",
                                       context={"student_id": student_id})
        return student

    # ---------- failing logic ----------
    def failed_subjects(self, s: Student) -> list[str]:
        return s.failed_subjects(settings.pass_marks)

    def status(self, s: Student) -> str:
        if not s.marks:
            return "NO MARKS"
        return "FAILED" if self.failed_subjects(s) else "PASSED"

    def failed_students(self) -> list[Student]:
        return [s for s in self.students.values() if self.status(s) == "FAILED"]

    # ---------- fines ----------
    @staticmethod
    def loan_fine(loan: Loan, today: date | None = None) -> int:
        today = today or date.today()
        end = loan.return_date or today          # واپس نہیں کی تو آج تک
        late_days = (end - loan.due_date).days - settings.grace_days
        return min(max(late_days, 0) * settings.fine_per_day, settings.max_fine)

    def student_fine(self, s: Student) -> int:
        return sum(self.loan_fine(l) for l in s.loans)

    def all_fines(self) -> list[tuple[Student, Loan, int]]:
        rows = []
        for s in self.students.values():
            for loan in s.loans:
                fine = self.loan_fine(loan)
                if fine > 0:
                    rows.append((s, loan, fine))
        return rows