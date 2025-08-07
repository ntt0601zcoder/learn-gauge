from rest_framework.response import Response

class RestResponse():
    content_type = "application/json"

    def __init__(self, data: dict = None, code: str = "", message: str = "", status: int = 200) -> None:
        self.__data = data
        self.__message = message
        self.__code = code
        self.__status = status
    
    @property
    def response(self):
        return Response(
            {
                "data": self.__data,
                "code": self.__code,
                "message": self.__get_default_message(),
            },
            status=self.__status,
            content_type=self.content_type
        )
    
    def __get_default_message(self):
        return self.__message or {
            500: "Lỗi hệ thống!",
            404: "Không tìm thấy tài nguyên!",
            400: "Yêu cầu thất bại!",
            200: "Thành công!",
            201: "Thành công!",
        }.get(self.__status, "")