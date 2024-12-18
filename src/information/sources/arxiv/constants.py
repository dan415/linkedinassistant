"""Constants for the Arxiv module."""
from enum import Enum

# API Configuration
ARXIV_API_URL = "http://export.arxiv.org/api/"
MAX_RESULTS = 25
MINIMUM_LENGTH = 50
PARAGRAPH_MIN_LENGTH = 10
DEFAULT_PERIOD = 7

# Arxiv Topic Categories
ARXIV_TOPICS = [
    "cat:math.AG",  # Algebraic Geometry
    "cat:cs.AI",  # Artificial Intelligence
    "cat:cs.GT",  # Game Theory
    "cat:cs.CV",  # Computer Vision
    "cat:cs.ET",  # Emerging Technologies
    "cat:cs.IR",  # Information Retrieval
    "cat:cs.LG",  # Machine Learning
    "cat:cs.NE",  # Neural and Evolutionary Computing
    "cat:cs.PL",  # Programming Languages
    "cat:cs.RO"  # Robotics
]



