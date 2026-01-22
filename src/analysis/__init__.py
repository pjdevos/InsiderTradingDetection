"""
Analysis module for suspicion scoring and pattern detection
"""
from analysis.scoring import SuspicionScorer, calculate_suspicion_score
from analysis.patterns import (
    WalletPatternAnalyzer,
    WalletProfile,
    NetworkPattern,
    TemporalPattern,
    analyze_wallet,
    find_suspicious_networks,
    find_repeat_offenders
)
from analysis.win_calculator import WinLossCalculator, get_win_loss_calculator
from analysis.win_scoring import (
    SuspiciousWinScorer,
    get_suspicious_win_scorer,
    WIN_ALERT_THRESHOLDS
)

__all__ = [
    # Suspicion scoring
    'SuspicionScorer',
    'calculate_suspicion_score',
    # Pattern analysis
    'WalletPatternAnalyzer',
    'WalletProfile',
    'NetworkPattern',
    'TemporalPattern',
    'analyze_wallet',
    'find_suspicious_networks',
    'find_repeat_offenders',
    # Win/loss calculation
    'WinLossCalculator',
    'get_win_loss_calculator',
    # Suspicious win scoring
    'SuspiciousWinScorer',
    'get_suspicious_win_scorer',
    'WIN_ALERT_THRESHOLDS'
]
