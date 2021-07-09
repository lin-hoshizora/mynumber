"""Helper functions for type checks."""
from typing import Any


def assure_type(var: Any, var_type: Any):
  """Check variable type

  Args:
    var: a variable
    var_type: exectped type of the variable

  Raises:
    TypeError: `var` is not an instance of `var_type`
  """
  if not isinstance(var, var_type):
    raise TypeError(f"Expected {var_type}, got {type(var)}")
