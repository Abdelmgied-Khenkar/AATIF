"""
Root conftest.py — ensures engine/ is on sys.path for all tests.
"""
import os
import sys

ENGINE_DIR = os.path.join(os.path.dirname(__file__), "engine")
if ENGINE_DIR not in sys.path:
    sys.path.insert(0, ENGINE_DIR)
