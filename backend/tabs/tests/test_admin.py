import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from tabs.models import Debate, Team

pytestmark = pytest.mark.django_db

MODELS = ['team', 'adjudicator', 'room', 'round', 'debate', 'result', 'bye']


@pytest.fixture
def admin_client(db: None) -> Client:
    User.objects.create_superuser('admin', 'admin@example.com', 'pw')
    client = Client()
    client.login(username='admin', password='pw')
    return client


@pytest.mark.parametrize('model', MODELS)
def test_changelist_loads_for_admin(admin_client: Client, model: str) -> None:
    assert admin_client.get(reverse(f'admin:tabs_{model}_changelist')).status_code == 200


@pytest.mark.parametrize('model', MODELS)
def test_add_form_loads_for_admin(admin_client: Client, model: str) -> None:
    assert admin_client.get(reverse(f'admin:tabs_{model}_add')).status_code == 200


def test_debate_change_page_shows_adjudicator_inline(admin_client: Client, debate: Debate) -> None:
    response = admin_client.get(reverse('admin:tabs_debate_change', args=[debate.pk]))
    assert response.status_code == 200
    assert b'adjudicators' in response.content


def test_team_can_be_created_through_admin(admin_client: Client) -> None:
    response = admin_client.post(
        reverse('admin:tabs_team_add'), {'name': 'Hand made', 'institution': 'Uni'}
    )
    assert response.status_code == 302
    assert Team.objects.filter(name='Hand made').exists()


def test_anonymous_cannot_reach_admin() -> None:
    response = Client().get(reverse('admin:tabs_team_changelist'))
    assert response.status_code == 302
    assert '/admin/login/' in response['Location']


def test_api_defaults_are_read_only_for_the_public() -> None:
    from django.conf import settings

    perms = settings.REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES']
    assert perms == ['rest_framework.permissions.IsAuthenticatedOrReadOnly']
