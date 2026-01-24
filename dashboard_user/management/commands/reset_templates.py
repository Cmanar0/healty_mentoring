from django.core.management.base import BaseCommand
from django.db import transaction
from dashboard_user.models import (
    ProjectTemplate, Questionnaire, Question, ProjectModule
)


class Command(BaseCommand):
    help = 'Delete all templates and create new default templates with questionnaires and questions'

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
                    'Run with --confirm to proceed.'
                )
            )
            return

        with transaction.atomic():
            # Delete all existing data
            self.stdout.write('Deleting existing data...')
            
            # Delete in correct order to avoid foreign key issues
            Question.objects.all().delete()
            Questionnaire.objects.all().delete()
            ProjectTemplate.objects.all().delete()
            
            self.stdout.write(self.style.SUCCESS('Deleted all existing templates and related data.'))

            # Get all modules for preselection
            all_modules = {m.module_type: m for m in ProjectModule.objects.all()}
            
            # Define new templates with their questionnaires and questions
            templates_data = {
                'Business Plan': {
                    'description': 'Create a comprehensive business plan to launch or grow your business',
                    'icon': 'fas fa-briefcase',
                    'color': '#3b82f6',
                    'preselected_modules': ['financial_planning', 'risk_assessment', 'stakeholder_feedback', 'resource_management'],
                    'questions': [
                        {
                            'question_text': 'What is your business idea or current business status?',
                            'question_type': 'textarea',
                            'is_required': True,
                            'help_text': 'Describe your business concept, current stage, or what you want to achieve.',
                            'order': 1,
                        },
                        {
                            'question_text': 'Who is your target market or ideal customer?',
                            'question_type': 'textarea',
                            'is_required': True,
                            'help_text': 'Describe your ideal customer demographics, needs, and pain points.',
                            'order': 2,
                        },
                        {
                            'question_text': 'What is your unique value proposition?',
                            'question_type': 'textarea',
                            'is_required': True,
                            'help_text': 'What makes your business different from competitors?',
                            'order': 3,
                        },
                        {
                            'question_text': 'What is your target launch or completion date?',
                            'question_type': 'date',
                            'is_required': False,
                            'help_text': 'When do you want to launch or achieve your business goals?',
                            'order': 4,
                        },
                        {
                            'question_text': 'What is your budget or funding situation?',
                            'question_type': 'textarea',
                            'is_required': False,
                            'help_text': 'Describe your available budget, funding sources, or financial constraints.',
                            'order': 5,
                        },
                        {
                            'question_text': 'What are your main challenges or concerns?',
                            'question_type': 'textarea',
                            'is_required': False,
                            'help_text': 'List any obstacles, risks, or concerns you anticipate.',
                            'order': 6,
                        },
                    ]
                },
                'Weight Loss': {
                    'description': 'Develop a personalized weight loss plan to achieve your health goals',
                    'icon': 'fas fa-heartbeat',
                    'color': '#10b981',
                    'preselected_modules': ['health_metrics', 'habit_tracking', 'progress_tracking', 'milestone_checkpoints'],
                    'questions': [
                        {
                            'question_text': 'What is your current weight and target weight?',
                            'question_type': 'textarea',
                            'is_required': True,
                            'help_text': 'Share your current weight and your goal weight.',
                            'order': 1,
                        },
                        {
                            'question_text': 'What is your target completion date?',
                            'question_type': 'date',
                            'is_required': True,
                            'help_text': 'When would you like to reach your weight loss goal?',
                            'order': 2,
                        },
                        {
                            'question_text': 'What is your current diet and eating habits?',
                            'question_type': 'textarea',
                            'is_required': True,
                            'help_text': 'Describe your current eating patterns, meals, and any dietary restrictions.',
                            'order': 3,
                        },
                        {
                            'question_text': 'What is your current activity level?',
                            'question_type': 'select',
                            'is_required': True,
                            'help_text': 'Select your current level of physical activity.',
                            'options': ['Sedentary (little to no exercise)', 'Lightly active (light exercise 1-3 days/week)', 'Moderately active (moderate exercise 3-5 days/week)', 'Very active (hard exercise 6-7 days/week)', 'Extremely active (physical job + hard exercise)'],
                            'order': 4,
                        },
                        {
                            'question_text': 'What are your main challenges with weight loss?',
                            'question_type': 'textarea',
                            'is_required': False,
                            'help_text': 'What has made it difficult to lose weight in the past?',
                            'order': 5,
                        },
                        {
                            'question_text': 'What support systems do you have in place?',
                            'question_type': 'textarea',
                            'is_required': False,
                            'help_text': 'Family, friends, gym membership, nutritionist, etc.',
                            'order': 6,
                        },
                    ]
                },
                'Trading': {
                    'description': 'Build a systematic trading strategy and develop your trading skills',
                    'icon': 'fas fa-chart-line',
                    'color': '#f59e0b',
                    'preselected_modules': ['financial_planning', 'progress_tracking', 'risk_assessment', 'milestone_checkpoints'],
                    'questions': [
                        {
                            'question_text': 'What is your trading experience level?',
                            'question_type': 'select',
                            'is_required': True,
                            'help_text': 'Select your current experience level.',
                            'options': ['Complete beginner', 'Beginner (some knowledge, no trading)', 'Intermediate (some trading experience)', 'Advanced (experienced trader)', 'Professional'],
                            'order': 1,
                        },
                        {
                            'question_text': 'What markets or instruments do you want to trade?',
                            'question_type': 'multiselect',
                            'is_required': True,
                            'help_text': 'Select all that apply.',
                            'options': ['Stocks', 'Forex', 'Cryptocurrency', 'Options', 'Futures', 'Commodities', 'Indices', 'Other'],
                            'order': 2,
                        },
                        {
                            'question_text': 'What is your trading capital or starting amount?',
                            'question_type': 'select',
                            'is_required': True,
                            'help_text': 'Select the range that best describes your trading capital.',
                            'options': ['Under $1,000', '$1,000 - $5,000', '$5,000 - $25,000', '$25,000 - $100,000', 'Over $100,000', 'Not applicable (paper trading)'],
                            'order': 3,
                        },
                        {
                            'question_text': 'What is your primary trading goal?',
                            'question_type': 'textarea',
                            'is_required': True,
                            'help_text': 'What do you want to achieve through trading? (e.g., supplemental income, full-time trading, learning, etc.)',
                            'order': 4,
                        },
                        {
                            'question_text': 'What is your risk tolerance?',
                            'question_type': 'select',
                            'is_required': True,
                            'help_text': 'How much risk are you comfortable taking?',
                            'options': ['Very conservative (minimal risk)', 'Conservative (low risk)', 'Moderate (balanced risk)', 'Aggressive (high risk)', 'Very aggressive (maximum risk)'],
                            'order': 5,
                        },
                        {
                            'question_text': 'What are your main challenges or concerns with trading?',
                            'question_type': 'textarea',
                            'is_required': False,
                            'help_text': 'What obstacles or fears do you have about trading?',
                            'order': 6,
                        },
                    ]
                },
                'Mindset': {
                    'description': 'Transform your mindset and develop empowering beliefs for personal growth',
                    'icon': 'fas fa-brain',
                    'color': '#8b5cf6',
                    'preselected_modules': ['identity_mindset', 'habit_tracking', 'progress_tracking', 'milestone_checkpoints'],
                    'questions': [
                        {
                            'question_text': 'What is your current mindset situation?',
                            'question_type': 'textarea',
                            'is_required': True,
                            'help_text': 'Describe your current thought patterns, beliefs, and mental state.',
                            'order': 1,
                        },
                        {
                            'question_text': 'What limiting beliefs do you want to overcome?',
                            'question_type': 'textarea',
                            'is_required': True,
                            'help_text': 'What negative thoughts or beliefs are holding you back?',
                            'order': 2,
                        },
                        {
                            'question_text': 'What is your desired mindset or mental state?',
                            'question_type': 'textarea',
                            'is_required': True,
                            'help_text': 'How do you want to think and feel? What empowering beliefs do you want to develop?',
                            'order': 3,
                        },
                        {
                            'question_text': 'What areas of your life do you want to improve?',
                            'question_type': 'multiselect',
                            'is_required': True,
                            'help_text': 'Select all areas where mindset change would help.',
                            'options': ['Career/Work', 'Relationships', 'Health & Fitness', 'Finances', 'Personal Growth', 'Confidence/Self-esteem', 'Stress Management', 'Goal Achievement', 'Other'],
                            'order': 4,
                        },
                        {
                            'question_text': 'What triggers your negative mindset patterns?',
                            'question_type': 'textarea',
                            'is_required': False,
                            'help_text': 'What situations, people, or thoughts tend to trigger limiting beliefs?',
                            'order': 5,
                        },
                        {
                            'question_text': 'What practices or techniques have you tried before?',
                            'question_type': 'textarea',
                            'is_required': False,
                            'help_text': 'Have you tried meditation, affirmations, therapy, or other mindset work?',
                            'order': 6,
                        },
                    ]
                },
                'Custom (Blank)': {
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
                        },
                        {
                            'question_text': 'What is your current situation or starting point?',
                            'question_type': 'textarea',
                            'is_required': True,
                            'help_text': 'Where are you starting from? What is your current state?',
                            'order': 2,
                        },
                        {
                            'question_text': 'What is your target completion date or timeline?',
                            'question_type': 'date',
                            'is_required': False,
                            'help_text': 'When do you want to complete this project?',
                            'order': 3,
                        },
                        {
                            'question_text': 'What are the key challenges or obstacles you anticipate?',
                            'question_type': 'textarea',
                            'is_required': False,
                            'help_text': 'List any potential difficulties, barriers, or concerns.',
                            'order': 4,
                        },
                        {
                            'question_text': 'What resources or support do you have available?',
                            'question_type': 'textarea',
                            'is_required': False,
                            'help_text': 'Describe any resources, tools, people, or support systems you have.',
                            'order': 5,
                        },
                        {
                            'question_text': 'How will you measure success?',
                            'question_type': 'textarea',
                            'is_required': False,
                            'help_text': 'What metrics, milestones, or indicators will show that you\'ve achieved your goal?',
                            'order': 6,
                        },
                    ]
                },
            }

            # Create templates with questionnaires and questions
            self.stdout.write('Creating new default templates...')
            
            for template_name, template_data in templates_data.items():
                # Create template
                template = ProjectTemplate.objects.create(
                    name=template_name,
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
                    )
                
                # Set preselected modules
                preselected_module_types = template_data.get('preselected_modules', [])
                preselected_modules = [all_modules[mt] for mt in preselected_module_types if mt in all_modules]
                if preselected_modules:
                    template.preselected_modules.set(preselected_modules)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Created "{template_name}" with {len(template_data["questions"])} questions and {len(preselected_modules)} preselected modules'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully created {len(templates_data)} default templates with questionnaires and questions!'
            )
        )
