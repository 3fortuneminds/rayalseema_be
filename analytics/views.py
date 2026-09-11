import csv

from django.http import HttpResponse
from django.utils.dateparse import parse_date
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.permissions import IsAdminRole, IsRestaurantOwner
from core.responses import error_response, success_response
from restaurants.models import Restaurant

from .services import get_dashboard_stats, get_platform_daily_summary, get_platform_dashboard, get_sales_report


class RestaurantDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsRestaurantOwner]

    def get(self, request):
        restaurant = Restaurant.objects.filter(owner=request.user).first()
        if restaurant is None:
            return error_response(message="You don't have a restaurant yet", status=404)
        return success_response(data=get_dashboard_stats(restaurant))


class RestaurantSalesReportView(APIView):
    permission_classes = [IsAuthenticated, IsRestaurantOwner]

    def get(self, request):
        restaurant = Restaurant.objects.filter(owner=request.user).first()
        if restaurant is None:
            return error_response(message="You don't have a restaurant yet", status=404)

        start_date = parse_date(request.query_params.get("start", ""))
        end_date = parse_date(request.query_params.get("end", ""))
        if start_date is None or end_date is None:
            return error_response(message="Provide start and end as YYYY-MM-DD query params", status=400)

        report = get_sales_report(restaurant, start_date, end_date)

        if request.query_params.get("export") == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="sales_{start_date}_to_{end_date}.csv"'
            writer = csv.writer(response)
            writer.writerow(["Date", "Orders", "Revenue"])
            for row in report:
                writer.writerow([row["date"], row["order_count"], row["revenue"]])
            return response

        return success_response(data=report)


class PlatformDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        return success_response(data=get_platform_dashboard())


class PlatformDailySummaryView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        start_date = parse_date(request.query_params.get("start", ""))
        end_date = parse_date(request.query_params.get("end", ""))
        if start_date is None or end_date is None:
            return error_response(message="Provide start and end as YYYY-MM-DD query params", status=400)

        rows = get_platform_daily_summary(start_date, end_date)

        if request.query_params.get("export") == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="platform_{start_date}_to_{end_date}.csv"'
            writer = csv.writer(response)
            writer.writerow(["Date", "Orders", "Revenue", "New customers"])
            for row in rows:
                writer.writerow([row.date, row.total_orders, row.total_revenue, row.new_customers])
            return response

        return success_response(
            data=[
                {
                    "date": row.date,
                    "total_orders": row.total_orders,
                    "total_revenue": row.total_revenue,
                    "new_customers": row.new_customers,
                }
                for row in rows
            ]
        )
