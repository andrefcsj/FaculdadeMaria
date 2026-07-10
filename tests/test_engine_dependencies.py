import unittest
from pathlib import Path

class EngineDependencyTests(unittest.TestCase):
    def test_engine_has_no_forbidden_imports(self):
        root = Path(__file__).resolve().parents[1] / 'engine'
        source = '\n'.join(p.read_text(encoding='utf-8') for p in root.rglob('*.py'))
        forbidden = ['import flask', 'from flask', 'import psycopg2', 'import sqlite3', 'import csv', 'import yfinance', 'import requests']
        for item in forbidden:
            self.assertNotIn(item, source)
