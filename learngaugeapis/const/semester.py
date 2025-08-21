from enum import Enum

class Semester(Enum):
    FIRST = "FIRST"
    SECOND = "SECOND"
    THIRD = "THIRD"

    @staticmethod
    def all():
        return [Semester.FIRST, Semester.SECOND, Semester.THIRD]