import pandas as pd
from sqlalchemy import (
    create_engine, MetaData, Table, Column, Integer, BigInteger,
    Float, String, Text, ForeignKey, select, insert
)
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, List, Any
import time

from clat.util.connection import Connection
from src.repository.export_to_repository import read_stim_info, read_session_id_from_db_name, write_session_to_db, \
    read_rf_info, write_rf_info_to_db, write_experiment_to_db, read_cluster_info, write_cluster_info_to_db, \
    read_stim_task_mapping, write_stim_experiment_mapping, write_task_stim_mapping, read_epochs, write_epochs_to_db, \
    read_raw_spike_responses, write_raw_spike_responses


def write_stim_info_to_db_sqlalchemy_with_conn(repo_conn, table_name: str,
                                               stim_info_data: Dict[int, Dict[str, Any]],
                                               stim_task_mapping: Dict):
    """
    Alternative SQLAlchemy function that uses your existing Connection class
    """
    from sqlalchemy import create_engine, MetaData, Table, text


    try:
        # Try to get raw connection - adjust this line based on your Connection class
        raw_conn = repo_conn.connection  # or however you access the raw connection

        # Create SQLAlchemy engine from existing connection
        engine = create_engine(
            "mysql://",
            strategy='mock',
            executor=lambda sql, *_: raw_conn.execute(sql)
        )

    except AttributeError:
        # Fallback: use original method but with mysqlclient instead
        try:
            connection_string = "mysql://xper_rw:up2nite@172.30.6.80/allen_data_repository"
            engine = create_engine(connection_string)
        except ImportError:
            # Final fallback: use original write_stim_info_to_db
            print("SQLAlchemy dependencies not available, falling back to original method")
            from src.repository.export_to_repository import write_stim_info_to_db
            write_stim_info_to_db(repo_conn, table_name, stim_info_data, stim_task_mapping)
            return

    metadata = MetaData()

    with engine.connect() as conn:
        # Use the same logic as before but with the existing connection
        clean_stim_info_data = _clean_column_names(stim_info_data)
        valid_stim_ids = set(stim_task_mapping['unique_stim_ids'])
        table = _ensure_table_exists(conn, metadata, table_name, clean_stim_info_data)
        _add_missing_columns(conn, table, clean_stim_info_data)
        metadata.clear()
        table = Table(table_name, metadata, autoload_with=engine)
        success_count = _insert_data(conn, table, clean_stim_info_data, valid_stim_ids)
        print(f"Successfully exported {success_count} records to {table_name}")


def export_to_repository_alchemy(df: pd.DataFrame, db_name: str, exp_name: str,
                                 stim_info_table: str = "None", stim_info_columns: List[str] = None):
    """
    Export data to repository database using SQLAlchemy for stim info operations.
    This is a drop-in replacement for the original export_to_repository function.
    """
    repo_conn = Connection("allen_data_repository")
    to_export_conn = Connection(db_name)

    # session ID
    session_id, date = read_session_id_from_db_name(db_name)
    write_session_to_db(repo_conn, session_id, date)

    # RF INFO
    rf_info = read_rf_info(to_export_conn)
    write_rf_info_to_db(repo_conn, session_id, rf_info)

    # Experiments
    experiment_id = f"{session_id}_{exp_name}"
    write_experiment_to_db(repo_conn, experiment_id, session_id, exp_name, db_name)

    # ClusterInfo
    cluster_info = read_cluster_info(to_export_conn)
    write_cluster_info_to_db(repo_conn, experiment_id, cluster_info)

    # Stim Ids and Task Stim Mappings
    stim_task_mapping = read_stim_task_mapping(df)
    write_stim_experiment_mapping(repo_conn, experiment_id, stim_task_mapping)
    write_task_stim_mapping(repo_conn, stim_task_mapping)

    # Epochs
    epochs = read_epochs(df)
    write_epochs_to_db(repo_conn, epochs)

    # Raw Spike Responses
    raw_spike_responses = read_raw_spike_responses(df)
    write_raw_spike_responses(repo_conn, raw_spike_responses)

    # Stim Info (using SQLAlchemy instead of original write_stim_info_to_db)
    if stim_info_table != "None" and stim_info_columns:
        # Read stim info data
        stim_info = read_stim_info(df, stim_info_columns)

        # Write using SQLAlchemy with existing connection
        write_stim_info_to_db_sqlalchemy_with_conn(
            repo_conn=repo_conn,
            table_name=stim_info_table,
            stim_info_data=stim_info,
            stim_task_mapping=stim_task_mapping
        )

    print(f"Export complete for {db_name} to repository database.")
