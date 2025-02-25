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

    @property
    def round_pi(self) -> float:
        """Calculate pi approximation for this individual round"""
        return (self.total_needles) / self.intersections if self.intersections > 0 else float('inf')

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
        total_intersections = sum(round.intersections for round in self.rounds) + new_intersections
        total_needles = sum(round.total_needles for round in self.rounds) + new_total_needles
        return (total_needles) / total_intersections if total_intersections > 0 else float('inf')
    
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
    
    def get_rounds_for_display(self):
        """Returns rounds in reverse chronological order"""
        return list(reversed(self.rounds))
    
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
    individual_pi_estimates = [(r.total_needles / r.intersections) if r.intersections > 0 else np.nan for r in rounds]
    
    ax.plot(round_numbers, cumulative_pi_estimates, 'b-', label='Pi Approximation')
    # Add pi reference line with annotation
    ax.axhline(y=np.pi, color='r', linestyle='--', label=f'π ≈ {np.pi:.3f}')
    
    # Add text annotation for pi value
    ax.text(
        x=len(round_numbers) * 0.02,  # Place near the left
        y=np.pi + 0.02,  # Slightly above the line
        s=f'π ≈ {np.pi:.3f}',
        color='r',
        bbox=dict(facecolor='white', alpha=0.8, edgecolor='none')
    )
    
    ax.set_xlabel('Round Number')
    ax.set_ylabel('Pi Approximation')
    ax.set_title("Buffon's Needle Pi Approximation Over Rounds")
    ax.legend()
    ax.grid(True)
    
    min_val = min(cumulative_pi_estimates)
    max_val = max(cumulative_pi_estimates)
    padding = (max_val - min_val) * 0.1
    ax.set_ylim([min_val - padding, max_val + padding])
    
    return fig

def main():
    st.set_page_config(layout="wide")
    st.title("Buffon's Needle Pi Estimation")
    
    if 'simulation' not in st.session_state:
        st.session_state.simulation = BuffonNeedleSimulation()
    
    col1, col2 = st.columns([0.7, 0.3])
    
    with col1:
        fig = plot_pi_approximation(st.session_state.simulation.rounds)
        st.pyplot(fig)
        
        # Initialize dialog state if not exists
        if 'show_clear_dialog' not in st.session_state:
            st.session_state.show_clear_dialog = False
        
        # Show clear data button
        if st.button("Clear All Data", key="clear_btn"):
            st.session_state.show_clear_dialog = True
        
        # Show confirmation dialog
        if st.session_state.show_clear_dialog:
            st.warning("Are you sure you want to clear all data?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, Clear Data", type="primary", key="confirm_clear"):
                    st.session_state.simulation.clear_data()
                    st.session_state.show_clear_dialog = False
                    st.rerun()
            with col2:
                if st.button("Cancel", key="cancel_clear"):
                    st.session_state.show_clear_dialog = False
                    st.rerun()
    
    with col2:
        st.subheader("Add New Round")
        with st.form("new_round_form"):
            total_needles = st.number_input(
                "Total number of sticks",
                min_value=1,
                value=20
            )
            
            max_intersections = total_needles
            intersections = st.number_input(
                "Number of intersections",
                min_value=1,
                max_value=max_intersections,
                value=int((total_needles)/3)
            )
            
            submitted = st.form_submit_button("Next Round")
            
            if submitted and intersections > 0:
                st.session_state.simulation.add_round(intersections, total_needles)
                st.rerun()
        
        # Display rounds in reverse chronological order
        st.subheader("Rounds History")
        all_rounds = st.session_state.simulation.get_rounds_for_display()
        
        if all_rounds:
            df = pd.DataFrame([
                {
                    "Round": r.round_number,
                    "Intersections": r.intersections,
                    "Total Sticks": r.total_needles,
                    "Round π": f"{r.round_pi:.6f}",
                    "Cumulative π": f"{r.cumulative_pi:.6f}",
                    "Difference from π": f"{abs(r.cumulative_pi - np.pi):.6f}"
                }
                for r in all_rounds
            ])
            
            # Create a container with fixed height and scrolling
            with st.container():
                st.dataframe(
                    df,
                    height=300,  # Fixed height with scrolling
                    hide_index=True
                )

if __name__ == "__main__":
    main()
