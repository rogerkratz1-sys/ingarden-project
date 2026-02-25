import sys
import importlib
import importlib.util as util
import os

print("cwd:", os.getcwd())
print("sys.path[0]:", sys.path[0])
print("top sys.path entries:", sys.path[:4])
print("find_spec('scripts'):", util.find_spec("scripts"))
print("find_spec('scripts.compute_metrics'):", util.find_spec("scripts.compute_metrics"))

try:
    m = importlib.import_module("scripts.compute_metrics")
    print("import scripts.compute_metrics ->", getattr(m, "__file__", "<no __file__>"))
except Exception as e:
    print("import scripts.compute_metrics failed:", type(e).__name__, e)

try:
    m2 = importlib.import_module("Scripts.compute_metrics")
    print("import Scripts.compute_metrics ->", getattr(m2, "__file__", "<no __file__>"))
except Exception as e:
    print("import Scripts.compute_metrics failed:", type(e).__name__, e)
