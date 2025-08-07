#!/usr/bin/env python3
"""
Script to correct file paths in the allen_data_repository database.
Replaces '/home/r2_allen/' with '/home/connorlab/' in StimPath and ThumbnailPath columns.
"""

import sys
import logging
from typing import List, Tuple, Dict
from clat.util.connection import Connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_path_columns(conn: Connection) -> Dict[str, List[str]]:
    """
    Find all tables and columns that contain 'StimPath' or 'ThumbnailPath'.

    Returns:
        Dictionary mapping table names to lists of path column names
    """
    path_columns = {}

    # Get all table names
    conn.execute("SHOW TABLES")
    tables = [row[0] for row in conn.fetch_all()]

    # Check each table for path columns
    for table in tables:
        conn.execute(f"DESCRIBE {table}")
        columns = [row[0] for row in conn.fetch_all()]

        # Find columns that are StimPath or ThumbnailPath
        path_cols = [col for col in columns
                     if col in ['StimPath', 'ThumbnailPath']]

        if path_cols:
            path_columns[table] = path_cols
            logger.info(f"Found path columns in table '{table}': {path_cols}")

    return path_columns


def count_rows_to_update(conn: Connection, table: str, column: str,
                         old_path: str) -> int:
    """
    Count how many rows need to be updated in a given table/column.
    """
    query = f"SELECT COUNT(*) FROM {table} WHERE {column} LIKE %s"
    conn.execute(query, (f"{old_path}%",))
    result = conn.fetch_one()
    return result if result else 0


def update_paths_in_table(conn: Connection, table: str, column: str,
                          old_path: str, new_path: str, dry_run: bool = True) -> int:
    """
    Update file paths in a specific table and column.

    Args:
        conn: Database connection
        table: Table name
        column: Column name
        old_path: Path prefix to replace
        new_path: New path prefix
        dry_run: If True, only count what would be updated without making changes

    Returns:
        Number of rows that were (or would be) updated
    """
    # Count rows that would be affected
    count_query = f"SELECT COUNT(*) FROM {table} WHERE {column} LIKE %s"
    conn.execute(count_query, (f"{old_path}%",))
    count = conn.fetch_one()

    if not count:
        logger.info(f"No rows to update in {table}.{column}")
        return 0

    logger.info(f"Found {count} rows to update in {table}.{column}")

    if dry_run:
        logger.info(f"[DRY RUN] Would update {count} rows in {table}.{column}")

        # Show some examples of what would be changed
        example_query = f"SELECT {column} FROM {table} WHERE {column} LIKE %s LIMIT 5"
        conn.execute(example_query, (f"{old_path}%",))
        examples = conn.fetch_all()

        if examples:
            logger.info(f"[DRY RUN] Example paths that would be updated in {table}.{column}:")
            for i, (path,) in enumerate(examples, 1):
                new_example_path = path.replace(old_path, new_path)
                logger.info(f"[DRY RUN]   {i}. {path}")
                logger.info(f"[DRY RUN]      -> {new_example_path}")

        return count

    # Perform the actual update
    update_query = f"""
        UPDATE {table} 
        SET {column} = REPLACE({column}, %s, %s)
        WHERE {column} LIKE %s
    """

    try:
        conn.execute(update_query, (old_path, new_path, f"{old_path}%"))
        logger.info(f"Successfully updated {count} rows in {table}.{column}")
        return count
    except Exception as e:
        logger.error(f"Error updating {table}.{column}: {e}")
        return 0


def main():
    """Main function to run the path correction."""

    # Configuration
    DATABASE_NAME = "allen_data_repository"
    OLD_PATH_PREFIX = "/home/r2_allen/"
    NEW_PATH_PREFIX = "/home/connorlab/"

    # Parse command line arguments for dry run
    dry_run = True
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        dry_run = False
        logger.info("EXECUTION MODE: Changes will be made to the database")
    else:
        logger.info("DRY RUN MODE: No changes will be made. Use --execute to actually update paths")

    try:
        # Connect to database
        logger.info(f"Connecting to database: {DATABASE_NAME}")
        conn = Connection(DATABASE_NAME)

        # Find all tables with path columns
        path_columns = find_path_columns(conn)

        if not path_columns:
            logger.info("No tables with StimPath or ThumbnailPath columns found")
            return

        logger.info(f"Found {len(path_columns)} tables with path columns")

        # Process each table and column
        total_updated = 0

        for table, columns in path_columns.items():
            logger.info(f"\nProcessing table: {table}")

            for column in columns:
                logger.info(f"  Processing column: {column}")

                updated_count = update_paths_in_table(
                    conn=conn,
                    table=table,
                    column=column,
                    old_path=OLD_PATH_PREFIX,
                    new_path=NEW_PATH_PREFIX,
                    dry_run=dry_run
                )

                total_updated += updated_count

        # Summary
        action_word = "would be updated" if dry_run else "updated"
        logger.info(f"\nSummary: {total_updated} rows {action_word} across all tables")

        if dry_run:
            logger.info("\nTo actually perform the updates, run with --execute flag:")
            logger.info(f"python {sys.argv[0]} --execute")
        else:
            logger.info("Path correction completed successfully!")

    except Exception as e:
        logger.error(f"Error during execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()