# Spindle Tramming Tool

is a tool used with linuxcnc to help with tramming na spindle. Use a dial indecator in the collet. GUI has controls to move in arc rotations to keep the indecator from moving when it has some amount of preload onto it. 

## Install

Suggest using virtualenv (include sitepackages aswell for being able to import linuxcnc package)
```bash
virtualenv --system-site-packages venv
```

Launch linuxcnc, launch the tool. The tool talks to linuxcnc remotly and runs standalone.

Launch the tool by running the shell script after making it executable (cmod +x the shell script)
