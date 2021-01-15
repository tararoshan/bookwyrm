''' sending out activities '''
import json

from django.http import JsonResponse
from django.test import TestCase
from django.test.client import RequestFactory

from bookwyrm import models, views


# pylint: disable=too-many-public-methods
class OutboxView(TestCase):
    ''' sends out activities '''
    def setUp(self):
        ''' we'll need some data '''
        self.factory = RequestFactory()
        self.local_user = models.User.objects.create_user(
            'mouse@local.com', 'mouse@mouse.com', 'mouseword',
            local=True, localname='mouse',
            remote_id='https://example.com/users/mouse',
        )
        work = models.Work.objects.create(title='Test Work')
        self.book = models.Edition.objects.create(
            title='Example Edition',
            remote_id='https://example.com/book/1',
            parent_work=work
        )


    def test_outbox(self):
        ''' returns user's statuses '''
        request = self.factory.get('')
        result = views.Outbox.as_view()(request, 'mouse')
        self.assertIsInstance(result, JsonResponse)

    def test_outbox_bad_method(self):
        ''' can't POST to outbox '''
        request = self.factory.post('')
        result = views.Outbox.as_view()(request, 'mouse')
        self.assertEqual(result.status_code, 405)

    def test_outbox_unknown_user(self):
        ''' should 404 for unknown and remote users '''
        request = self.factory.post('')
        result = views.Outbox.as_view()(request, 'beepboop')
        self.assertEqual(result.status_code, 405)
        result = views.Outbox.as_view()(request, 'rat')
        self.assertEqual(result.status_code, 405)

    def test_outbox_privacy(self):
        ''' don't show dms et cetera in outbox '''
        models.Status.objects.create(
            content='PRIVATE!!', user=self.local_user, privacy='direct')
        models.Status.objects.create(
            content='bffs ONLY', user=self.local_user, privacy='followers')
        models.Status.objects.create(
            content='unlisted status', user=self.local_user, privacy='unlisted')
        models.Status.objects.create(
            content='look at this', user=self.local_user, privacy='public')

        request = self.factory.get('')
        result = views.Outbox.as_view()(request, 'mouse')
        self.assertIsInstance(result, JsonResponse)
        data = json.loads(result.content)
        self.assertEqual(data['type'], 'OrderedCollection')
        self.assertEqual(data['totalItems'], 2)

    def test_outbox_filter(self):
        ''' if we only care about reviews, only get reviews '''
        models.Review.objects.create(
            content='look at this', name='hi', rating=1,
            book=self.book, user=self.local_user)
        models.Status.objects.create(
            content='look at this', user=self.local_user)

        request = self.factory.get('', {'type': 'bleh'})
        result = views.Outbox.as_view()(request, 'mouse')
        self.assertIsInstance(result, JsonResponse)
        data = json.loads(result.content)
        self.assertEqual(data['type'], 'OrderedCollection')
        self.assertEqual(data['totalItems'], 2)

        request = self.factory.get('', {'type': 'Review'})
        result = views.Outbox.as_view()(request, 'mouse')
        self.assertIsInstance(result, JsonResponse)
        data = json.loads(result.content)
        self.assertEqual(data['type'], 'OrderedCollection')
        self.assertEqual(data['totalItems'], 1)
