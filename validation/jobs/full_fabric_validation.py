mkdir -p jobs

cat > jobs/full_fabric_validation.py <<'EOF'
"""
Full fabric validation suite.
Runs underlay tests, then overlay tests.
"""

from pyats.easypy import run


def main(runtime):
    """Entry point for pyats job."""
    runtime.job.name = "AI Fabric Validation"
    
    # Run underlay tests
    run(
        testscript="../tests/test_underlay.py",
        runtime=runtime,
        taskid="Underlay Validation"
    )
    
    # Run overlay tests
    run(
        testscript="../tests/test_overlay.py",
        runtime=runtime,
        taskid="Overlay Validation"
    )
EOF
