from enum import Enum

class CLOType(Enum):
    CLO1 = "CLO1"
    CLO2 = "CLO2"
    CLO3 = "CLO3"
    CLO4 = "CLO4"

    @staticmethod
    def all():
        return [CLOType.CLO1.value, CLOType.CLO2.value, CLOType.CLO3.value, CLOType.CLO4.value]