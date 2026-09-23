from clat.util import connection

from src.startup import context
from src.analysis.ga.repo_ga_response_update import update_repository_with_ga_responses


def main():
    ga_config = context.ga_config
    response_processor = ga_config.response_processor
    if getattr(response_processor, "mua_metric", None) is not None:
        # The processor reads MUAChannelResponses; backfill it first if it was never
        # populated (same detection as recalculate_mua_ga).
        from src.pga.mua_channel_responses import MuaChannelResponseStore
        if not MuaChannelResponseStore.for_ga(response_processor.mua_metric).ensure_populated():
            raise RuntimeError(f"MUAChannelResponses has no rows for "
                               f"{response_processor.mua_metric!r} and the backfill produced none.")
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
