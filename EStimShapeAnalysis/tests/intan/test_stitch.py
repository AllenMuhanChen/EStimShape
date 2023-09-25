import unittest
import os
from src.intan.stitch import IntanFileStitcher


class TestIntanFileStitcher(unittest.TestCase):

    def setUp(self):
        # Specify the directories you have on your computer
        self.test_dirs = [
            "/run/user/1003/gvfs/smb-share:server=connorhome.local,share=connorhome/Julie/IntanData/Cortana/2023-09-22/1695411976234126_230922_154616",
            "/run/user/1003/gvfs/smb-share:server=connorhome.local,share=connorhome/Julie/IntanData/Cortana/2023-09-22/1695413856827412_230922_161737",
        ]

        # Get the sizes of the amplifier.dat files in each directory
        self.file_sizes = []
        for dir_path in self.test_dirs:
            file_path = os.path.join(dir_path, 'amplifier.dat')
            self.file_sizes.append(os.path.getsize(file_path))

        # Create a directory for the output (you can also specify this)
        self.output_dir = "/run/user/1003/gvfs/smb-share:server=connorhome.local,share=connorhome/Julie/IntanData/Cortana/2023-09-22/test_stitcher_output"

    def test_stitch_files(self):
        stitcher = IntanFileStitcher(self.test_dirs)
        stitcher.stitch_files(self.output_dir)

        # Check if the output file exists
        output_file_path = os.path.join(self.output_dir, 'amplifier.dat')
        self.assertTrue(os.path.exists(output_file_path))

        # Check if the output file size matches the sum of the individual file sizes
        output_file_size = os.path.getsize(output_file_path)
        print("file 1 size: ", self.file_sizes[0])
        print("file 2 size: ", self.file_sizes[1])
        print("output file size: ", output_file_size)
        self.assertEqual(output_file_size, sum(self.file_sizes))


if __name__ == '__main__':
    unittest.main()
