#!/usr/bin/env python3
"""
Backup script for experiment data using the ExperimentType pattern.

This script backs up:
- MySQL databases
- Local experiment files
- Remote intan recording files
- Impedance measurement files (created today)

The backup is organized by experiment type and stored on the SMB share.
"""
import os
import re
import shutil
import subprocess
from datetime import datetime
from typing import Tuple

from src.startup import context
from src.startup.startup_system import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, GAExperiment, \
    NAFCExperiment, IsoGaborExperiment, LightnessExperiment, ShuffleExperiment


def extract_info_from_database_name(db_name):
    """Extract type, date, and location_id from database name"""
    # Example: allen_ga_train_250213_0
    # We need to extract "train", "250213", and "0"
    pattern = r'allen_\w+_(\w+)_(\d+)_(\d+)'
    match = re.match(pattern, db_name)

    if match:
        type_name = match.group(1)
        date = match.group(2)
        location_id = match.group(3)
        return type_name, date, location_id
    else:
        # Fallback if pattern doesn't match
        print(f"Warning: Could not parse database name '{db_name}'. Using defaults.")
        return "unknown", datetime.now().strftime("%y%m%d"), "0"


def main():
    """Main function to perform backups using the refactored system"""

    # Extract info from ga_database in context
    type_name, date, location_id = extract_info_from_database_name(context.ga_database)

    print(f"Starting backup for experiments:")
    print(f"  Type: {type_name}")
    print(f"  Date: {date}")
    print(f"  Location: {location_id}")
    print()

    # Create BackupManager with the extracted information
    backup_manager = BackupManager(type_name, date, location_id)

    # Perform the backup
    backup_manager.perform_backup()

    print("\nBackup script completed.")



