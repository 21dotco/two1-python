from django.test import TestCase
import two1.djangobitcoin.djangobitcoin.settings as settings
settings.STATIC_SERVE_CONFIG += '.test'
from two1.djangobitcoin.static_serve.static_serve import get_config

class ConfigurationsTests(TestCase):
    def test_info_for_path_items(self):
        configurations = get_config()
        info, mlists = configurations.infoForPathItems(['serve', 'kittens', 'kitty.jpg'])
        self.assertEqual(info['localPath'], '~/Documents/Kittens/red.jpeg')

# TODO need to use injected config instead of one from file system
# class StaticServeTests(TestCase):
#     def test_get_target_path(self):
#         target_path = getTargetPath('/serve/kittens/kitty.jpg')
#         self.assertTrue(target_path['path'].endswith('/Documents/Kittens/red.jpeg'))
