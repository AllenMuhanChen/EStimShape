from clat.intan.amplifiers import read_amplifier_data
from clat.intan.rhd.load_intan_rhd_format import read_data


class TestAmplifiers:
    def test_read_amplifier_data(self):
        path_to_rhd = '/run/user/1003/gvfs/smb-share:server=connorhome.local,share=connorhome/Julie/IntanData/Cortana/2023-09-15/1694801146439198_230915_140547/info.rhd'
        data = read_data(path_to_rhd)
        amplifier_channels = data['amplifier_channels']

        # # Example usage:
        file_path = "/run/user/1003/gvfs/smb-share:server=connorhome.local,share=connorhome/Julie/IntanData/Cortana/2023-09-15/1694801146439198_230915_140547/amplifier.dat"
        v = read_amplifier_data(file_path, amplifier_channels)
        print(v)
