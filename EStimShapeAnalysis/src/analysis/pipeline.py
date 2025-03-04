from concurrent.futures import ProcessPoolExecutor

import logging
import pandas as pd
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generic, TypeVar, Dict, Any, List, Tuple, Union

# Type variables for input/output types
InputT = TypeVar('InputT')
OutputT = TypeVar('OutputT')
ResultT = TypeVar('ResultT')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('neurophys.pipeline')


###################
# CORE INTERFACES #
###################

class InputHandler(Generic[InputT, OutputT], ABC):
    """Base class for input handlers that prepare data for computation."""

    @abstractmethod
    def prepare(self, data: InputT) -> OutputT:
        """Transform input data into format needed by computation module."""
        pass


class ComputationModule(Generic[InputT, OutputT], ABC):
    """Base class for analysis computation modules."""

    @abstractmethod
    def compute(self, prepared_data: InputT) -> OutputT:
        """Perform the core analysis computation."""
        pass

    @property
    def metadata(self) -> Dict[str, Any]:
        """Return metadata about the computation."""
        return {
            'name': self.__class__.__name__,
            'parameters': self.get_parameters()
        }

    def get_parameters(self) -> Dict[str, Any]:
        """Return computation parameters."""
        # Get all instance attributes that don't start with underscore
        return {
            key: value for key, value in self.__dict__.items()
            if not key.startswith('_')
        }


class OutputHandler(Generic[InputT, ResultT], ABC):
    """Base class for output handlers that format or visualize results."""

    @abstractmethod
    def process(self, result: InputT) -> ResultT:
        """Process the computation results."""
        pass


class AnalysisModule(Generic[InputT, OutputT, ResultT]):
    """Combined module for a complete analysis step."""

    def __init__(self,
                 input_handler: InputHandler,
                 computation: ComputationModule,
                 output_handler: OutputHandler,
                 name: str = None):
        self.input_handler = input_handler
        self.computation = computation
        self.output_handler = output_handler
        self.name = name or self.__class__.__name__
        self._results = None
        self._raw_output = None

    def run(self, data: InputT) -> ResultT:
        """Execute the full analysis module."""
        try:
            logger.info(f"Module {self.name}: Starting preparation...")
            prepared_data = self.input_handler.prepare(data)

            logger.info(f"Module {self.name}: Running computation...")
            computation_result = self.computation.compute(prepared_data)
            self._raw_output = computation_result

            logger.info(f"Module {self.name}: Processing output...")
            output = self.output_handler.process(computation_result)
            self._results = output

            return output
        except Exception as e:
            logger.error(f"Error in module {self.name}: {str(e)}")
            raise

    @property
    def results(self):
        """Access the processed results."""
        return self._results

    @property
    def raw_output(self):
        """Access the raw computation results before output processing."""
        return self._raw_output

    def __str__(self):
        return f"AnalysisModule({self.name})"

    def __repr__(self):
        return self.__str__()


class MultiInputHandler(InputHandler):
    """Handles multiple inputs from parallel branches."""

    def __init__(self, handlers=None):
        """Initialize with optional specific handlers for each input."""
        self.handlers = handlers or []

    def prepare(self, data_tuple):
        """Process each element in the tuple with corresponding handler."""
        if not isinstance(data_tuple, tuple):
            raise TypeError("Expected a tuple of inputs")

        # If specific handlers are provided, use them
        if self.handlers:
            if len(self.handlers) != len(data_tuple):
                raise ValueError(f"Got {len(data_tuple)} inputs but have {len(self.handlers)} handlers")

            prepared_data = []
            for i, (handler, data) in enumerate(zip(self.handlers, data_tuple)):
                prepared_data.append(handler.prepare(data))
            return tuple(prepared_data)

        # Default behavior: pass through all inputs
        return data_tuple


class PassthroughHandler(InputHandler):
    """Simple handler that passes data through unchanged."""

    def prepare(self, data):
        """Return the data unchanged."""
        return data


class DataFrameOutputHandler(OutputHandler):
    """Standard output handler that ensures results are in DataFrame format."""

    def process(self, result):
        """Convert result to DataFrame if needed."""
        if isinstance(result, pd.DataFrame):
            return result
        elif isinstance(result, dict):
            return pd.DataFrame([result])
        elif isinstance(result, list) and all(isinstance(item, dict) for item in result):
            return pd.DataFrame(result)
        else:
            # Just return as is if we don't know how to convert
            return result


####################
# PIPELINE CLASSES #
####################

# Type definition for pipeline structures
StructureType = Union[
    AnalysisModule,
    List['StructureType'],
    Tuple['StructureType', ...],
    Dict[str, Any]
]


@dataclass
class PipelineResult:
    """Container for pipeline execution results."""
    final_output: Any
    step_outputs: Dict[str, Any] = field(default_factory=dict)
    execution_time: Dict[str, float] = field(default_factory=dict)

    def get_step_result(self, step_name: str) -> Any:
        """Get the result of a specific named step."""
        return self.step_outputs.get(step_name)


