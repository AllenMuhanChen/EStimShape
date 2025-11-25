from src.analysis.analyze_raw_data import fetch_session_ids
from src.analysis.ga.ga_vector_analysis import GAResponseVectorAnalysis
from src.startup.startup_system import ExperimentManager

def main():
    # Initialize analysis modules
    analyses = [
        GAResponseVectorAnalysis()
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
            compiled_data = analysis.compile_and_export()


if __name__ == "__main__":
    main()