class BackupManager:
    """Manager class for handling experiment backups"""

    def __init__(self, type_name: str, date: str, location_id: str):
        self.type_name = type_name
        self.date = date
        self.location_id = location_id

        # Reuse the same experiment instances as ExperimentManager
        self.experiments = [
            GAExperiment(type_name, date, location_id),
            NAFCExperiment(type_name, date, location_id),
            IsoGaborExperiment(type_name, date, location_id),
            LightnessExperiment(type_name, date, location_id),
            ShuffleExperiment(type_name, date, location_id),
        ]

    def get_backup_directory(self) -> Tuple[str, bool]:
        """
        Create and return the backup directory path.
        Returns tuple of (path, success)
        """
        backup_name = f"{self.type_name}_{self.date}_{self.location_id}"
        backup_dir = f"/run/user/1003/gvfs/smb-share:server=connorhome.local,share=connorhome/Allen/ExperimentData/45X/{backup_name}"

        # Try to create the backup directory
        try:
            os.makedirs(backup_dir, exist_ok=True)
            print(f"Created backup directory: {backup_dir}")
            return backup_dir, True
        except Exception as e:
            print(f"Error creating directory {backup_dir}: {e}")
            print("Please ensure the SMB share is mounted and accessible.")
            return backup_dir, False

    def backup_database(self, db_name: str, backup_path: str) -> bool:
        """Backup a MySQL database to the specified path"""
        print(f"Backing up database: {db_name}")

        dump_file = os.path.join(backup_path, f"{db_name}.sql")

        try:
            cmd = [
                "mysqldump",
                f"--host={MYSQL_HOST}",
                f"--user={MYSQL_USER}",
                f"--password={MYSQL_PASSWORD}",
                db_name
            ]

            with open(dump_file, 'w') as f:
                subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, check=True)

            print(f"Successfully backed up database {db_name}")
            return True

        except Exception as e:
            print(f"Error backing up database {db_name}: {e}")
            return False

    def backup_directory(self, source_dir: str, target_dir: str) -> bool:
        """Backup a directory to the specified path using rsync"""
        # Skip if source doesn't exist
        if not os.path.exists(source_dir):
            print(f"Skipping non-existent directory: {source_dir}")
            return False

        try:
            print(f"Backing up directory: {source_dir}")

            # Create target directory
            os.makedirs(target_dir, exist_ok=True)

            # Modified rsync for SMB compatibility
            cmd = [
                "rsync",
                "-rtvh",
                "--progress",
                "--no-perms",
                "--no-owner",
                "--no-group",
                f"{source_dir}/",  # The trailing slash is important
                f"{target_dir}/"
            ]

            process = subprocess.run(cmd, check=True)
            print(f"Successfully backed up directory {source_dir}")
            return True

        except subprocess.SubprocessError as e:
            print(f"rsync error for {source_dir}: {e}")

            # Fall back to shutil if rsync fails
            try:
                print("Falling back to shutil.copytree...")
                shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
                print(f"Successfully backed up directory using shutil")
                return True
            except Exception as e2:
                print(f"shutil error: {e2}")
                return False

        except Exception as e:
            print(f"Error backing up directory {source_dir}: {e}")
            return False

    def backup_impedance_measurements(self, backup_path: str):
        """Backup impedance measurement files created today to the specified backup path"""
        # Source directory for impedance measurements
        impedance_src_dir = "/run/user/1003/gvfs/sftp:host=172.30.9.78/home/i2_allen/Documents/ImpedanceMeasurements/"

        # Make sure the backup path exists
        try:
            os.makedirs(backup_path, exist_ok=True)
        except Exception as e:
            print(f"Error creating impedance backup directory: {e}")
            return

        # Check if source directory exists
        if not os.path.exists(impedance_src_dir):
            print(f"Warning: Impedance measurements path does not exist or is not mounted: {impedance_src_dir}")
            return

        # Today's date for filtering files
        today = datetime.now().date()

        try:
            # Get all files in the source directory
            files = os.listdir(impedance_src_dir)
            today_files = []

            # Filter for today's files
            for filename in files:
                source_path = os.path.join(impedance_src_dir, filename)

                # Skip directories
                if not os.path.isfile(source_path):
                    continue

                # Check if file was modified today
                mod_time = os.path.getmtime(source_path)
                file_date = datetime.fromtimestamp(mod_time).date()

                if file_date == today:
                    today_files.append(filename)

            if not today_files:
                print("No impedance measurement files found from today")
                return

            print(f"Found {len(today_files)} impedance measurement files from today")

            # Copy each file
            for filename in today_files:
                source_path = os.path.join(impedance_src_dir, filename)
                dest_path = os.path.join(backup_path, filename)

                print(f"Copying {filename} to {backup_path}")

                try:
                    # Use rsync for copying
                    cmd = [
                        "rsync",
                        "-vh",  # verbose and human-readable
                        "--progress",
                        "--no-perms",
                        "--no-owner",
                        "--no-group",
                        source_path,
                        dest_path
                    ]

                    subprocess.run(cmd, check=True)
                    print(f"Successfully copied {filename}")

                except Exception as e:
                    print(f"Error copying file {filename}: {e}")

        except Exception as e:
            print(f"Error processing impedance measurement files: {e}")

    def perform_backup(self):
        """Perform complete backup of all experiments"""
        # Get backup directory
        backup_dir, success = self.get_backup_directory()
        if not success:
            return

        # Create subdirectories
        db_backup_path = os.path.join(backup_dir, "databases")
        local_backup_path = os.path.join(backup_dir, "local_files")
        remote_backup_path = os.path.join(backup_dir, "intan_files")
        impedance_backup_path = os.path.join(backup_dir, "impedance_measurements")

        os.makedirs(db_backup_path, exist_ok=True)
        os.makedirs(local_backup_path, exist_ok=True)
        os.makedirs(remote_backup_path, exist_ok=True)

        # Backup today's impedance measurement files
        self.backup_impedance_measurements(impedance_backup_path)

        # Backup each experiment
        for experiment in self.experiments:
            if not experiment.should_backup():
                print(f"Skipping backup for {experiment.__class__.__name__}")
                continue

            db_name = experiment.get_database_name()

            # Backup database
            self.backup_database(db_name, db_backup_path)

            # Backup local directories
            for local_path in experiment.get_local_backup_paths():
                target_dir = os.path.join(local_backup_path, db_name)
                self.backup_directory(local_path, target_dir)

            # Backup remote directories
            remote_paths = experiment.get_remote_backup_paths()
            for path_key, remote_path in remote_paths.items():
                target_dir = os.path.join(remote_backup_path, db_name)
                self.backup_directory(remote_path, target_dir)

        print(f"\nBackup completed to: {backup_dir}")




if __name__ == "__main__":
    main()