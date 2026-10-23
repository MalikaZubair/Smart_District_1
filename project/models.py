from dataclasses import dataclass, field
from datetime import date
from statistics import mean


@dataclass(frozen=True)
class Mark:
    student_id: str
    subject: str
    marks: float


@dataclass(frozen=True)
class Loan:
    student_id: str
    book: str
    due_date: date
    return_date: date | None = None


@dataclass
class Student:
    student_id: str
    name: str
    email: str
    department: str
    semester: int
    marks: list[Mark] = field(default_factory=list)
    loans: list[Loan] = field(default_factory=list)

    @property
    def average(self) -> float:
        return round(mean(m.marks for m in self.marks), 2) if self.marks else 0.0

    def failed_subjects(self, pass_marks: float) -> list[str]:
        return [m.subject for m in self.marks if m.marks < pass_marks]