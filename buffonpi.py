import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import List
import pandas as pd
import sqlite3
import os

@dataclass
class RoundInfo:
    round_number: int
    intersections: int
    total_needles: int
    cumulative_pi: float

class BuffonNeedleSimulation:
    def __init__(self, db_path: str = "buffon_needle.db"):
        self.db_path = db_path
        self.init_database()
        self.rounds = self.load_rounds()
        
    def init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rounds (
                    round_number INTEGER PRIMARY KEY,
                    intersections INTEGER NOT NULL,
                    total_needles INTEGER NOT NULL,
                    cumulative_pi REAL NOT NULL
                )
            """)
    
    def calculate_cumulative_pi(self, new_intersections: int, new_total_needles: int) -> float:
        """Calculate cumulative pi based on all rounds including the new one"""
        total_intersections = sum(round.intersections for round in self.rounds) + new_intersections
        total_needles = sum(round.total_needles for round in self.rounds) + new_total_needles
        return (2 * total_needles) / total_intersections if total_intersections > 0 else float('inf')
    
    def load_rounds(self) -> List[RoundInfo]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT round_number, intersections, total_needles, cumulative_pi FROM rounds ORDER BY round_number")
            return [
                RoundInfo(
                    round_number=row[0],
                    intersections=row[1],
                    total_needles=row[2],
                    cumulative_pi=row[3]
                )
                for row in cursor.fetchall()
            ]
    
    def add_round(self, intersections: int, total_needles: int):
        cumulative_pi = self.calculate_cumulative_pi(intersections, total_needles)
        next_round = len(self.rounds) + 1
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO rounds (round_number, intersections, total_needles, cumulative_pi)
                VALUES (?, ?, ?, ?)
            """, (next_round, intersections, total_needles, cumulative_pi))
        
        self.rounds = self.load_rounds()
    
    def get_first_last_rounds(self, n: int = 5):
        if not self.rounds:
            return [], []
        
        first_rounds = self.rounds[:n]
        last_rounds = self.rounds[-n:] if len(self.rounds) > n else []
        return first_rounds, last_rounds
    
    def clear_data(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.init_database()
        self.rounds = []

def plot_pi_approximation(rounds: List[RoundInfo], figsize=(10, 6)):
    if not rounds:
        return plt.Figure()
    
    fig, ax = plt.subplots(figsize=figsize)
    
    round_numbers = [r.round_number for r in rounds]
    cumulative_pi_estimates = [r.cumulative_pi for r in rounds]
    
    # Plot the cumulative approximations
    ax.plot(round_numbers, cumulative_pi_estimates, 'b-', label='Pi Approximation')
    ax.axhline(y=np.pi, color='r', linestyle='--', label='Actual Pi')
    
    ax.set_xlabel('Round Number')
    ax.set_ylabel('Pi Approximation')
    ax.set_title("Buffon's Needle Pi Approximation Over Rounds")
    ax.legend()
    ax.grid(True)
    
    # Let the y-axis adjust dynamically based on the data
    min_val = min(cumulative_pi_estimates)
    max_val = max(cumulative_pi_estimates)
    padding = (max_val - min_val) * 0.1  # Add 10% padding
    ax.set_ylim([min_val - padding, max_val + padding])
    
    return fig

def main():
    st.set_page_config(layout="wide")
    st.title("Buffon's Needle Pi Estimation")
    
    # Initialize simulation with SQLite database
    if 'simulation' not in st.session_state:
        st.session_state.simulation = BuffonNeedleSimulation()
    
    # Create two columns
    col1, col2 = st.columns([0.7, 0.3])
    
    with col1:
        # Display the main plot
        fig = plot_pi_approximation(st.session_state.simulation.rounds)
        st.pyplot(fig)
        
        # Add a clear data button
        if st.button("Clear All Data"):
            st.session_state.simulation.clear_data()
            st.rerun()
    
    with col2:
        st.subheader("Add New Round")
        with st.form("new_round_form"):
            total_needles = st.number_input(
                "Total number of sticks",
                min_value=1,
                value=20
            )
            
            # Limit intersections based on total needles
            max_intersections = total_needles
            intersections = st.number_input(
                "Number of intersections",
                min_value=1,
                max_value=max_intersections,
                value=1  # Simple start at 1
            )
            
            submitted = st.form_submit_button("Next Round")
            
            # Add validation message after form submission
            if submitted:
                if intersections > 0:
                    st.session_state.simulation.add_round(intersections, total_needles)
                    st.rerun()
                else:
                    st.error("Number of intersections must be greater than 0!")
        
        # Display first and last rounds
        st.subheader("First and Last Rounds")
        first_rounds, last_rounds = st.session_state.simulation.get_first_last_rounds()
        
        st.write("First 5 Rounds:")
        if first_rounds:
            df_first = pd.DataFrame([
                {
                    "Round": r.round_number,
                    "Intersections": r.intersections,
                    "Total Sticks": r.total_needles,
                    "π Approximation": f"{r.cumulative_pi:.6f}"
                }
                for r in first_rounds
            ])
            st.dataframe(df_first)
        
        if last_rounds:
            st.write("Last 5 Rounds:")
            df_last = pd.DataFrame([
                {
                    "Round": r.round_number,
                    "Intersections": r.intersections,
                    "Total Sticks": r.total_needles,
                    "π Approximation": f"{r.cumulative_pi:.6f}"
                }
                for r in last_rounds
            ])
            st.dataframe(df_last)

if __name__ == "__main__":
    main()
