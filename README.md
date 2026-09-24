An automation framework for generating, editing, and executing parallelized parameter sweeps using OpenFAST.

File Descriptions:
- build_table.py: Aggregates output data from across the generated parameter sweep directories, parsing specific variables into a structured summary table.
- case_setup.py: Automates workspace deployment by duplicating baseline aerodynamic turbine configurations (e.g., AWT-27) into isolated experimental directories.
- fix_output.py: Modifies OpenFAST configuration driver files to enforce standardized text-based formatting.
- sweep.py: Executes concurrent, multi-worker parallel simulation sweeps across defined ranges

The table generated in usage_examples.txt can be used to build a predictive model.
