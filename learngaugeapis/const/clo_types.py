from enum import Enum

class CLOType(Enum):
    CLO1 = "CLO1"
    CLO2 = "CLO2"
    CLO3 = "CLO3"
    CLO4 = "CLO4"

    @staticmethod
    def all():
        return [CLOType.CLO1, CLOType.CLO2, CLOType.CLO3, CLOType.CLO4]