"""
Management command for performance testing and profiling
"""

import json
import statistics
import time

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import connection
from django.test import Client


class Command(BaseCommand):
    help = "Run performance tests on the meal planner application"

    def add_arguments(self, parser):
        parser.add_argument(
            "--iterations",
            type=int,
            default=10,
            help="Number of iterations to run for each test",
        )
        parser.add_argument(
            "--endpoints",
            nargs="*",
            default=["/recipes/", "/recipes/meal-plans/", "/recipes/shopping-list/"],
            help="Endpoints to test",
        )
        parser.add_argument(
            "--warm-cache",
            action="store_true",
            help="Warm the cache before running tests",
        )
        parser.add_argument(
            "--output-format",
            choices=["json", "table"],
            default="table",
            help="Output format for results",
        )

    def handle(self, *args, **options):
        self.iterations = options["iterations"]
        self.endpoints = options["endpoints"]
        self.warm_cache = options["warm_cache"]
        self.output_format = options["output_format"]

        self.stdout.write(self.style.SUCCESS("Starting performance tests..."))

        # Create test user if not exists
        self.test_user = self.get_or_create_test_user()

        # Warm cache if requested
        if self.warm_cache:
            self.warm_up_cache()

        # Run tests
        results = {}
        for endpoint in self.endpoints:
            self.stdout.write(f"Testing endpoint: {endpoint}")
            results[endpoint] = self.test_endpoint(endpoint)

        # Output results
        self.output_results(results)

    def get_or_create_test_user(self):
        """Create or get test user"""
        user, created = User.objects.get_or_create(
            username="perf_test_user",
            defaults={
                "email": "test@example.com",
                "is_staff": False,
                "is_superuser": False,
            },
        )
        if created:
            user.set_password("testpass123")
            user.save()
        return user

    def warm_up_cache(self):
        """Warm up cache by making requests"""
        self.stdout.write("Warming up cache...")
        client = Client()
        client.force_login(self.test_user)

        for endpoint in self.endpoints:
            client.get(endpoint)

    def test_endpoint(self, endpoint):
        """Test a single endpoint multiple times"""
        client = Client()
        client.force_login(self.test_user)

        response_times = []
        query_counts = []
        status_codes = []

        for i in range(self.iterations):
            # Clear query log
            connection.queries_log.clear()

            # Time the request
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()

            # Record metrics
            response_times.append(end_time - start_time)
            query_counts.append(len(connection.queries))
            status_codes.append(response.status_code)

            # Small delay between requests
            time.sleep(0.1)

        # Calculate statistics
        return {
            "response_times": {
                "min": min(response_times),
                "max": max(response_times),
                "mean": statistics.mean(response_times),
                "median": statistics.median(response_times),
                "stdev": (
                    statistics.stdev(response_times) if len(response_times) > 1 else 0
                ),
            },
            "query_counts": {
                "min": min(query_counts),
                "max": max(query_counts),
                "mean": statistics.mean(query_counts),
                "median": statistics.median(query_counts),
            },
            "status_codes": list(set(status_codes)),
            "iterations": self.iterations,
        }

    def output_results(self, results):
        """Output test results"""
        if self.output_format == "json":
            self.stdout.write(json.dumps(results, indent=2))
        else:
            self.output_table_results(results)

    def output_table_results(self, results):
        """Output results in table format"""
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("PERFORMANCE TEST RESULTS"))
        self.stdout.write("=" * 80)

        for endpoint, metrics in results.items():
            self.stdout.write(f"\nEndpoint: {endpoint}")
            self.stdout.write("-" * 50)

            # Response times
            rt = metrics["response_times"]
            self.stdout.write("Response Times (seconds):")
            self.stdout.write(f'  Min:    {rt["min"]:.3f}s')
            self.stdout.write(f'  Max:    {rt["max"]:.3f}s')
            self.stdout.write(f'  Mean:   {rt["mean"]:.3f}s')
            self.stdout.write(f'  Median: {rt["median"]:.3f}s')
            self.stdout.write(f'  StdDev: {rt["stdev"]:.3f}s')

            # Query counts
            qc = metrics["query_counts"]
            self.stdout.write("\nDatabase Queries:")
            self.stdout.write(f'  Min:    {qc["min"]:.0f}')
            self.stdout.write(f'  Max:    {qc["max"]:.0f}')
            self.stdout.write(f'  Mean:   {qc["mean"]:.1f}')
            self.stdout.write(f'  Median: {qc["median"]:.0f}')

            # Status codes
            self.stdout.write(f'\nStatus Codes: {metrics["status_codes"]}')

            # Performance analysis
            self.analyze_performance(endpoint, metrics)

    def analyze_performance(self, endpoint, metrics):
        """Analyze performance and provide recommendations"""
        rt = metrics["response_times"]
        qc = metrics["query_counts"]

        issues = []
        recommendations = []

        # Check response time
        if rt["mean"] > 1.0:
            issues.append(f"Slow response time: {rt['mean']:.3f}s average")
            recommendations.append("Consider adding caching or optimizing queries")

        # Check query count
        if qc["mean"] > 20:
            issues.append(f"High query count: {qc['mean']:.1f} average")
            recommendations.append(
                "Consider using select_related() or prefetch_related()"
            )

        # Check consistency
        if rt["stdev"] > rt["mean"] * 0.5:
            issues.append("Inconsistent response times")
            recommendations.append("Check for intermittent performance issues")

        if issues:
            self.stdout.write(f'\n{self.style.WARNING("Performance Issues:")}')
            for issue in issues:
                self.stdout.write(f"  ⚠ {issue}")

            self.stdout.write(f'\n{self.style.SUCCESS("Recommendations:")}')
            for rec in recommendations:
                self.stdout.write(f"  💡 {rec}")
        else:
            self.stdout.write(f'\n{self.style.SUCCESS("✓ Performance looks good!")}')

    def cleanup(self):
        """Clean up test data"""
        # Remove test user if created
        User.objects.filter(username="perf_test_user").delete()
