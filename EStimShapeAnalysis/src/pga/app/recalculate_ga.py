from clat.util import connection

from src.startup import context


def main():
    ga_config = context.ga_config
    response_processor = ga_config.response_processor
    clear_driving_responses(ga_config.connection())
    response_processor.process_to_db(ga_config.ga_name)


def clear_driving_responses(conn: connection):
    """
    Clear all driving responses from the database.
    This function is a placeholder for the actual implementation.
    """
    #set the driving responses to None
    conn.execute("UPDATE StimGaInfo SET response = NULL")

if __name__ == "__main__":
    main()
