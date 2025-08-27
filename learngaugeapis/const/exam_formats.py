from enum import Enum

class ExamFormat(Enum):
    ESSAY = "ESSAY"
    PRACTICE = "PRACTICE"
    WRITTEN = "WRITTEN"
    MCQ = "MCQ"

    @classmethod
    def all(cls):
        return [(item.value, item.value) for item in cls]