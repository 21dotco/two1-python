import json
from unittest import skip

import os
from django.test import Client
from django.test import TestCase
import two1.examples.server.settings as settings

settings.ENDPOINTS_FILE = 'endpoints_test.json'

def response2json(response):
    j = json.loads(response.content.decode("utf-8"))
    print(j)
    return j


class ChartsTests(TestCase):
    def test_chart(self):
        chart_data = """
{
	"labels": ["South", "East", "North", "West"],
	"series": [{
		"Bitcoin": [200, 150, 300, 60]
	}, {
		"Litecoin": [20, 190, 40, 30]
	}],
	"title": "Cryptocurrencies"
}
"""
        response = Client().post("/charts/chart?chart_type=Bar&tx=paid",
                                 chart_data, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content), 15000)


class FaceDetectTests(TestCase):
    def test_detect_from_url(self):
        response = Client().get(
            "/facedetect/detect-from-url?url=https%3A%2F%2Fmedia.licdn.com%2Fmedia%2Fp%2F4%2F000%2F177%2F3b9%2F28f29f4.jpg&tx=paid")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response2json(response)), 1)

    def test_detect_from_file(self):
        with open(os.path.join(os.path.dirname(__file__),"test_data/36bd0b8.jpg"), "rb") as file:
            response = Client().post("http://127.0.0.1:8000/facedetect/detect-from-file?tx=paid", {"image": file})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response2json(response)), 1)

    @skip("Missing backend service")
    def test_detect2_from_file(self):
        with open(os.path.join(os.path.dirname(__file__),"test_data/36bd0b8.jpg"), "rb") as file:
            response = Client().post("http://127.0.0.1:8000/facedetect/detect2-from-file?tx=paid", {"image": file})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response2json(response)["faces"]), 1)

    @skip("Missing backend service")
    def test_extract_from_file(self):
        with open(os.path.join(os.path.dirname(__file__),"test_data/faces.jpg"), "rb") as file:
            response = Client().post("http://127.0.0.1:8000/facedetect/extract-from-file?tx=paid", {"image": file})
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content), 10000)


class LanguageTests(TestCase):
    def test_translate(self):
        response = Client().post("/language/translate?tx=paid",
                                 {"text": "book", "to_language": "ru"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue("translated" in response2json(response))

    def test_sentiment_analysis(self):
        response = Client().post("/language/sentiment-analysis?tx=paid",
                                 {"text": "bitcoin rocks!"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue("polarity" in response2json(response))


class PhoneTests(TestCase):
    def test_reverse_lookup(self):
        response = Client().get("/phone/phone-lookup?phone=14153545628&tx=paid")
        self.assertEqual(response.status_code, 200)
        self.assertTrue("name" in response2json(response))

    # Temporarily commented out due to service problems
    # def test_send_sms(self):
    #     response = Client().post("/phone/send-sms?phone=14153545628&tx=paid",
    #                              {"phone": "0000000000", "text": "hello"})
    #     self.assertEqual(response.status_code, 200)
    #     self.assertTrue("success" in response2json(response))


class BarcodeTests(TestCase):
    def test_generate_qr(self):
        response = Client().get("/barcode/generate-qr?text=can%20I%20haz%20code%3F&tx=paid")
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content), 500)

    def test_upc_lookup(self):
        response = Client().get("/barcode/upc-lookup?upc=07114200050&tx=paid")
        self.assertEqual(response.status_code, 200)

# class SpeechTests(TestCase):
#     def test_text_to_speech(self):
#         response = Client().get("/speech/text-to-speech?text=hello%20bitcoin&tx=paid")
#         #self.assertEqual(response.status_code, 200)
#         #self.assertGreater(len(response.content), 4000)


class WeatherTests(TestCase):
    def test_current_temperature(self):
        response = Client().get("/weather/current-temperature?place=CA%2FSan%20Francisco&tx=paid")
        self.assertEqual(response.status_code, 200)
        result = response.content.decode("utf-8")
        self.assertGreater(float(result), 32)
        self.assertLess(float(result), 100)

    def test_forecast(self):
        response = Client().get("/weather/forecast?place=CA%2FSan%20Francisco&tx=paid")
        self.assertEqual(response.status_code, 200)
        self.assertTrue("response" in response2json(response))

    def test_radar(self):
        response = Client().get("/weather/radar?place=CA%2FSan%20Francisco&tx=paid")
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content), 1000)


class ScraperTests(TestCase):
    def test_scrape_text(self):
        response = Client().get("/scrape/scrape-text?url=https%3A%2F%2Fmedium.com%2F%4021dotco%2Fa-bitcoin-miner-in-every-device-and-in-every-hand-e315b40f2821&tx=paid")
        self.assertEqual(response.status_code, 200)

    def test_scrape_text_with_selector(self):
        response = Client().get("/scrape/scrape-text-with-selector?url=https%3A%2F%2Fmedium.com%2F%4021dotco%2Fa-bitcoin-miner-in-every-device-and-in-every-hand-e315b40f2821&selector=%2F%2Fdiv%5B%40class%3D%22section-inner%20layoutSingleColumn%22%5D%2F%2Ftext()%20&tx=paid")
        self.assertEqual(response.status_code, 200)
