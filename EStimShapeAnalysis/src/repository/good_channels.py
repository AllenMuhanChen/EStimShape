#!/usr/bin/env python3
from __future__ import annotations
"""
Good Channels Manager

Functions for managing the GoodChannels table in the allen_data_repository database.
"""

from clat.util.connection import Connection
from typing import List


def main():
    # Example session ID to work with
    SESSION_ID = "250427_0"
    # Example list of good channels to write
    GOOD_CHANNELS = ["A-017", "A-018", "A-031"]
    # Write good channels
    write_good_channels(SESSION_ID, GOOD_CHANNELS)




def write_good_channels(session_id: str, channel_list: List[str]) -> None:
    """
    Writes a list of good channels for a session to the GoodChannels table.
    Creates the table if it doesn't exist.

    Args:
        session_id: The session ID to associate with the channels
        channel_list: A list of channel identifiers considered "good"
    """
    conn = Connection("allen_data_repository")

    # Create table if it doesn't exist
    conn.execute("""
    CREATE TABLE IF NOT EXISTS GoodChannels (
      session_id VARCHAR(10) NOT NULL,
      channel VARCHAR(255) NOT NULL,
      PRIMARY KEY (session_id, channel),
      FOREIGN KEY (session_id) REFERENCES Sessions(session_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=latin1
    """)

    # Verify the session exists
    conn.execute("SELECT COUNT(*) FROM Sessions WHERE session_id = %s", params=(session_id,))
    if conn.fetch_one()[0] == 0:
        raise ValueError(f"Session ID '{session_id}' does not exist in the Sessions table")

    # Clear existing records for this session
    conn.execute("DELETE FROM GoodChannels WHERE session_id = %s", params=(session_id,))

    # Insert the new good channels
    for channel in channel_list:
        conn.execute(
            "INSERT INTO GoodChannels (session_id, channel) VALUES (%s, %s)",
            params=(session_id, channel)
        )

    print(f"Successfully wrote {len(channel_list)} good channels for session {session_id}")


def read_good_channels(session_id: str) -> List[str]:
    """
    Reads the list of good channels for a session from the GoodChannels table.

    Args:
        session_id: The session ID to retrieve channels for

    Returns:
        A list of channel identifiers marked as "good" for the session
    """
    conn = Connection("allen_data_repository")

    # Create table if it doesn't exist
    conn.execute("""
    CREATE TABLE IF NOT EXISTS GoodChannels (
      session_id VARCHAR(10) NOT NULL,
      channel VARCHAR(255) NOT NULL,
      PRIMARY KEY (session_id, channel),
      FOREIGN KEY (session_id) REFERENCES Sessions(session_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=latin1
    """)

    # Retrieve the good channels for this session
    conn.execute(
        "SELECT channel FROM GoodChannels WHERE session_id = %s ORDER BY channel",
        params=(session_id,)
    )

    # Extract channel names from the results
    return [row[0] for row in conn.fetch_all()]


def read_cluster_channels(session_id: str) -> List[str]:
    """
    Reads the list of cluster channels for a specific session from the ClusterInfo table.

    Args:
        session_id: The session ID to retrieve cluster channels for

    Returns:
        A list of unique channel identifiers from the ClusterInfo table for all
        experiments associated with the session
    """
    conn = Connection("allen_data_repository")

    # Query experiments for this session
    conn.execute(
        "SELECT experiment_id FROM Experiments WHERE session_id = %s",
        params=(session_id,)
    )
    experiment_ids = [row[0] for row in conn.fetch_all()]

    if not experiment_ids:
        return []

    # Format placeholders for SQL IN clause
    placeholders = ', '.join(['%s'] * len(experiment_ids))

    # Query channels from ClusterInfo table for all experiments in this session
    conn.execute(
        f"SELECT DISTINCT channel FROM ClusterInfo WHERE experiment_id IN ({placeholders}) ORDER BY channel",
        params=experiment_ids
    )

    # Return the list of unique channel identifiers
    return [row[0] for row in conn.fetch_all()]

# Example usage - edit these values to test
if __name__ == "__main__":
    main()
