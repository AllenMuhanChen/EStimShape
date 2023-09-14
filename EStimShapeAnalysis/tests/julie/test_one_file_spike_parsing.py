
from src.intan.one_file_spike_parsing import OneFileParser
def test_parse():
    parser = OneFileParser()
    data = parser.parse("/run/user/1003/gvfs/sftp:host=172.30.6.58/home/connorlab/Documents/IntanData/2023-09-14/test_1694709657041242_230914_124058")
    print(data)


