"""speciesOT — interspecies CellOT baseline package.

Marker to make `speciesOT.hub.*` importable from the workspace root.
Existing notebooks that `sys.path.insert(...)` the inner `speciesOT/` dir
and `import speciesot_helpers` still work — adding this `__init__.py`
does not change sibling-module imports.
"""
