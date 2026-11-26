from django.core.management.base import BaseCommand
from apps.question_generation.models import QuestionGenerationJob
from apps.question_generation.services import process_job


class Command(BaseCommand):
    help = 'Process bounded queued source-grounded question-generation jobs (staff-only intake).'

    def add_arguments(self, parser):
        parser.add_argument('--limit',type=int,default=3)

    def handle(self,*args,**options):
        count=max(0,min(options['limit'],10))
        ids=list(QuestionGenerationJob.objects.filter(state=QuestionGenerationJob.State.QUEUED)
                 .order_by('created_at').values_list('pk',flat=True)[:count])
        for id in ids:
            outcome=process_job(id)
            self.stdout.write(f'{id}: {outcome}')
