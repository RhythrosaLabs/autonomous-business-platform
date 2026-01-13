import unittest
import os
from modules.video_generation import generate_ken_burns_video

class TestKenBurnsVideo(unittest.TestCase):
    def setUp(self):
        # Use a small sample image for testing
        self.test_image = "test_kenburns_sample.jpg"
        # Create a simple image if not present
        if not os.path.exists(self.test_image):
            from PIL import Image
            img = Image.new('RGB', (640, 480), color='blue')
            img.save(self.test_image)
        self.output_path = "kenburns_test_output.mp4"

    def tearDown(self):
        # Clean up files after test
        if os.path.exists(self.test_image):
            os.remove(self.test_image)
        if os.path.exists(self.output_path):
            os.remove(self.output_path)

    def test_generate_ken_burns_video(self):
        result = generate_ken_burns_video(
            image_path=self.test_image,
            output_path=self.output_path,
            duration=2,
            fps=10,
            resolution="720p"
        )
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.output_path))

if __name__ == "__main__":
    unittest.main()
