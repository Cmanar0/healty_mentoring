from django.core.management.base import BaseCommand
from django.db import transaction
from dashboard_user.models import (
    ProjectTemplate, Questionnaire, Question, ProjectModule
)


class Command(BaseCommand):
    help = 'Delete all templates and create only the blank template with default questionnaire. Modules are preserved.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion of all existing templates',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    'This will delete ALL templates, questionnaires, and questions!\n'
                    'Only the "Custom (Blank)" template will be recreated with default questionnaire.\n'
                    'Modules will be preserved.\n'
                    'Run with --confirm to proceed.'
                )
            )
            return

        with transaction.atomic():
            # Delete all existing templates and questionnaires
            self.stdout.write('Deleting existing templates and questionnaires...')
            
            # Delete in correct order to avoid foreign key issues
            Question.objects.all().delete()
            Questionnaire.objects.all().delete()
            ProjectTemplate.objects.all().delete()
            
            self.stdout.write(self.style.SUCCESS('Deleted all existing templates and related data.'))

            # Get all modules for preselection (modules are preserved, not deleted)
            all_modules = {m.module_type: m for m in ProjectModule.objects.all()}
            
            # Only create the "Custom (Blank)" template with default questionnaire
            template_data = {
                'description': 'A flexible blank template for custom projects with general-purpose questions',
                'icon': 'fas fa-file-alt',
                'color': '#64748b',
                'preselected_modules': ['progress_tracking', 'milestone_checkpoints'],
                'questions': [
                    {
                        'question_text': 'What is the main goal or objective of this project?',
                        'question_type': 'textarea',
                        'is_required': True,
                        'help_text': 'Describe the primary purpose and desired outcome of this project.',
                        'order': 1,
                        'is_target_date': False,
                    },
                    {
                        'question_text': 'What is your current situation or starting point?',
                        'question_type': 'textarea',
                        'is_required': True,
                        'help_text': 'Where are you starting from? What is your current state?',
                        'order': 2,
                        'is_target_date': False,
                    },
                    {
                        'question_text': 'Target Date',
                        'question_type': 'date',
                        'is_required': False,
                        'help_text': 'When do you want to complete this project?',
                        'order': 3,
                        'is_target_date': True,  # Mark as target date question
                    },
                    {
                        'question_text': 'What are the key challenges or obstacles you anticipate?',
                        'question_type': 'textarea',
                        'is_required': False,
                        'help_text': 'List any potential difficulties, barriers, or concerns.',
                        'order': 4,
                        'is_target_date': False,
                    },
                    {
                        'question_text': 'What resources or support do you have available?',
                        'question_type': 'textarea',
                        'is_required': False,
                        'help_text': 'Describe any resources, tools, people, or support systems you have.',
                        'order': 5,
                        'is_target_date': False,
                    },
                    {
                        'question_text': 'How will you measure success?',
                        'question_type': 'textarea',
                        'is_required': False,
                        'help_text': 'What metrics, milestones, or indicators will show that you\'ve achieved your goal?',
                        'order': 6,
                        'is_target_date': False,
                    },
                ]
            }

            # Create the blank template
            self.stdout.write('Creating blank template with default questionnaire...')
            
            template = ProjectTemplate.objects.create(
                name='Custom (Blank)',
                description=template_data['description'],
                icon=template_data['icon'],
                color=template_data['color'],
                is_custom=False,
                author=None,
                is_active=True,
                order=0,
            )
            
            # Create questionnaire (should be auto-created by signal, but ensure it exists)
            questionnaire, created = Questionnaire.objects.get_or_create(
                template=template,
                defaults={'title': 'Onboarding Questionnaire'}
            )
            
            # Create questions
            for question_data in template_data['questions']:
                Question.objects.create(
                    questionnaire=questionnaire,
                    question_text=question_data['question_text'],
                    question_type=question_data['question_type'],
                    is_required=question_data['is_required'],
                    help_text=question_data.get('help_text', ''),
                    options=question_data.get('options', []),
                    order=question_data['order'],
                    is_target_date=question_data.get('is_target_date', False),
                )
            
            # Set preselected modules
            preselected_module_types = template_data.get('preselected_modules', [])
            preselected_modules = [all_modules[mt] for mt in preselected_module_types if mt in all_modules]
            if preselected_modules:
                template.preselected_modules.set(preselected_modules)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Created "Custom (Blank)" template with {len(template_data["questions"])} questions and {len(preselected_modules)} preselected modules'
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                '\nSuccessfully created blank template with default questionnaire!\n'
                'Modules have been preserved. Mentors can now create their own templates.'
            )
        )
