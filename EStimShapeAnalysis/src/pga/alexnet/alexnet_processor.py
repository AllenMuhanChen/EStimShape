from typing import List

from src.pga.alexnet.onnx_parser import UnitIdentifier


class AlexNetResponseProcessor:
    def __init__(self, conn, unit_id: UnitIdentifier) -> None:
        self.conn = conn
        self.unit_id = unit_id

    def process_to_db(self, ga_name: str) -> None:
        """Process unit activations and update StimGaInfo responses."""
        stim_ids = self._get_stims_without_responses()

        for stim_id in stim_ids:
            activation = self._get_unit_activation(stim_id)
            if activation is not None:
                self._update_stim_response(stim_id, activation)

    def _get_stims_without_responses(self) -> List[int]:
        """Get all stim_ids from StimGaInfo that have no response."""
        query = """
            SELECT stim_id 
            FROM StimGaInfo 
            WHERE response IS NULL OR response = ''
        """
        self.conn.execute(query)
        return [row[0] for row in self.conn.fetch_all()]

    def _get_unit_activation(self, stim_id: int) -> float | None:
        """Get activation for specified unit and stim_id."""
        query = """
            SELECT activation 
            FROM UnitActivations 
            WHERE stim_id = %s AND unit = %s
        """
        self.conn.execute(query, (stim_id, self.unit_id.to_string()))
        result = self.conn.fetch_one()
        return float(result) if result else None

    def _update_stim_response(self, stim_id: int, activation: float) -> None:
        """Update the response in StimGaInfo."""
        query = "UPDATE StimGaInfo SET response = %s WHERE stim_id = %s"
        self.conn.execute(query, (activation, stim_id))
        self.conn.mydb.commit()