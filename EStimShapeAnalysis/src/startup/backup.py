import os
import subprocess
import datetime
import shutil
import re
from src.startup import context

# MySQL connection parameters
MYSQL_HOST = '172.30.6.80'
MYSQL_USER = 'xper_rw'
MYSQL_PASSWORD = 'up2nite'


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
        return "unknown", "unknown", "unknown"


def main():
    # Extract info from ga_database in context
    type_name, date, location_id = extract_info_from_database_name(context.ga_database)

    # Create backup directory name based on extracted info
    backup_name = f"{type_name}_{date}_{location_id}"
    backup_dir = f"/run/user/1003/gvfs/smb-share:server=connorhome.local,share=connorhome/Allen/ExperimentData/45X/{backup_name}"

    # Ensure the backup directory exists
    try:
        os.makedirs(backup_dir, exist_ok=True)
        print(f"Created backup directory: {backup_dir}")
    except Exception as e:
        print(f"Error creating directory {backup_dir}: {e}")
        print("This might be because 'smb://' URLs need to be mounted first.")
        print("Trying an alternative path format...")

        # Alternative path format if SMB URL doesn't work directly
        backup_dir = f"/run/user/1003/gvfs/smb-share:server=connorhome.local,share=connorhome/Allen/ExperimentData/45X/{backup_name}"
        try:
            os.makedirs(backup_dir, exist_ok=True)
            print(f"Created backup directory: {backup_dir}")
        except Exception as e2:
            print(f"Error creating alternative directory: {e2}")
            print("Please ensure the SMB share is mounted and accessible.")
            return

    # Create subdirectories
    db_backup_path = os.path.join(backup_dir, "databases")
    local_backup_path = os.path.join(backup_dir, "local_files")
    remote_backup_path = os.path.join(backup_dir, "intan_files")
    impedance_backup_path = os.path.join(backup_dir, "impedance_measurements")

    os.makedirs(db_backup_path, exist_ok=True)
    os.makedirs(local_backup_path, exist_ok=True)
    os.makedirs(remote_backup_path, exist_ok=True)

    # Get databases from context
    databases = [
        context.ga_database,
        context.nafc_database,
        context.isogabor_database,
        context.twodvsthreed_database
    ]

    # Backup today's impedance measurement files
    backup_impedance_measurements(impedance_backup_path)

    # Backup databases
    for db_name in databases:
        backup_database(db_name, db_backup_path)

    # Backup local directories
    for db_name in databases:
        local_dir = f"/home/r2_allen/Documents/EStimShape/{db_name}"
        target_dir = os.path.join(local_backup_path, db_name)
        backup_directory(local_dir, target_dir)

    # Backup remote directories
    remote_paths = {
        context.ga_database: context.ga_intan_path,
        context.isogabor_database: context.isogabor_intan_path,
        context.twodvsthreed_database: context.twodvsthreed_intan_path,
        context.nafc_database: f"/run/user/1003/gvfs/sftp:host=172.30.9.78/home/i2_allen/Documents/EStimShape/{context.nafc_database}"
    }

    for db_name, remote_path in remote_paths.items():
        target_dir = os.path.join(remote_backup_path, db_name)
        backup_directory(remote_path, target_dir)

    print(f"\nBackup completed to: {backup_dir}")


def backup_database(db_name, backup_path):
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


def backup_directory(source_dir, target_dir):
    """Backup a directory to the specified path using rsync"""
    # Skip if source doesn't exist
    if not os.path.exists(source_dir):
        print(f"Skipping non-existent directory: {source_dir}")
        return False

    try:
        print(f"Backing up directory: {source_dir}")

        # Create target directory
        os.makedirs(target_dir, exist_ok=True)

        # Modified rsync for SMB compatibility:
        # -r: recursive (instead of -a which causes permission issues)
        # -t: preserve times
        # -v: verbose
        # -h: human-readable sizes
        # --progress: show progress during transfer
        # --no-perms: don't try to set permissions
        # --no-owner: don't try to set owner
        # --no-group: don't try to set group
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


def backup_impedance_measurements(backup_path):
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
    today = datetime.datetime.now().date()

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
            file_date = datetime.datetime.fromtimestamp(mod_time).date()

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
if __name__ == "__main__":
    main()