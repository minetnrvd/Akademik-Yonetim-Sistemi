import unittest

from app import app


class PublicUiSmokeTests(unittest.TestCase):
    def test_login_page_renders_core_elements(self):
        client = app.test_client()
        response = client.get('/login', follow_redirects=False)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<main id="main-content">', response.data)
        self.assertIn(b'Skip to content', response.data)
        self.assertIn(b'name="email"', response.data)
        self.assertIn(b'name="password"', response.data)

    def test_register_page_renders_role_and_password_fields(self):
        client = app.test_client()
        response = client.get('/register', follow_redirects=False)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'name="role"', response.data)
        self.assertIn(b'name="password"', response.data)

    def test_404_page_is_user_friendly(self):
        client = app.test_client()
        response = client.get('/this-page-does-not-exist', follow_redirects=False)

        self.assertEqual(response.status_code, 404)
        self.assertIn(b'Page Not Found', response.data)


if __name__ == '__main__':
    unittest.main()
