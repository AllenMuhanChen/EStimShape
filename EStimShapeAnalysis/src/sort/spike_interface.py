import spikeinterface.extractors as se


def main():
    intan_path = "/run/user/1003/gvfs/sftp:host=172.30.6.58/home/connorlab/Documents/IntanData/2023-09-12/1694529683452000_230912_144921/info.rhd"
    se.read_intan(file_path=intan_path)
    print("Done")


if __name__ == '__main__':
    main()