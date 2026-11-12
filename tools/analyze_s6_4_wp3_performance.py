"""Check WP-3 native admission, complete matched work and reconciled observer gates."""

import analyze_s6_4_wp2_performance as verifier
from run_s6_4_wp3_performance import PROTOCOL


if __name__ == "__main__":
    verifier.PROTOCOL = PROTOCOL
    verifier.main()
