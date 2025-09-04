from rest_framework.pagination import PageNumberPagination

class CustomPageNumberPagination(PageNumberPagination):
    page_size_query_param = "size"
    max_page_size = 50
    page_size = 50

    def get_paginated_data(self, data):
        return {
            'total_page': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'results': data
        }