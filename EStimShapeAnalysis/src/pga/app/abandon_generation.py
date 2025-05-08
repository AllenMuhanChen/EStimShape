from typing import List, Tuple, Optional
from clat.util.connection import Connection
from src.startup import context
import xml.etree.ElementTree as ET

class GenerationIdentifier:
    def __init__(self, connection: Connection):
        self.connection = connection

    def identify_failed_generation(self) -> Optional[int]:
        query = """
        SELECT DISTINCT gen_id
        FROM StimGaInfo sgi
        LEFT JOIN StimSpec ss ON sgi.stim_id = ss.id
        WHERE sgi.response IS NULL AND ss.id IS NULL
        ORDER BY gen_id DESC
        LIMIT 1
        """
        self.connection.execute(query)
        result = self.connection.fetch_one()
        return result if result else None

    def get_current_generation(self) -> Optional[int]:
        query = "SELECT val FROM InternalState WHERE name = 'task_to_do_ga_and_gen_ready'"
        self.connection.execute(query)
        current_gen_info = self.connection.fetch_one()

        if current_gen_info:
            root = ET.fromstring(current_gen_info)
            gen_id_element = root.find(f".//entry[string='{context.ga_name}']")
            if gen_id_element is not None:
                return int(gen_id_element.find('long').text)
        return None

class GenerationAbandonner:
    def __init__(self, connection: Connection):
        self.connection = connection

    def remove_generation(self, gen_id: int):
        # Remove entries from LineageGaInfo
        lineage_query = "DELETE FROM LineageGaInfo WHERE gen_id = %s"
        self.connection.execute(lineage_query, (gen_id,))

        # # Remove entries from StimGaInfo
        # stim_query = "DELETE FROM StimGaInfo WHERE gen_id = %s"
        # self.connection.execute(stim_query, (gen_id,))

        print(f"Removed entries for gen_id {gen_id}")

    def update_generation_info(self, current_gen: int, new_gen: int):
        query = "SELECT val FROM InternalState WHERE name = 'task_to_do_ga_and_gen_ready'"
        self.connection.execute(query)
        current_gen_info = self.connection.fetch_one()

        if current_gen_info:
            root = ET.fromstring(current_gen_info)
            gen_id_element = root.find(f".//entry[string='{context.ga_name}']")
            if gen_id_element is not None:
                gen_id_element.find('long').text = str(new_gen)
                updated_xml = ET.tostring(root, encoding='unicode')

                update_query = "UPDATE InternalState SET val = %s WHERE name = 'task_to_do_ga_and_gen_ready'"
                self.connection.execute(update_query, (updated_xml,))
                print(f"Updated generation number from {current_gen} to {new_gen}")
            else:
                print(f"No generation info found for GA: {context.ga_name}")
        else:
            print("No generation info found in InternalState")

def get_user_input_generation() -> Optional[int]:
    user_input = input("Enter the generation ID to remove (press Enter to automatically detect the failed generation): ")
    if user_input.strip():
        try:
            return int(user_input)
        except ValueError:
            print("Invalid input. Please enter a valid integer.")
            return None
    return None

def main():
    connection = Connection(context.ga_database)
    identifier = GenerationIdentifier(connection)
    abandonner = GenerationAbandonner(connection)

    user_gen = get_user_input_generation()
    if user_gen is None:
        failed_gen = identifier.identify_failed_generation()
        if failed_gen is None:
            print("No failed generation found")
            return
        gen_to_remove = failed_gen
        print(f"Automatically detected failed generation: {gen_to_remove}")
    else:
        gen_to_remove = user_gen

    current_gen = identifier.get_current_generation()
    if current_gen is None:
        print("Could not determine current generation")
        return

    if gen_to_remove != current_gen:
        print(f"Warning: Generation to remove ({gen_to_remove}) is not the current generation ({current_gen})")
        proceed = input("Do you want to proceed? (y/n): ").lower()
        if proceed != 'y':
            print("Operation cancelled")
            return

    abandonner.remove_generation(gen_to_remove)
    abandonner.update_generation_info(current_gen, gen_to_remove - 1)

if __name__ == "__main__":
    main()