class AnalysisPipeline:
    """Orchestrates the execution of analysis modules."""

    def __init__(self, structure: StructureType = None):
        """Initialize with an optional pipeline structure."""
        self.structure = structure
        self._step_count = 0
        self._step_results = {}
        self._step_timing = {}

    def run(self, input_data) -> PipelineResult:
        """Execute the pipeline structure on input data."""
        import time

        if self.structure is None:
            raise ValueError("Pipeline structure not defined")

        self._step_count = 0
        self._step_results = {}
        self._step_timing = {}

        start_time = time.time()
        result = self._process_structure(self.structure, input_data)
        total_time = time.time() - start_time

        logger.info(f"Pipeline completed in {total_time:.2f} seconds")

        return PipelineResult(
            final_output=result,
            step_outputs=self._step_results,
            execution_time=self._step_timing
        )

    def _process_structure(self, structure, data, step_path=""):
        """Process any structure recursively."""
        import time

        # Case: single module (leaf node)
        if isinstance(structure, AnalysisModule):
            step_name = structure.name
            if step_path:
                step_name = f"{step_path}.{step_name}"

            logger.info(f"Executing module: {step_name}")
            start_time = time.time()
            result = structure.run(data)
            elapsed = time.time() - start_time

            self._step_count += 1
            self._step_results[step_name] = result
            self._step_timing[step_name] = elapsed

            logger.info(f"Module {step_name} completed in {elapsed:.2f} seconds")
            return result

        # Case: dictionary with named module
        elif isinstance(structure, dict) and "module" in structure:
            module = structure["module"]
            step_name = structure.get("name", module.name)
            if step_path:
                step_name = f"{step_path}.{step_name}"

            logger.info(f"Executing named module: {step_name}")
            start_time = time.time()
            result = module.run(data)
            elapsed = time.time() - start_time

            self._step_count += 1
            self._step_results[step_name] = result
            self._step_timing[step_name] = elapsed

            logger.info(f"Module {step_name} completed in {elapsed:.2f} seconds")
            return result

        # Case: sequential flow [A, B, ...]
        elif isinstance(structure, list):
            current_data = data
            next_path = f"{step_path}.seq" if step_path else "seq"

            for i, step in enumerate(structure):
                step_id = f"{next_path}[{i}]"
                current_data = self._process_structure(step, current_data, step_id)

            return current_data

        # Case: parallel branches (A, B, ...)
        elif isinstance(structure, tuple):
            results = []
            next_path = f"{step_path}.par" if step_path else "par"

            for i, branch in enumerate(structure):
                step_id = f"{next_path}[{i}]"
                results.append(self._process_structure(branch, data, step_id))

            return tuple(results)

        else:
            raise TypeError(f"Unsupported structure type: {type(structure)}")

    def __str__(self):
        if self.structure:
            return f"AnalysisPipeline(steps={self._count_steps(self.structure)})"
        return "AnalysisPipeline(empty)"

    def _count_steps(self, structure):
        """Count the number of analysis modules in the structure."""
        if isinstance(structure, AnalysisModule):
            return 1
        elif isinstance(structure, dict) and "module" in structure:
            return 1
        elif isinstance(structure, (list, tuple)):
            return sum(self._count_steps(item) for item in structure)
        return 0


#################
# BUILDER CLASS #
#################

class Branch:
    """Builder for creating pipeline branches."""

    def __init__(self):
        self.steps = []

    def then(self, module: Union[AnalysisModule, Dict]) -> 'Branch':
        """Add a sequential step to this branch."""
        self.steps.append(module)
        return self

    def branch(self, *branches: 'Branch') -> 'Branch':
        """Create parallel branches."""
        # Extract the steps from each branch
        branch_steps = [branch.build() for branch in branches]
        if not all(branch_steps):
            raise ValueError("Cannot add empty branches")

        self.steps.append(tuple(branch_steps))
        return self

    def build(self):
        """Build the branch structure."""
        if not self.steps:
            return None
        if len(self.steps) == 1:
            return self.steps[0]
        return self.steps


class PipelineBuilder:
    """Builder for creating analysis pipelines."""

    def __init__(self):
        self.branch = Branch()

    def then(self, module: Union[AnalysisModule, Dict]) -> 'PipelineBuilder':
        """Add a sequential step to the pipeline."""
        self.branch.then(module)
        return self

    def branch(self, *branches: Branch) -> 'PipelineBuilder':
        """Create parallel branches in the pipeline."""
        self.branch.branch(*branches)
        return self

    def build(self) -> AnalysisPipeline:
        """Build the pipeline from the defined structure."""
        structure = self.branch.build()
        if not structure:
            raise ValueError("Cannot build empty pipeline")
        return AnalysisPipeline(structure)


def create_pipeline() -> PipelineBuilder:
    """Factory function to create a new pipeline builder."""
    return PipelineBuilder()


def create_branch() -> Branch:
    """Factory function to create a new branch."""
    return Branch()


#############################
# EXECUTION HELPER FUNCTIONS #
#############################

def execute_parallel(modules: List[AnalysisModule], data, max_workers: int = None):
    """Execute multiple modules in parallel and return results."""
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_module = {
            executor.submit(module.run, data): module
            for module in modules
        }

        results = {}
        for future in future_to_module:
            module = future_to_module[future]
            try:
                result = future.result()
                results[module.name] = result
            except Exception as exc:
                logger.error(f'{module.name} generated an exception: {exc}')
                results[module.name] = None

    return results


class AnalysisModuleFactory:
    """Factory for creating common analysis module combinations."""

    @staticmethod
    def create(
            computation: ComputationModule,
            input_handler: InputHandler = None,
            output_handler: OutputHandler = None,
            name: str = None
    ) -> AnalysisModule:
        """Create an analysis module with the given components."""
        input_handler = input_handler or PassthroughHandler()
        output_handler = output_handler or DataFrameOutputHandler()
        return AnalysisModule(
            input_handler=input_handler,
            computation=computation,
            output_handler=output_handler,
            name=name or computation.__class__.__name__
        )