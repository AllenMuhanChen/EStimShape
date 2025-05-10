from src.analysis.compile_all import analyses


def main():
    session_id = "250509_0"
    channel = "A-011"
    for analysis in analyses:
        #
        analysis.analyze(channel, "raw", session_id=session_id)


if __name__ == "__main__":
    main()


