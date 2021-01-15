''' test for app action functionality '''
from unittest.mock import patch
from django.template.response import TemplateResponse
from django.test import TestCase
from django.test.client import RequestFactory

from bookwyrm import models, views
from bookwyrm.activitypub import ActivitypubResponse


class ShelfViews(TestCase):
    ''' tag views'''
    def setUp(self):
        ''' we need basic test data and mocks '''
        self.factory = RequestFactory()
        self.local_user = models.User.objects.create_user(
            'mouse@local.com', 'mouse@mouse.com', 'mouseword',
            local=True, localname='mouse',
            remote_id='https://example.com/users/mouse',
        )
        self.work = models.Work.objects.create(title='Test Work')
        self.book = models.Edition.objects.create(
            title='Example Edition',
            remote_id='https://example.com/book/1',
            parent_work=self.work
        )
        self.shelf = models.Shelf.objects.create(
            name='Test Shelf',
            identifier='test-shelf',
            user=self.local_user
        )


    def test_shelf_page(self):
        ''' there are so many views, this just makes sure it LOADS '''
        view = views.Shelf.as_view()
        shelf = self.local_user.shelf_set.first()
        request = self.factory.get('')
        request.user = self.local_user
        with patch('bookwyrm.views.shelf.is_api_request') as is_api:
            is_api.return_value = False
            result = view(request, self.local_user.username, shelf.identifier)
        self.assertIsInstance(result, TemplateResponse)
        self.assertEqual(result.template_name, 'shelf.html')
        self.assertEqual(result.status_code, 200)

        with patch('bookwyrm.views.shelf.is_api_request') as is_api:
            is_api.return_value = True
            result = view(
                request, self.local_user.username, shelf.identifier)
        self.assertIsInstance(result, ActivitypubResponse)
        self.assertEqual(result.status_code, 200)

        request = self.factory.get('/?page=1')
        request.user = self.local_user
        with patch('bookwyrm.views.shelf.is_api_request') as is_api:
            is_api.return_value = True
            result = view(
                request, self.local_user.username, shelf.identifier)
        self.assertIsInstance(result, ActivitypubResponse)
        self.assertEqual(result.status_code, 200)


    def test_edit_shelf_privacy(self):
        ''' set name or privacy on shelf '''
        view = views.Shelf.as_view()
        shelf = self.local_user.shelf_set.get(identifier='to-read')
        self.assertEqual(shelf.privacy, 'public')

        request = self.factory.post(
            '', {
                'privacy': 'unlisted',
                'user': self.local_user.id,
                'name': 'To Read',
            })
        request.user = self.local_user
        view(request, self.local_user.username, shelf.id)
        shelf.refresh_from_db()

        self.assertEqual(shelf.privacy, 'unlisted')


    def test_edit_shelf_name(self):
        ''' change the name of an editable shelf '''
        view = views.Shelf.as_view()
        shelf = models.Shelf.objects.create(
            name='Test Shelf', user=self.local_user)
        self.assertEqual(shelf.privacy, 'public')

        request = self.factory.post(
            '', {
                'privacy': 'public',
                'user': self.local_user.id,
                'name': 'cool name'
            })
        request.user = self.local_user
        view(request, request.user.username, shelf.id)
        shelf.refresh_from_db()

        self.assertEqual(shelf.name, 'cool name')
        self.assertEqual(shelf.identifier, 'testshelf-%d' % shelf.id)


    def test_edit_shelf_name_not_editable(self):
        ''' can't change the name of an non-editable shelf '''
        view = views.Shelf.as_view()
        shelf = self.local_user.shelf_set.get(identifier='to-read')
        self.assertEqual(shelf.privacy, 'public')

        request = self.factory.post(
            '', {
                'privacy': 'public',
                'user': self.local_user.id,
                'name': 'cool name'
            })
        request.user = self.local_user
        view(request, request.user.username, shelf.id)

        self.assertEqual(shelf.name, 'To Read')


    def test_handle_shelve(self):
        ''' shelve a book '''
        request = self.factory.post('', {
            'book': self.book.id,
            'shelf': self.shelf.identifier
        })
        request.user = self.local_user
        with patch('bookwyrm.broadcast.broadcast_task.delay'):
            views.shelve(request)
        # make sure the book is on the shelf
        self.assertEqual(self.shelf.books.get(), self.book)


    def test_handle_shelve_to_read(self):
        ''' special behavior for the to-read shelf '''
        shelf = models.Shelf.objects.get(identifier='to-read')
        request = self.factory.post('', {
            'book': self.book.id,
            'shelf': shelf.identifier
        })
        request.user = self.local_user

        with patch('bookwyrm.broadcast.broadcast_task.delay'):
            views.shelve(request)
        # make sure the book is on the shelf
        self.assertEqual(shelf.books.get(), self.book)


    def test_handle_shelve_reading(self):
        ''' special behavior for the reading shelf '''
        shelf = models.Shelf.objects.get(identifier='reading')
        request = self.factory.post('', {
            'book': self.book.id,
            'shelf': shelf.identifier
        })
        request.user = self.local_user

        with patch('bookwyrm.broadcast.broadcast_task.delay'):
            views.shelve(request)
        # make sure the book is on the shelf
        self.assertEqual(shelf.books.get(), self.book)


    def test_handle_shelve_read(self):
        ''' special behavior for the read shelf '''
        shelf = models.Shelf.objects.get(identifier='read')
        request = self.factory.post('', {
            'book': self.book.id,
            'shelf': shelf.identifier
        })
        request.user = self.local_user

        with patch('bookwyrm.broadcast.broadcast_task.delay'):
            views.shelve(request)
        # make sure the book is on the shelf
        self.assertEqual(shelf.books.get(), self.book)


    def test_handle_unshelve(self):
        ''' remove a book from a shelf '''
        self.shelf.books.add(self.book)
        self.shelf.save()
        self.assertEqual(self.shelf.books.count(), 1)
        request = self.factory.post('', {
            'book': self.book.id,
            'shelf': self.shelf.id
        })
        request.user = self.local_user
        with patch('bookwyrm.broadcast.broadcast_task.delay'):
            views.unshelve(request)
        self.assertEqual(self.shelf.books.count(), 0)
