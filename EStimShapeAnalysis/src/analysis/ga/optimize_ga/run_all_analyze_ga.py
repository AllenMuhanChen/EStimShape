from typing import List, Tuple
from clat.util.connection import Connection
from src.analysis.ga.optimize_ga.analyze_magnitudes import AnalyzeMagnitudesAnalysis
from src.startup.startup_system import ExperimentManager


def main():
    # Initialize analysis modules
    analyses = [
        AnalyzeMagnitudesAnalysis()
    ]

    # Process all sessions
    print("Fetching all sessions...")
    sessions_to_process = fetch_session_ids()
    print(f"Found {len(sessions_to_process)} sessions")


    # Run all analyses for this session
    for session_id in sessions_to_process:
        manager = ExperimentManager(session_id=session_id)
        manager.switch_context_only()
        for analysis in analyses:
            analysis.session_id = session_id
            compiled_data = analysis.compile()
            analysis.analyze(None, compiled_data)


def fetch_session_ids() -> List[str]:
    """Fetch all session IDs from the database."""
    conn = Connection("allen_data_repository")
    query = "SELECT session_id FROM Sessions"
    conn.execute(query)
    session_ids = conn.fetch_all()
    return [session_id_tuple[0] for session_id_tuple in session_ids]


if __name__ == "__main__":
    main()
