from clat.util import connection

from src.startup import context
from src.analysis.ga.repo_ga_response_update import update_repository_with_ga_responses


def main():
    ga_config = context.ga_config
    response_processor = ga_config.response_processor
    clear_driving_responses(ga_config.connection())
    response_processor.process_to_db(ga_config.ga_name)

    # GA Responses were just recomputed; push them into the repository (best-effort).
    update_repository_with_ga_responses()


def clear_driving_responses(conn: connection):
    """
    Clear all driving responses from the database.
    This function is a placeholder for the actual implementation.
    """
    #set the driving responses to None
    conn.execute("UPDATE StimGaInfo SET response = NULL")

    # delete GA Respones from TaskfieldCache
    conn.execute("DELETE FROM TaskFieldCache WHERE name = 'GA Response'")

if __name__ == "__main__":
    main()
