from django.core.management.base import BaseCommand
from django.core.cache import cache


class Command(BaseCommand):
    help = "Seed sample cache values for development"

    def handle(self, *args, **options):
        cache.set("demo:key", "redis-working", 60)
        self.stdout.write(self.style.SUCCESS("Seeded Redis demo cache"))
