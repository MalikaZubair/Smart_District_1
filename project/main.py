import asyncio
import getpass
import hmac
import sys

from exceptions import AuthenticationError, ConfigError

try:
    from config import settings
except ConfigError as exc:
    sys.exit(f"[CONFIG ERROR] {exc}")

from decorators import log_errors
from logger_setup import get_logger
from reports import ReportGenerator
from services import PortalService

logger = get_logger()

MENU = """
========== ACADEMIC PORTAL ==========
1. List all students
2. Search student by ID
3. Failed students
4. Late fines
5. Generate reports
6. Reload data
0. Exit
> """


async def ainput(prompt: str) -> str:
    return await asyncio.to_thread(input, prompt)   # event loop block نہیں ہوتا


@log_errors
async def login() -> bool:
    for attempt in range(1, 4):
        given = await asyncio.to_thread(getpass.getpass, "Admin password: ")
        # constant-time compare: timing attack سے بچاؤ
        if hmac.compare_digest(given.encode(), settings.admin_password.encode()):
            logger.info("Login successful")
            return True
        logger.warning("Failed login attempt %d", attempt)
        print("Wrong password.")
    raise AuthenticationError("Too many failed login attempts")


class PortalCLI:
    def __init__(self, service: PortalService):
        self.service = service

    @log_errors
    async def list_students(self):
        print(f"\n{'ID':<8}{'Name':<20}{'Dept':<22}{'Avg':>6}  Status")
        for s in self.service.students.values():
            print(f"{s.student_id:<8}{s.name:<20}{s.department:<22}"
                  f"{s.average:>6}  {self.service.status(s)}")
        if self.service.rejected_rows:
            print(f"\n({self.service.rejected_rows} invalid rows skipped, see logs)")

    @log_errors
    async def search(self):
        sid = await ainput("Student ID: ")
        s = self.service.get(sid)
        print(f"\n{s.student_id} | {s.name} | {s.email} | {s.department} | Sem {s.semester}")
        for m in s.marks:
            print(f"  {m.subject:<12}{m.marks}")
        print(f"  Average: {s.average} | Status: {self.service.status(s)} "
              f"| Fine: Rs. {self.service.student_fine(s)}")

    @log_errors
    async def failed(self):
        failed = self.service.failed_students()
        if not failed:
            print("No failed students.")
        for s in failed:
            print(f"{s.student_id} {s.name}: {', '.join(self.service.failed_subjects(s))}")

    @log_errors
    async def fines(self):
        rows = self.service.all_fines()
        if not rows:
            print("No late fines.")
        for s, loan, fine in rows:
            print(f"{s.student_id} {s.name:<14}{loan.book:<24}Rs. {fine}")
        print(f"Total: Rs. {sum(f for _, _, f in rows)}")

    @log_errors
    async def reports(self):
        paths = await ReportGenerator(self.service).generate_all()
        for p in paths:
            print(f"Saved: {p}")

    @log_errors
    async def reload(self):
        self.service = await PortalService.create()
        print("Data reloaded.")

    async def run(self):
        actions = {"1": self.list_students, "2": self.search, "3": self.failed,
                   "4": self.fines, "5": self.reports, "6": self.reload}
        while True:
            choice = (await ainput(MENU)).strip()
            if choice == "0":
                break
            action = actions.get(choice)
            if action is None:
                print("Invalid option.")
                continue
            await action()


@log_errors
async def main():
    logger.info("Portal started")
    if not await login():
        return
    service = await PortalService.create()
    await PortalCLI(service).run()
    logger.info("Portal closed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye.")