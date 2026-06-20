from django.core.management.base import BaseCommand
from django.utils import timezone
from campaigns.models import Task


class Command(BaseCommand):
    help = 'Release all tasks whose 10-minute lock has expired'

    def handle(self, *args, **options):
        now = timezone.now()
        cutoff = now - timezone.timedelta(minutes=10)

        expired = Task.objects.filter(
            status='visited',
            locked_at__isnull=False,
            locked_at__lte=cutoff,
        )

        count = 0
        for task in expired:
            task.release_if_expired()
            count += 1

        self.stdout.write(f'Released {count} expired task(s)')
