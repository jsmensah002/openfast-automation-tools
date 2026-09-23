An automation framework for generating, editing, and executing parallelized parameter sweeps using OpenFAST.

File Descriptions:
- case_setup.py: Automates workspace deployment by duplicating baseline aerodynamic turbine configurations (e.g., AWT-27) into isolated experimental directories.
- fix_output.py: Modifies OpenFAST configuration driver files to enforce standardized text-based formatting.
- sweep.py: Executes concurrent, multi-worker parallel simulation sweeps across defined ranges

