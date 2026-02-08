"""
Django management command to auto-generate mentor guides and one subtask per guide.

Images: uses static/images/guide_1.png .. guide_4.png for the first 4 guides,
then reuses static/images/setup_profile.png for the rest (saved under unique names in media/guides/).

Usage:
    python manage.py generate_guides

Options:
    --clear    Delete all existing Guide and GuideStep rows before creating (default: skip if any exist).
"""

import os
from django.core.management.base import BaseCommand
from django.core.files import File
from django.conf import settings
from django.urls import reverse


class Command(BaseCommand):
    help = 'Create mentor guides and one subtask per guide (images from static/images/).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete all existing guides and steps before creating new ones.',
        )

    def handle(self, *args, **options):
        from dashboard_mentor.models import Guide, GuideStep

        base_dir = settings.BASE_DIR
        static_images = os.path.join(base_dir, 'static', 'images')

        # Guide definitions. First guide has multiple subtasks; others have one subtask each.
        profile_url = reverse('general:dashboard_mentor:profile')
        setup_profile_subtasks = [
            {'name': 'Complete at least 80% of your profile', 'button_name': 'Go to profile', 'action_id': 'guide_setup_profile_80', 'order': 0},
            {'name': 'Set your Mentor Type', 'button_name': 'Set type', 'action_id': 'guide_setup_mentor_type', 'order': 1},
            {'name': 'Set your Bio', 'button_name': 'Set bio', 'action_id': 'guide_setup_bio', 'order': 2},
            {'name': 'Set your Languages', 'button_name': 'Set languages', 'action_id': 'guide_setup_languages', 'order': 3},
            {'name': 'Set your Categories', 'button_name': 'Set categories', 'action_id': 'guide_setup_categories', 'order': 4},
            {'name': 'Set pricing for your session', 'button_name': 'Set pricing', 'action_id': 'guide_setup_pricing', 'order': 5},
            {'name': 'Set your Session Length', 'button_name': 'Set length', 'action_id': 'guide_setup_session_length', 'order': 6},
        ]
        guides_data = [
            {
                'name': 'Setup Your Profile',
                'subtitle': 'Be visible',
                'description': 'Complete your profile so mentees can find you and trust your expertise.',
                'button_name': 'Go to profile',
                'step_url_name': 'general:dashboard_mentor:profile',
                'action_id': 'guide_setup_profile',
                'subtasks': setup_profile_subtasks,
                'step_url_override': profile_url,
            },
            {
                'name': 'Set Your Availability',
                'subtitle': 'When you can mentor',
                'description': 'Define when you are available for sessions so clients can book you.',
                'button_name': 'Set availability',
                'step_url_name': 'general:dashboard_mentor:my_sessions',
                'action_id': 'guide_availability',
            },
            {
                'name': 'Invite Your First Client',
                'subtitle': 'Grow your practice',
                'description': 'Invite clients to connect and start your first mentoring relationship.',
                'button_name': 'Invite client',
                'step_url_name': 'general:dashboard_mentor:invite_client',
                'action_id': 'guide_invite_client',
            },
            {
                'name': 'Create a Project Template',
                'subtitle': 'Structure your work',
                'description': 'Templates help you deliver consistent value across clients.',
                'button_name': 'Templates',
                'step_url_name': 'general:dashboard_mentor:templates_list',
                'action_id': 'guide_templates',
            },
            {
                'name': 'Schedule a Session',
                'subtitle': 'Book time with clients',
                'description': 'Create and manage sessions from your calendar.',
                'button_name': 'My sessions',
                'step_url_name': 'general:dashboard_mentor:my_sessions',
                'action_id': 'guide_schedule_session',
            },
            {
                'name': 'Explore Your Dashboard',
                'subtitle': 'Stay on top of things',
                'description': 'Use stats, backlog, and education to run your practice.',
                'button_name': 'Dashboard',
                'step_url_name': 'general:dashboard_mentor:dashboard',
                'action_id': 'guide_dashboard',
            },
        ]

        if options['clear']:
            count_guides = Guide.objects.count()
            GuideStep.objects.all().delete()
            Guide.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Cleared {count_guides} guides and their steps.'))

        if Guide.objects.exists() and not options['clear']:
            self.stdout.write(self.style.WARNING('Guides already exist. Use --clear to replace them.'))
            return

        # Image sources: guide_1.png .. guide_5.png; reuse guide_5.png for 6th guide and beyond
        def image_path_for_index(i):
            return os.path.join(static_images, f'guide_{min(i + 1, 5)}.png')

        created = 0
        for order, g in enumerate(guides_data):
            guide = Guide(
                name=g['name'],
                subtitle=g.get('subtitle', ''),
                description=g.get('description', ''),
                button_name=g['button_name'],
                order=order,
                is_active=True,
            )
            guide.save()

            # Attach image: copy from static to media/guides/
            img_path = image_path_for_index(order)
            if os.path.isfile(img_path):
                save_name = f'guide_{order + 1}.png' if order < 5 else f'guide_5_{order + 1}.png'
                with open(img_path, 'rb') as f:
                    guide.image.save(save_name, File(f), save=True)
                self.stdout.write(f'  Guide "{guide.name}" image: {save_name}')
            else:
                self.stdout.write(self.style.WARNING(f'  Image not found: {img_path}'))

            # Subtasks: multiple for first guide, one per guide for the rest
            step_url_base = g.get('step_url_override') or (reverse(g['step_url_name']) if g.get('step_url_name') else '')
            subtasks_def = g.get('subtasks')
            if subtasks_def:
                for st in subtasks_def:
                    step = GuideStep(
                        guide=guide,
                        name=st['name'],
                        subtitle=st.get('subtitle', ''),
                        description=st.get('description', ''),
                        button_name=st.get('button_name', 'Go'),
                        url=step_url_base,
                        action_id=st.get('action_id', ''),
                        order=st.get('order', 0),
                        is_active=True,
                    )
                    step.save()
                    created += 1
                    self.stdout.write(self.style.SUCCESS(f'    Subtask "{step.name}" (pk={step.pk}), action_id={step.action_id or "(none)"}'))
            else:
                try:
                    step_url = reverse(g['step_url_name'])
                except Exception:
                    step_url = ''
                step = GuideStep(
                    guide=guide,
                    name=g['name'],
                    subtitle=g.get('subtitle', ''),
                    description=g.get('description', ''),
                    button_name=g['button_name'],
                    url=step_url,
                    action_id=g.get('action_id', ''),
                    order=0,
                    is_active=True,
                )
                step.save()
                created += 1
                self.stdout.write(self.style.SUCCESS(f'  Created guide "{guide.name}" (pk={guide.pk}) + 1 subtask (pk={step.pk}), action_id={step.action_id or "(none)"}'))

        self.stdout.write(self.style.SUCCESS(f'Done. Created {created} guides and subtasks.'))