def _clean_column_names(stim_info_data: Dict[int, Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """Clean column names by replacing spaces with underscores"""
    clean_data = {}
    for stim_id, stim_data in stim_info_data.items():
        clean_data[stim_id] = {
            col.replace(' ', '_'): value
            for col, value in stim_data.items()
        }
    return clean_data


def _ensure_table_exists(conn, metadata: MetaData, table_name: str,
                         stim_info_data: Dict[int, Dict[str, Any]]) -> Table:
    """Create table if it doesn't exist, return Table object"""

    # Check if table exists using SQLAlchemy's inspection
    from sqlalchemy import inspect
    inspector = inspect(conn)

    if table_name not in inspector.get_table_names():
        print(f"Table '{table_name}' does not exist. Creating it...")

        # Create base table with just stim_id and foreign key
        table = Table(
            table_name, metadata,
            Column('stim_id', BigInteger, primary_key=True),
            # Note: Foreign key creation in SQLAlchemy
            # ForeignKey('StimExperimentMapping.stim_id', ondelete='CASCADE')
        )

        # Create the table
        table.create(conn)
        print(f"Table '{table_name}' created successfully")
        time.sleep(1)  # Wait for table creation

    else:
        # Table exists, load it with reflection
        table = Table(table_name, metadata, autoload_with=conn)

    return table


def _add_missing_columns(conn, table: Table, stim_info_data: Dict[int, Dict[str, Any]]):
    """Add missing columns to existing table"""

    # Get required columns from data
    required_cols = set()
    for stim_data in stim_info_data.values():
        required_cols.update(stim_data.keys())

    # Get existing columns
    existing_cols = set(table.columns.keys())

    # Find missing columns
    missing_cols = required_cols - existing_cols

    if missing_cols:
        print(f"Adding {len(missing_cols)} missing columns to {table.name}...")

        # Detect column types
        column_types = _detect_sqlalchemy_column_types(stim_info_data)

        for col in missing_cols:
            try:
                sql_type = column_types.get(col, String(255))
                print(f"Adding column '{col}' with type '{sql_type}'...")

                # Raw SQL for ALTER TABLE (SQLAlchemy doesn't have built-in ALTER COLUMN)
                alter_sql = f"ALTER TABLE {table.name} ADD COLUMN {col} {_sqlalchemy_type_to_mysql(sql_type)}"
                conn.execute(alter_sql)

                # Verify column was added
                time.sleep(0.5)

            except SQLAlchemyError as e:
                print(f"Error adding column '{col}': {e}")


def _detect_sqlalchemy_column_types(stim_info_data: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    """Detect appropriate SQLAlchemy column types"""
    import numpy as np

    column_types = {}
    column_values = {}

    # Collect values for each column
    for stim_data in stim_info_data.values():
        for col, value in stim_data.items():
            if col not in column_values:
                column_values[col] = []
            if value is not None:
                column_values[col].append(value)

    # Determine types
    for col, values in column_values.items():
        if not values:
            column_types[col] = String(255)
            continue

        sample_values = values[:100]

        # Check for integers
        if all(isinstance(v, (int, np.int64, np.int32)) for v in sample_values):
            max_val = max(sample_values)
            min_val = min(sample_values)

            if min_val >= -2147483648 and max_val <= 2147483647:
                column_types[col] = Integer
            else:
                column_types[col] = BigInteger

        # Check for floats
        elif all(isinstance(v, (float, np.float64, np.float32)) for v in sample_values):
            column_types[col] = Float

        # Check for strings
        elif all(isinstance(v, str) for v in sample_values):
            max_length = max(len(str(v)) for v in sample_values)

            if max_length <= 200:
                column_types[col] = String(255)
            elif max_length > 1000:
                column_types[col] = LONGTEXT
            else:
                column_types[col] = String(1000)
        else:
            column_types[col] = String(255)

    return column_types


def _sqlalchemy_type_to_mysql(sqlalchemy_type) -> str:
    """Convert SQLAlchemy type to MySQL type string for ALTER TABLE"""
    if isinstance(sqlalchemy_type, type):
        if sqlalchemy_type == Integer:
            return "INT"
        elif sqlalchemy_type == BigInteger:
            return "BIGINT"
        elif sqlalchemy_type == Float:
            return "FLOAT"
        elif sqlalchemy_type == LONGTEXT:
            return "LONGTEXT"
    elif hasattr(sqlalchemy_type, 'length'):
        return f"VARCHAR({sqlalchemy_type.length})"

    return "VARCHAR(255)"  # fallback


def _insert_data(conn, table: Table, stim_info_data: Dict[int, Dict[str, Any]],
                 valid_stim_ids: set) -> int:
    """Insert/update data using SQLAlchemy"""
    success_count = 0

    for stim_id, stim_data in stim_info_data.items():
        if stim_id not in valid_stim_ids:
            continue

        # Prepare data with type conversion
        insert_data = {'stim_id': int(stim_id)}

        for col, value in stim_data.items():
            if col in table.columns:
                # Convert value to basic Python types
                converted_value = _convert_value(value)
                insert_data[col] = converted_value

        if len(insert_data) <= 1:  # Only stim_id
            continue

        try:
            # SQLAlchemy upsert for MySQL
            stmt = insert(table).values(**insert_data)

            # MySQL ON DUPLICATE KEY UPDATE
            update_dict = {k: v for k, v in insert_data.items() if k != 'stim_id'}
            if update_dict:
                from sqlalchemy.dialects.mysql import insert as mysql_insert
                stmt = mysql_insert(table).values(**insert_data)
                stmt = stmt.on_duplicate_key_update(**update_dict)

            conn.execute(stmt)
            success_count += 1

        except SQLAlchemyError as e:
            print(f"Error storing StimInfo for stim_id {stim_id}: {e}")

    return success_count


def _convert_value(value):
    """Convert value to basic Python types"""
    if hasattr(value, 'item'):  # Handle numpy types
        try:
            value = value.item()
        except (ValueError, AttributeError):
            pass

    if isinstance(value, (float, int, bool, str)) or value is None:
        return value
    else:
        return str(value)

